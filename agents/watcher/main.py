"""
PRAHARI-NGO — Watcher Agent
Continuously monitors public Indian data streams, correlates signals,
and emits ThreatAssessments when confidence threshold is crossed.

Triggered by Cloud Scheduler every 5 minutes.
"""

import sys
import time
import json
import logging
import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, PROJECT_ROOT)

from .schemas import WatchCycleResult, Signal
from .sources.weather import fetch_weather_signals
from .sources.rss import fetch_rss_signals
from .sources.reddit import fetch_reddit_signals
# Planned: IMD district-wise warnings (requires IMD API registration)
# from .sources.imd import fetch_imd_warnings
# Planned: CWC river gauge data (requires cwc.gov.in data portal access)
# from .sources.cwc import fetch_cwc_river_levels
from .correlator import correlate_signals
from .grounding import ground_threat

from shared.firestore_client import create_threat, log_agent_activity
from shared.pubsub_client import publish_threat_detected

# ─────────────────────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Prahari Watcher Agent",
    description="Multi-source Indian crisis signal monitoring and correlation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track last cycle stats
_last_cycle: WatchCycleResult | None = None


# ─────────────────────────────────────────────────────────────
# Core Watch Cycle
# ─────────────────────────────────────────────────────────────

async def run_watch_cycle() -> WatchCycleResult:
    """
    Execute one complete watch cycle:
    1. Fetch signals from all sources (Weather, RSS, Reddit)
    2. Correlate signals across sources
    3. Ground threats via Gemini + Google Search
    4. Write to Firestore + publish to Pub/Sub
    5. Log agent activity
    """
    global _last_cycle
    start_time = time.time()
    cycle_id = f"cycle_{uuid4().hex[:8]}"
    
    logger.info(f"[{cycle_id}] Starting watch cycle")
    
    errors = []
    
    # Step 1: Fetch signals from all sources in parallel
    logger.info(f"[{cycle_id}] Step 1: Fetching signals")
    
    weather_signals, rss_signals, reddit_signals = await asyncio.gather(
        fetch_weather_signals(),
        fetch_rss_signals(),
        fetch_reddit_signals(),
        return_exceptions=True,
    )
    
    # Handle exceptions from gather
    all_signals: list[Signal] = []
    signals_by_source = {}
    
    if isinstance(weather_signals, list):
        all_signals.extend(weather_signals)
        signals_by_source["openweather"] = len(weather_signals)
    else:
        errors.append(f"Weather source error: {weather_signals}")
        signals_by_source["openweather"] = 0
    
    if isinstance(rss_signals, list):
        all_signals.extend(rss_signals)
        signals_by_source["rss"] = len(rss_signals)
    else:
        errors.append(f"RSS source error: {rss_signals}")
        signals_by_source["rss"] = 0
    
    if isinstance(reddit_signals, list):
        all_signals.extend(reddit_signals)
        signals_by_source["reddit"] = len(reddit_signals)
    else:
        errors.append(f"Reddit source error: {reddit_signals}")
        signals_by_source["reddit"] = 0
    
    logger.info(f"[{cycle_id}] Collected {len(all_signals)} signals: {signals_by_source}")
    
    # Step 2: Correlate signals
    logger.info(f"[{cycle_id}] Step 2: Correlating signals")
    threats = correlate_signals(all_signals)
    
    logger.info(f"[{cycle_id}] Correlation found {len(threats)} potential threats")
    
    # Step 3: Ground each threat via Gemini
    grounded_threats = []
    for threat in threats:
        logger.info(f"[{cycle_id}] Step 3: Grounding threat in {threat.location.district}")
        
        signals_json = json.dumps(
            [e.model_dump(mode="json") for e in threat.evidence_chain],
            indent=2,
            default=str,
        )
        
        grounded = await ground_threat(signals_json, threat.confidence)
        
        if grounded.confidence >= 0.65:
            grounded_threats.append(grounded)
    
    # Step 4: Write threats to Firestore + Pub/Sub
    for threat in grounded_threats:
        logger.info(f"[{cycle_id}] Step 4: Emitting threat {threat.type} in {threat.location.district}")
        
        # Write to Firestore
        threat_data = threat.model_dump(mode="json")
        threat_data["watcher_reasoning"] = threat.reasoning
        threat_id = create_threat(threat_data)
        
        # Publish to Pub/Sub for Coordinator
        try:
            publish_threat_detected(
                threat_id=threat_id,
                threat_type=threat.type,
                severity=threat.severity,
                confidence=threat.confidence,
                location={
                    "district": threat.location.district,
                    "state": threat.location.state,
                    "lat": threat.location.lat,
                    "lon": threat.location.lon,
                    "radius_km": threat.location.radius_km,
                },
            )
        except Exception as e:
            errors.append(f"Pub/Sub publish failed: {e}")
            logger.error(f"[{cycle_id}] Pub/Sub publish failed: {e}")
    
    # Step 5: Log agent activity
    duration_ms = int((time.time() - start_time) * 1000)
    
    log_agent_activity(
        agent="watcher",
        action="watch_cycle",
        reasoning=f"Scanned {len(all_signals)} signals from {len(signals_by_source)} source types. "
                  f"Found {len(grounded_threats)} threats above confidence threshold.",
        input_summary=f"Weather: {signals_by_source.get('openweather', 0)}, "
                      f"RSS: {signals_by_source.get('rss', 0)}, "
                      f"Reddit: {signals_by_source.get('reddit', 0)}",
        output_summary=f"{len(grounded_threats)} threats emitted",
        duration_ms=duration_ms,
    )
    
    result = WatchCycleResult(
        cycle_id=cycle_id,
        signals_collected=len(all_signals),
        signals_by_source=signals_by_source,
        threats_detected=len(grounded_threats),
        threats=grounded_threats,
        duration_ms=duration_ms,
        errors=errors,
    )
    
    _last_cycle = result
    logger.info(f"[{cycle_id}] Watch cycle complete in {duration_ms}ms")
    
    return result


# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "watcher"}


@app.post("/watch/cycle")
async def trigger_cycle():
    """
    Trigger one watch cycle. Called by Cloud Scheduler every 5 minutes.
    """
    result = await run_watch_cycle()
    return result.model_dump(mode="json")


@app.get("/watch/status")
async def get_status():
    """Return stats from the last watch cycle."""
    if _last_cycle is None:
        return {"status": "no cycles run yet"}
    return _last_cycle.model_dump(mode="json")


@app.post("/watch/replay-inject")
async def replay_inject(signals: list[dict]):
    """
    Demo-only: inject replay data into a watch cycle.
    Used by the Kerala 2018 replay mode on the dashboard.
    """
    parsed_signals = []
    for s in signals:
        try:
            parsed_signals.append(Signal(**s))
        except Exception as e:
            logger.warning(f"Skipping invalid replay signal: {e}")
    
    if not parsed_signals:
        raise HTTPException(status_code=400, detail="No valid signals provided")
    
    # Run correlation on injected signals
    threats = correlate_signals(parsed_signals)
    
    grounded_threats = []
    for threat in threats:
        signals_json = json.dumps(
            [e.model_dump(mode="json") for e in threat.evidence_chain],
            indent=2,
            default=str,
        )
        grounded = await ground_threat(signals_json, threat.confidence)
        if grounded.confidence >= 0.5:  # Lower threshold for replay
            grounded_threats.append(grounded)
    
    # Write to Firestore for dashboard
    for threat in grounded_threats:
        threat_data = threat.model_dump(mode="json")
        threat_data["watcher_reasoning"] = threat.reasoning
        threat_data["status"] = "monitoring"
        create_threat(threat_data)
    
    return {
        "injected_signals": len(parsed_signals),
        "threats_detected": len(grounded_threats),
        "threats": [t.model_dump(mode="json") for t in grounded_threats],
    }
