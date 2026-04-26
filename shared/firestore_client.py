"""
Shared Firestore client for all Prahari agents.
Provides typed helpers for the 4 collections: volunteers, live_threats, response_plans, agent_activity.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID", "prahari-ngo-rj")

_db = None


def get_db() -> firestore.Client:
    """Get or create the Firestore client singleton."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
        logger.info(f"Firestore client initialized for project={PROJECT_ID}")
    return _db


# ─────────────────────────────────────────────────────────────
# Collection References
# ─────────────────────────────────────────────────────────────

def volunteers_ref():
    return get_db().collection("volunteers")


def threats_ref():
    return get_db().collection("live_threats")


def plans_ref():
    return get_db().collection("response_plans")


def activity_ref():
    return get_db().collection("agent_activity")


# ─────────────────────────────────────────────────────────────
# Volunteer Operations
# ─────────────────────────────────────────────────────────────

def create_volunteer(data: dict) -> str:
    """
    Create a new volunteer record.
    Generates UUID, sets timestamps.
    Returns the document ID.
    """
    doc_id = str(uuid4())
    now = datetime.now(timezone.utc)
    
    data.update({
        "id": doc_id,
        "created_at": now,
        "updated_at": now,
        "deduped_from": data.get("deduped_from", []),
    })
    
    volunteers_ref().document(doc_id).set(data)
    logger.info(f"Created volunteer: {doc_id} — {data.get('name', 'unknown')}")
    return doc_id


def get_volunteer(doc_id: str) -> dict | None:
    """Fetch a single volunteer by ID."""
    doc = volunteers_ref().document(doc_id).get()
    return doc.to_dict() if doc.exists else None


def get_volunteers_by_district(district: str) -> list[dict]:
    """Fetch all volunteers in a given district."""
    docs = (
        volunteers_ref()
        .where(filter=FieldFilter("location.district", "==", district))
        .stream()
    )
    return [doc.to_dict() for doc in docs]


def get_all_volunteers() -> list[dict]:
    """Fetch all volunteers. Use sparingly — for embedding comparison."""
    docs = volunteers_ref().stream()
    return [doc.to_dict() for doc in docs]


def update_volunteer(doc_id: str, updates: dict):
    """Partial update of a volunteer record."""
    updates["updated_at"] = datetime.now(timezone.utc)
    volunteers_ref().document(doc_id).update(updates)
    logger.info(f"Updated volunteer: {doc_id}")


def merge_volunteer(keep_id: str, merge_id: str):
    """
    Merge a duplicate into the primary record.
    Adds merge_id to the primary's deduped_from list, deletes the duplicate.
    """
    primary = get_volunteer(keep_id)
    if not primary:
        logger.error(f"Primary volunteer {keep_id} not found for merge")
        return
    
    deduped = primary.get("deduped_from", [])
    deduped.append(merge_id)
    update_volunteer(keep_id, {"deduped_from": deduped})
    
    volunteers_ref().document(merge_id).delete()
    logger.info(f"Merged volunteer {merge_id} into {keep_id}")


def get_volunteer_count() -> int:
    """Get total number of volunteers."""
    return len(list(volunteers_ref().select([]).stream()))


# ─────────────────────────────────────────────────────────────
# Threat Operations
# ─────────────────────────────────────────────────────────────

def create_threat(data: dict) -> str:
    """Create a new live threat record."""
    doc_id = f"threat_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    data.update({
        "id": doc_id,
        "status": data.get("status", "monitoring"),
        "created_at": now,
        "updated_at": now,
    })
    
    threats_ref().document(doc_id).set(data)
    logger.info(f"Created threat: {doc_id} — {data.get('type')} in {data.get('location', {}).get('district')}")
    return doc_id


def get_threat(doc_id: str) -> dict | None:
    """Fetch a single threat by ID."""
    doc = threats_ref().document(doc_id).get()
    return doc.to_dict() if doc.exists else None


def get_active_threats() -> list[dict]:
    """Fetch all non-resolved threats."""
    docs = (
        threats_ref()
        .where(filter=FieldFilter("status", "in", ["monitoring", "pre_staged", "confirmed"]))
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )
    return [doc.to_dict() for doc in docs]


def update_threat(doc_id: str, updates: dict):
    """Partial update of a threat record."""
    updates["updated_at"] = datetime.now(timezone.utc)
    threats_ref().document(doc_id).update(updates)
    logger.info(f"Updated threat: {doc_id}")


# ─────────────────────────────────────────────────────────────
# Response Plan Operations
# ─────────────────────────────────────────────────────────────

def create_plan(data: dict) -> str:
    """Create a new response plan."""
    doc_id = f"plan_{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    data.update({
        "id": doc_id,
        "status": data.get("status", "draft"),
        "created_at": now,
        "activated_at": None,
    })
    
    plans_ref().document(doc_id).set(data)
    logger.info(f"Created response plan: {doc_id} for threat {data.get('threat_id')}")
    return doc_id


def get_plan(doc_id: str) -> dict | None:
    """Fetch a single plan by ID."""
    doc = plans_ref().document(doc_id).get()
    return doc.to_dict() if doc.exists else None


def get_plans_for_threat(threat_id: str) -> list[dict]:
    """Fetch all plans associated with a threat."""
    docs = (
        plans_ref()
        .where(filter=FieldFilter("threat_id", "==", threat_id))
        .stream()
    )
    return [doc.to_dict() for doc in docs]


def update_plan(doc_id: str, updates: dict):
    """Partial update of a response plan."""
    plans_ref().document(doc_id).update(updates)
    logger.info(f"Updated plan: {doc_id}")


def activate_plan(doc_id: str):
    """Activate a pre-staged plan (crisis confirmed)."""
    update_plan(doc_id, {
        "status": "active",
        "activated_at": datetime.now(timezone.utc),
    })
    logger.info(f"Plan activated: {doc_id}")


# ─────────────────────────────────────────────────────────────
# Agent Activity Logging
# ─────────────────────────────────────────────────────────────

def log_agent_activity(
    agent: str,
    action: str,
    reasoning: str,
    input_summary: str,
    output_summary: str,
    duration_ms: int,
    related_entity: dict | None = None,
) -> str:
    """
    Log an agent's activity for the real-time dashboard stream.
    
    Args:
        agent: "ingestor" | "watcher" | "coordinator"
        action: What the agent did (e.g., "extract_volunteers", "correlate_signals")
        reasoning: Gemini's thought process / explanation
        input_summary: Brief description of input
        output_summary: Brief description of output
        duration_ms: How long the operation took
        related_entity: Optional {type, id} linking to a volunteer/threat/plan
    
    Returns:
        Activity document ID
    """
    doc_id = f"activity_{uuid4().hex[:12]}"
    
    activity_ref().document(doc_id).set({
        "id": doc_id,
        "agent": agent,
        "action": action,
        "reasoning": reasoning,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc),
        "related_entity": related_entity,
    })
    
    logger.debug(f"Agent activity logged: {agent}/{action}")
    return doc_id
