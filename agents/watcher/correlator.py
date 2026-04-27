"""
Multi-source signal correlation logic for the Watcher Agent.
A threat is ONLY emitted when >=2 INDEPENDENT sources agree.
"""

import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Optional

from .schemas import Signal, ThreatAssessment, ThreatLocation, EvidenceItem

logger = logging.getLogger(__name__)

# Location normalization — map city names to districts
CITY_TO_DISTRICT = {
    "thiruvananthapuram": ("Thiruvananthapuram", "Kerala", 8.5241, 76.9366),
    "kochi": ("Ernakulam", "Kerala", 9.9312, 76.2673),
    "alappuzha": ("Alappuzha", "Kerala", 9.4981, 76.3388),
    "chennai": ("Chennai", "Tamil Nadu", 13.0827, 80.2707),
    "bengaluru": ("Bengaluru Urban", "Karnataka", 12.9716, 77.5946),
    "bangalore": ("Bengaluru Urban", "Karnataka", 12.9716, 77.5946),
    "mumbai": ("Mumbai", "Maharashtra", 19.0760, 72.8777),
    "delhi": ("New Delhi", "Delhi", 28.6139, 77.2090),
    "kolkata": ("Kolkata", "West Bengal", 22.5726, 88.3639),
    "hyderabad": ("Hyderabad", "Telangana", 17.3850, 78.4867),
    "pune": ("Pune", "Maharashtra", 18.5204, 73.8567),
    "ahmedabad": ("Ahmedabad", "Gujarat", 23.0225, 72.5714),
    "guwahati": ("Kamrup Metropolitan", "Assam", 26.1445, 91.7362),
    "ernakulam": ("Ernakulam", "Kerala", 9.9312, 76.2673),
    "thrissur": ("Thrissur", "Kerala", 10.5276, 76.2144),
    "kottayam": ("Kottayam", "Kerala", 9.5916, 76.5222),
    "pathanamthitta": ("Pathanamthitta", "Kerala", 9.2648, 76.7870),
    "idukki": ("Idukki", "Kerala", 9.8494, 76.9710),
    "wayanad": ("Wayanad", "Kerala", 11.6854, 76.1320),
    "kozhikode": ("Kozhikode", "Kerala", 11.2588, 75.7804),
    "kerala": ("Kerala (state)", "Kerala", 10.8505, 76.2711),
}

# Time bucket size for grouping signals
TIME_BUCKET_MINUTES = 15


def _normalize_location(location_hint: str) -> tuple[str, str, float, float]:
    """Normalize a location hint to (district, state, lat, lon)."""
    if not location_hint:
        return ("Unknown", "Unknown", 0.0, 0.0)
    
    hint_lower = location_hint.lower().strip()
    
    for key, (district, state, lat, lon) in CITY_TO_DISTRICT.items():
        if key in hint_lower:
            return (district, state, lat, lon)
    
    # Fallback: return raw hint as district
    return (location_hint, "Unknown", 0.0, 0.0)


def _time_bucket(dt: datetime) -> str:
    """Round a datetime to the nearest TIME_BUCKET_MINUTES."""
    bucket = dt.replace(
        minute=(dt.minute // TIME_BUCKET_MINUTES) * TIME_BUCKET_MINUTES,
        second=0,
        microsecond=0,
    )
    return bucket.isoformat()


def correlate_signals(signals: list[Signal]) -> list[ThreatAssessment]:
    """
    Group signals by (location, crisis_type, time_bucket) and emit threats
    only when >=2 independent source types agree.
    
    This is what separates Prahari from a notification system.
    """
    if not signals:
        return []
    
    # Group signals by (district, crisis_type, time_bucket)
    groups: dict[tuple, list[Signal]] = defaultdict(list)
    
    for signal in signals:
        district, state, lat, lon = _normalize_location(signal.location_hint)
        crisis_type = signal.crisis_type_hint or "other"
        time_bucket = _time_bucket(signal.timestamp)
        
        key = (district, crisis_type, time_bucket)
        groups[key].append(signal)
    
    # Evaluate each group
    threats = []
    
    for (district, crisis_type, time_bucket), group_signals in groups.items():
        # Require at least 2 distinct source types
        source_types = set(s.source_type for s in group_signals)
        if len(source_types) < 2:
            continue
        
        # Calculate confidence from multi-source agreement
        base_confidence = min(0.5 + 0.15 * len(source_types), 0.85)
        
        # Boost for official sources
        if "openweather" in source_types:
            base_confidence += 0.05
        if any(
            s.source_type == "news_rss" and s.source_name in ["ndtv", "toi", "hindu"]
            for s in group_signals
        ):
            base_confidence += 0.05
        # Government sources get highest boost — most authoritative
        if "imd" in source_types:
            base_confidence += 0.10  # IMD red/orange alert
        if "cwc" in source_types:
            base_confidence += 0.10  # CWC river gauge data
        
        base_confidence = min(base_confidence, 0.95)
        
        # Determine severity from signal count and source diversity
        severity = min(1 + len(source_types) + (len(group_signals) // 3), 5)
        
        # Get location info
        _, state, lat, lon = _normalize_location(group_signals[0].location_hint)
        
        # Build evidence chain
        evidence = []
        for s in sorted(group_signals, key=lambda x: x.timestamp):
            evidence.append(EvidenceItem(
                source=s.source_name,
                timestamp=s.timestamp,
                content=s.content[:300],
                url=s.url,
                weight=_source_weight(s.source_type),
            ))
        
        threat = ThreatAssessment(
            is_real_threat=base_confidence >= 0.65,
            type=crisis_type,
            severity=severity,
            confidence=base_confidence,
            location=ThreatLocation(
                district=district,
                state=state,
                lat=lat,
                lon=lon,
                radius_km=15.0,
            ),
            est_escalation_window_min=_estimate_escalation(crisis_type),
            reasoning=f"Correlated {len(group_signals)} signals from {len(source_types)} independent sources in {district}. Sources: {', '.join(source_types)}.",
            evidence_chain=evidence,
        )
        
        if threat.confidence >= 0.65:
            threats.append(threat)
            logger.info(
                f"🚨 Threat detected: {crisis_type} in {district} "
                f"(confidence={base_confidence:.2f}, sources={len(source_types)})"
            )
    
    return threats


def _source_weight(source_type: str) -> float:
    """Assign reliability weight to each source type."""
    weights = {
        "openweather": 0.9,
        "news_rss": 0.7,
        "reddit": 0.4,
    }
    return weights.get(source_type, 0.3)


def _estimate_escalation(crisis_type: str) -> int:
    """Estimate escalation window in minutes based on crisis type."""
    windows = {
        "flood": 60,
        "fire": 30,
        "earthquake": 15,
        "cyclone": 90,
        "landslide": 45,
        "stampede": 15,
    }
    return windows.get(crisis_type, 60)
