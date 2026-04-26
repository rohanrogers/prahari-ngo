"""
Pydantic schemas for the Watcher Agent.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Signal(BaseModel):
    """A raw signal from any data source."""
    source_type: str  # "openweather" | "rss" | "reddit"
    source_name: str  # "openweather" | "ndtv" | "toi" | "hindu" | "mathrubhumi" | "r/kerala"
    timestamp: datetime
    content: str
    url: Optional[str] = None
    location_hint: Optional[str] = None
    crisis_type_hint: Optional[str] = None
    raw_data: dict = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    """A piece of evidence in the threat evidence chain."""
    source: str
    timestamp: datetime
    content: str
    url: Optional[str] = None
    weight: float = 0.5


class ThreatLocation(BaseModel):
    """Geographic location of a detected threat."""
    city: str = ""
    district: str = ""
    state: str = ""
    lat: float = 0.0
    lon: float = 0.0
    radius_km: float = 15.0


class ThreatAssessment(BaseModel):
    """
    Complete threat assessment from the Watcher's correlation + Gemini analysis.
    """
    is_real_threat: bool = False
    type: str = "other"  # "flood" | "fire" | "stampede" | "earthquake" | "cyclone" | "landslide" | "other"
    severity: int = Field(ge=1, le=5, default=1)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    location: ThreatLocation = Field(default_factory=ThreatLocation)
    est_escalation_window_min: int = Field(ge=15, le=90, default=60)
    reasoning: str = ""
    evidence_chain: list[EvidenceItem] = Field(default_factory=list)
    grounded_facts: list[str] = Field(default_factory=list)


class WatchCycleResult(BaseModel):
    """Result of one watch cycle."""
    cycle_id: str
    signals_collected: int = 0
    signals_by_source: dict[str, int] = Field(default_factory=dict)
    threats_detected: int = 0
    threats: list[ThreatAssessment] = Field(default_factory=list)
    duration_ms: int = 0
    errors: list[str] = Field(default_factory=list)
