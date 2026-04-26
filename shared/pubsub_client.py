"""
Shared Pub/Sub client for Prahari agents.
Handles publishing and receiving messages across the 3 topics:
- threats-detected (Watcher → Coordinator)
- crisis-confirmed (Dashboard → Coordinator)
- ingestion-events (Dashboard → Ingestor)
"""

import os
import json
import logging
from typing import Any

from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID", "prahari-ngo-rj")

# Topic names (must match infra/pubsub_topics.sh)
TOPIC_THREATS_DETECTED = "threats-detected"
TOPIC_CRISIS_CONFIRMED = "crisis-confirmed"
TOPIC_INGESTION_EVENTS = "ingestion-events"

_publisher = None


def get_publisher() -> pubsub_v1.PublisherClient:
    """Get or create the Pub/Sub publisher singleton."""
    global _publisher
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
        logger.info("Pub/Sub publisher initialized")
    return _publisher


def _topic_path(topic_name: str) -> str:
    """Build the full topic path."""
    publisher = get_publisher()
    return publisher.topic_path(PROJECT_ID, topic_name)


def publish_message(topic_name: str, data: dict, **attributes) -> str:
    """
    Publish a JSON message to a Pub/Sub topic.
    
    Args:
        topic_name: One of the TOPIC_* constants
        data: Message payload (will be JSON-serialized)
        **attributes: Optional message attributes
    
    Returns:
        Published message ID
    """
    publisher = get_publisher()
    topic = _topic_path(topic_name)
    
    message_bytes = json.dumps(data).encode("utf-8")
    future = publisher.publish(topic, message_bytes, **attributes)
    message_id = future.result()
    
    logger.info(f"Published to {topic_name}: message_id={message_id}")
    return message_id


def publish_threat_detected(
    threat_id: str,
    threat_type: str,
    severity: int,
    confidence: float,
    location: dict,
    trigger: str = "auto",
) -> str:
    """
    Publish a threat detection event for the Coordinator to pick up.
    
    Args:
        threat_id: Unique threat identifier
        threat_type: "flood" | "fire" | "stampede" | etc.
        severity: 1-5
        confidence: 0.0-1.0
        location: {district, state, lat, lon, radius_km}
        trigger: "auto" or "manual"
    
    Returns:
        Message ID
    """
    from datetime import datetime, timezone
    
    return publish_message(TOPIC_THREATS_DETECTED, {
        "threat_id": threat_id,
        "type": threat_type,
        "severity": severity,
        "confidence": confidence,
        "location": location,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trigger": trigger,
    })


def publish_crisis_confirmed(
    threat_id: str,
    confirmed_by: str,
    override_params: dict | None = None,
) -> str:
    """
    Publish a crisis confirmation event.
    Triggered from the dashboard when a human operator confirms a threat.
    
    Args:
        threat_id: ID of the confirmed threat
        confirmed_by: Email of the confirming user
        override_params: Optional overrides {radius_km, required_skills}
    
    Returns:
        Message ID
    """
    from datetime import datetime, timezone
    
    return publish_message(TOPIC_CRISIS_CONFIRMED, {
        "threat_id": threat_id,
        "confirmed_by": confirmed_by,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "override_params": override_params or {},
    })


def publish_ingestion_event(
    job_id: str,
    file_uri: str,
    file_type: str,
    user_id: str,
) -> str:
    """
    Publish a file upload event for the Ingestor to process.
    
    Args:
        job_id: Unique job identifier
        file_uri: GCS URI of the uploaded file
        file_type: "whatsapp_text" | "pdf" | "image" | "excel" | "csv"
        user_id: Uploading user's ID
    
    Returns:
        Message ID
    """
    from datetime import datetime, timezone
    
    return publish_message(TOPIC_INGESTION_EVENTS, {
        "job_id": job_id,
        "file_uri": file_uri,
        "file_type": file_type,
        "user_id": user_id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })


def parse_pubsub_message(envelope: dict) -> dict:
    """
    Parse incoming Pub/Sub push message envelope.
    Used by Cloud Run HTTP endpoints receiving Pub/Sub pushes.
    
    Args:
        envelope: The raw Pub/Sub push envelope from the HTTP request body
    
    Returns:
        Decoded message data as dict
    """
    import base64
    
    if not envelope or "message" not in envelope:
        raise ValueError("Invalid Pub/Sub envelope: missing 'message'")
    
    message = envelope["message"]
    
    if "data" not in message:
        raise ValueError("Invalid Pub/Sub message: missing 'data'")
    
    data_bytes = base64.b64decode(message["data"])
    return json.loads(data_bytes)
