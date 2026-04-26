"""
Pydantic schemas for the Coordinator Agent.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CrisisContext(BaseModel):
    """Context about the crisis for volunteer matching."""
    threat_id: str
    type: str  # "flood" | "fire" | "stampede" etc.
    severity: int = Field(ge=1, le=5, default=3)
    location: dict = Field(default_factory=dict)
    required_skills: list[str] = Field(default_factory=list)
    preferred_languages: list[str] = Field(default_factory=list)
    urgency: str = "medium"  # "low" | "medium" | "high" | "critical"
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    escalation_window_min: int = 60
    radius_km: float = 15.0


class MatchedVolunteer(BaseModel):
    """A volunteer matched to a crisis."""
    volunteer_id: str
    name: str = ""
    match_score: float = Field(ge=0.0, le=1.0, default=0.0)
    match_reasons: list[str] = Field(default_factory=list)
    distance_km: float = 0.0
    assigned_role: Optional[str] = None
    outreach_status: str = "pending"  # "pending" | "sent" | "responded_yes" | "responded_no" | "no_response"


class OutreachMessage(BaseModel):
    """A generated outreach message for a volunteer."""
    volunteer_id: str
    language: str  # ISO 639-1
    channel: str  # "whatsapp" | "sms" | "call_script"
    message: str
    generated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None


class ResponsePlan(BaseModel):
    """A complete response plan for a crisis."""
    threat_id: str
    status: str = "draft"  # "draft" | "pre_staged" | "active" | "completed"
    matched_volunteers: list[MatchedVolunteer] = Field(default_factory=list)
    outreach_messages: dict[str, OutreachMessage] = Field(default_factory=dict)
    coordinator_reasoning: str = ""
    timeline: list[dict] = Field(default_factory=list)


class CoordinatorMode(BaseModel):
    """Coordinator execution mode."""
    mode: str = "pre_staged"  # "pre_staged" | "active"
    max_matches: int = 15
