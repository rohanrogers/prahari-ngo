"""
PRAHARI-NGO — Ingestor Agent
FastAPI application for multimodal volunteer data extraction.

Transforms chaotic NGO data (WhatsApp exports, PDFs, photos, Excel)
into a unified, deduplicated, semantically-searchable Volunteer Graph.
"""

import os
import sys
import time
import json
import logging
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path for shared imports
PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, PROJECT_ROOT)

from .schemas import (
    IngestionRequest,
    IngestionTestRequest,
    IngestionStatus,
    FileType,
)
from .extractors import (
    extract_from_whatsapp,
    extract_from_pdf,
    extract_from_image,
    extract_from_excel,
    extract_from_text,
)
from .normalizer import normalize_skills, normalize_languages, normalize_phone, detect_text_language
from .deduplicator import find_duplicates

from shared.firestore_client import (
    create_volunteer,
    get_all_volunteers,
    merge_volunteer,
    log_agent_activity,
)
from shared.embeddings import (
    generate_embedding,
    build_volunteer_profile_text,
    cosine_similarity,
)

# ─────────────────────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Prahari Ingestor Agent",
    description="Multimodal volunteer data extraction from chaotic NGO sources",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracker (in production, use Firestore)
_jobs: dict[str, IngestionStatus] = {}


# ─────────────────────────────────────────────────────────────
# Core Pipeline
# ─────────────────────────────────────────────────────────────

def _run_pipeline(
    text: str = None,
    file_path: str = None,
    file_type: str = "whatsapp_text",
    job_id: str = None,
) -> dict:
    """
    Run the full ingestion pipeline:
    1. Extract volunteers from raw input
    2. Normalize skills + languages + phone
    3. Generate embeddings
    4. Deduplicate against existing volunteers
    5. Write to Firestore
    6. Log agent activity
    """
    start_time = time.time()
    job_id = job_id or str(uuid4())
    
    # Update job status
    if job_id in _jobs:
        _jobs[job_id].status = "processing"
    
    # Step 1: Extract
    logger.info(f"[{job_id}] Step 1: Extracting from {file_type}")
    
    if file_type == "whatsapp_text" and text:
        result = extract_from_whatsapp(text)
    elif file_type == "pdf" and file_path:
        result = extract_from_pdf(file_path)
    elif file_type == "image" and file_path:
        result = extract_from_image(file_path)
    elif file_type in ("excel", "csv") and file_path:
        result = extract_from_excel(file_path)
    elif text:
        result = extract_from_text(text)
    else:
        raise ValueError(f"Unsupported file type or missing input: {file_type}")
    
    if result.errors:
        logger.error(f"[{job_id}] Extraction errors: {result.errors}")
        if job_id in _jobs:
            _jobs[job_id].status = "failed"
            _jobs[job_id].errors = result.errors
        return {"status": "failed", "errors": result.errors}
    
    extracted = result.volunteers
    logger.info(f"[{job_id}] Extracted {len(extracted)} volunteers")
    
    # Step 2: Normalize
    logger.info(f"[{job_id}] Step 2: Normalizing")
    normalized = []
    for vol in extracted:
        norm = {
            "name": vol.name,
            "phone": normalize_phone(vol.phone),
            "email": vol.email,
            "location": vol.location.model_dump() if vol.location else {},
            "skills": normalize_skills(vol.skills_raw),
            "skills_raw": vol.skills_raw,
            "languages": normalize_languages(vol.languages_raw),
            "availability": vol.availability.model_dump() if vol.availability else {},
            "source": {
                "type": file_type.split("_")[0],
                "file_name": file_path or "(direct text)",
                "confidence": vol.confidence,
            },
        }
        
        # Auto-detect languages from name/skills if none extracted
        if not norm["languages"] and text:
            norm["languages"] = detect_text_language(text[:500])
        
        normalized.append(norm)
    
    # Step 3: Generate embeddings
    logger.info(f"[{job_id}] Step 3: Generating embeddings")
    for vol in normalized:
        profile_text = build_volunteer_profile_text(vol)
        vol["embedding"] = generate_embedding(profile_text)
    
    # Step 4: Deduplicate against existing volunteers
    logger.info(f"[{job_id}] Step 4: Deduplicating")
    existing_volunteers = get_all_volunteers()
    
    new_volunteers = []
    duplicates_merged = 0
    
    for vol in normalized:
        dupes = find_duplicates(vol, existing_volunteers, cosine_fn=cosine_similarity)
        
        if dupes:
            # Merge into the highest-confidence existing record
            best_match, confidence = dupes[0]
            logger.info(
                f"[{job_id}] Dedup: {vol['name']} matches {best_match.get('name')} "
                f"(confidence={confidence:.2f})"
            )
            # Keep existing, note the merge
            if best_match.get("id"):
                merge_volunteer(best_match["id"], vol.get("id", ""))
            duplicates_merged += 1
        else:
            new_volunteers.append(vol)
    
    # Step 5: Write to Firestore
    logger.info(f"[{job_id}] Step 5: Writing {len(new_volunteers)} to Firestore")
    created_ids = []
    for vol in new_volunteers:
        doc_id = create_volunteer(vol)
        created_ids.append(doc_id)
    
    # Step 6: Log activity
    duration_ms = int((time.time() - start_time) * 1000)
    log_agent_activity(
        agent="ingestor",
        action="extract_volunteers",
        reasoning=result.reasoning,
        input_summary=f"{file_type}, {len(extracted)} messages processed",
        output_summary=f"{len(extracted)} extracted, {duplicates_merged} dedup'd, {len(new_volunteers)} new",
        duration_ms=duration_ms,
    )
    
    # Update job status
    if job_id in _jobs:
        _jobs[job_id].status = "completed"
        _jobs[job_id].extracted_count = len(extracted)
        _jobs[job_id].duplicates_merged = duplicates_merged
    
    return {
        "status": "completed",
        "job_id": job_id,
        "extracted_count": len(extracted),
        "duplicates_merged": duplicates_merged,
        "new_volunteers": len(new_volunteers),
        "created_ids": created_ids,
        "reasoning": result.reasoning,
        "duration_ms": duration_ms,
    }


# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "ingestor"}


@app.post("/ingest")
async def ingest(request: IngestionRequest, background_tasks: BackgroundTasks):
    """
    Trigger the ingestion pipeline for a file.
    Processing happens in background; check status via GET /ingest/{job_id}.
    """
    _jobs[request.job_id] = IngestionStatus(
        job_id=request.job_id,
        status="queued",
    )
    
    background_tasks.add_task(
        _run_pipeline,
        file_path=request.file_uri,
        file_type=request.file_type.value,
        job_id=request.job_id,
    )
    
    return {"job_id": request.job_id, "status": "processing"}


@app.get("/ingest/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of an ingestion job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _jobs[job_id]


@app.post("/ingest/test")
async def ingest_test(request: IngestionTestRequest):
    """
    Synchronous ingestion for demo — accepts raw text, returns extracted volunteers.
    This is the endpoint the dashboard uses for live demo.
    """
    result = _run_pipeline(
        text=request.text,
        file_type="whatsapp_text",
        job_id=str(uuid4()),
    )
    return result


@app.post("/ingest/upload")
async def ingest_upload(file: UploadFile = File(...)):
    """
    Upload a file directly for ingestion.
    Supports: .txt, .pdf, .jpg, .jpeg, .png, .xlsx, .xls, .csv
    """
    # Determine file type
    ext = Path(file.filename).suffix.lower()
    file_type_map = {
        ".txt": "whatsapp_text",
        ".pdf": "pdf",
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".xlsx": "excel",
        ".xls": "excel",
        ".csv": "csv",
    }
    
    file_type = file_type_map.get(ext)
    if not file_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Supported: {list(file_type_map.keys())}",
        )
    
    # Save to temp file
    content = await file.read()
    
    if file_type == "whatsapp_text":
        # Text files can be processed directly
        text = content.decode("utf-8", errors="replace")
        result = _run_pipeline(text=text, file_type=file_type)
    else:
        # Binary files need to be saved
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            result = _run_pipeline(file_path=tmp_path, file_type=file_type)
        finally:
            os.unlink(tmp_path)
    
    return result


# ─────────────────────────────────────────────────────────────
# Pub/Sub Push Handler
# ─────────────────────────────────────────────────────────────

@app.post("/on-ingestion-event")
async def on_ingestion_event(envelope: dict, background_tasks: BackgroundTasks):
    """
    Handle Pub/Sub push for ingestion-events topic.
    Called when a file is uploaded via the dashboard.
    """
    from shared.pubsub_client import parse_pubsub_message
    
    try:
        data = parse_pubsub_message(envelope)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    job_id = data.get("job_id", str(uuid4()))
    _jobs[job_id] = IngestionStatus(job_id=job_id, status="queued")
    
    background_tasks.add_task(
        _run_pipeline,
        file_path=data.get("file_uri"),
        file_type=data.get("file_type", "whatsapp_text"),
        job_id=job_id,
    )
    
    return {"status": "accepted", "job_id": job_id}
