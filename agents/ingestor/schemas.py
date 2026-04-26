"""
Pydantic schemas for the Ingestor Agent.
Defines the data models for volunteer extraction, normalization, and deduplication.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FileType(str, Enum):
    """Supported file types for ingestion."""
    WHATSAPP_TEXT = "whatsapp_text"
    PDF = "pdf"
    IMAGE = "image"
    EXCEL = "excel"
    CSV = "csv"
    GOOGLE_FORM = "google_form"


class VolunteerLocation(BaseModel):
    """Geographic location of a volunteer."""
    city: str = ""
    district: str = ""
    state: str = ""
    lat: float = 0.0
    lon: float = 0.0
    raw_address: Optional[str] = None


class VolunteerAvailability(BaseModel):
    """Availability schedule for a volunteer."""
    days: list[str] = Field(default_factory=list)
    hours: str = ""
    notes: Optional[str] = None


class VolunteerSource(BaseModel):
    """Source metadata for how this volunteer was ingested."""
    type: str  # "whatsapp" | "pdf" | "image" | "excel" | "form"
    file_name: str = ""
    ingested_at: Optional[datetime] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class ExtractedVolunteer(BaseModel):
    """
    A volunteer record extracted by Gemini from raw input.
    This is the intermediate representation before normalization and dedup.
    """
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    location: VolunteerLocation = Field(default_factory=VolunteerLocation)
    skills_raw: list[str] = Field(default_factory=list)
    languages_raw: list[str] = Field(default_factory=list)
    availability: VolunteerAvailability = Field(default_factory=VolunteerAvailability)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    duplicate_hints: list[str] = Field(default_factory=list)


class NormalizedVolunteer(BaseModel):
    """
    A fully normalized volunteer record ready for Firestore.
    Skills and languages are mapped to the standard taxonomy.
    """
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    location: VolunteerLocation = Field(default_factory=VolunteerLocation)
    skills: list[str] = Field(default_factory=list)  # Normalized taxonomy keys
    skills_raw: list[str] = Field(default_factory=list)  # Original extracted
    languages: list[str] = Field(default_factory=list)  # ISO 639-1 codes
    availability: VolunteerAvailability = Field(default_factory=VolunteerAvailability)
    embedding: list[float] = Field(default_factory=list)  # 768-dim vector
    source: VolunteerSource
    deduped_from: list[str] = Field(default_factory=list)


class IngestionRequest(BaseModel):
    """Request body for POST /ingest."""
    file_uri: str
    file_type: FileType
    job_id: str


class IngestionTestRequest(BaseModel):
    """Request body for POST /ingest/test (synchronous demo)."""
    text: str


class IngestionStatus(BaseModel):
    """Response for GET /ingest/{job_id}."""
    job_id: str
    status: str  # "processing" | "completed" | "failed"
    extracted_count: int = 0
    duplicates_merged: int = 0
    errors: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Internal result from the extraction pipeline."""
    volunteers: list[ExtractedVolunteer] = Field(default_factory=list)
    reasoning: str = ""
    raw_text_preview: str = ""
    errors: list[str] = Field(default_factory=list)
