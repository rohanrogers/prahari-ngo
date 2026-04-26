"""
PRAHARI-NGO — Coordinator Agent
Matches volunteers to crises using Gemini function calling,
generates multilingual outreach messages.

Triggered by Pub/Sub when threats are detected or crises confirmed.
"""

import sys
import json
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, PROJECT_ROOT)

from .schemas import CrisisContext
from .planner import run_coordinator

from shared.firestore_client import get_threat, log_agent_activity
from shared.pubsub_client import parse_pubsub_message

# ─────────────────────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Prahari Coordinator Agent",
    description="Volunteer matching and multilingual outreach via Gemini function calling",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "coordinator"}


@app.post("/on-threat")
async def on_threat_detected(envelope: dict):
    """
    Pub/Sub push handler for threats-detected topic.
    Runs coordinator in PRE_STAGED mode — soft matching, no activation.
    """
    try:
        data = parse_pubsub_message(envelope)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    threat_id = data.get("threat_id")
    if not threat_id:
        raise HTTPException(status_code=400, detail="Missing threat_id")
    
    # Fetch full threat data from Firestore
    threat = get_threat(threat_id)
    if not threat:
        logger.warning(f"Threat {threat_id} not found in Firestore, using Pub/Sub data")
        threat = data
    
    logger.info(f"Pre-staging response for threat {threat_id}: {threat.get('type')} in {threat.get('location', {}).get('district')}")
    
    result = await run_coordinator(threat, mode="pre_staged")
    return result


@app.post("/on-crisis-confirmed")
async def on_crisis_confirmed(envelope: dict):
    """
    Pub/Sub push handler for crisis-confirmed topic.
    Runs coordinator in ACTIVE mode — hard matching, outreach generation.
    """
    try:
        data = parse_pubsub_message(envelope)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    threat_id = data.get("threat_id")
    if not threat_id:
        raise HTTPException(status_code=400, detail="Missing threat_id")
    
    # Fetch full threat data
    threat = get_threat(threat_id)
    if not threat:
        raise HTTPException(status_code=404, detail=f"Threat {threat_id} not found")
    
    overrides = data.get("override_params", {})
    
    logger.info(f"Activating response for threat {threat_id}: confirmed by {data.get('confirmed_by')}")
    
    result = await run_coordinator(threat, mode="active", overrides=overrides)
    return result


@app.post("/coordinate")
async def coordinate_manual(context: CrisisContext):
    """
    Manual coordination trigger (for dashboard use).
    Accepts full crisis context and runs the coordinator.
    """
    threat_data = {
        "threat_id": context.threat_id,
        "type": context.type,
        "severity": context.severity,
        "confidence": context.confidence,
        "location": context.location,
        "required_skills": context.required_skills,
        "est_escalation_window_min": context.escalation_window_min,
    }
    
    result = await run_coordinator(
        threat_data,
        mode="active",
        overrides={
            "radius_km": context.radius_km,
            "required_skills": context.required_skills,
        },
    )
    return result
