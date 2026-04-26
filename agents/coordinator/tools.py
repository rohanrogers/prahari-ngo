"""
Function calling tool implementations for the Coordinator Agent.
These are the actual functions that Gemini calls via function calling.
"""

import math
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Tool Definitions (Gemini Function Calling Schemas)
# ─────────────────────────────────────────────────────────────

COORDINATOR_TOOLS = [
    {
        "name": "search_volunteers_semantic",
        "description": "Search the Volunteer Graph using semantic similarity. Use this for skill queries where exact matches aren't enough (e.g., 'medical help needed' should match 'nurse', 'paramedic', 'first aid trained').",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of skills needed",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 50,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "filter_by_geography",
        "description": "Filter a volunteer list by distance from a crisis location.",
        "parameters": {
            "type": "object",
            "properties": {
                "volunteer_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "center_lat": {"type": "number"},
                "center_lon": {"type": "number"},
                "radius_km": {"type": "number"},
            },
            "required": ["volunteer_ids", "center_lat", "center_lon", "radius_km"],
        },
    },
    {
        "name": "filter_by_availability",
        "description": "Filter volunteers by availability in a given time window.",
        "parameters": {
            "type": "object",
            "properties": {
                "volunteer_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "time_window_hours": {
                    "type": "integer",
                    "description": "Hours from now",
                },
                "day_of_week": {"type": "string"},
            },
            "required": ["volunteer_ids", "time_window_hours"],
        },
    },
    {
        "name": "filter_by_language",
        "description": "Filter volunteers by language capability. Critical for regional crises.",
        "parameters": {
            "type": "object",
            "properties": {
                "volunteer_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "required_languages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ISO 639-1 codes, e.g., ['ml', 'en']",
                },
                "require_all": {
                    "type": "boolean",
                    "default": False,
                },
            },
            "required": ["volunteer_ids", "required_languages"],
        },
    },
    {
        "name": "rank_volunteers",
        "description": "Rank filtered volunteers by match quality considering distance, skill overlap, language fit, and availability.",
        "parameters": {
            "type": "object",
            "properties": {
                "volunteer_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "crisis_context": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "required_skills": {"type": "array", "items": {"type": "string"}},
                        "preferred_languages": {"type": "array", "items": {"type": "string"}},
                        "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    },
                },
            },
            "required": ["volunteer_ids", "crisis_context"],
        },
    },
    {
        "name": "generate_outreach_message",
        "description": "Generate a personalized, multilingual outreach message (WhatsApp-ready) for a specific volunteer.",
        "parameters": {
            "type": "object",
            "properties": {
                "volunteer_id": {"type": "string"},
                "crisis_context": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "Crisis type e.g. flood, fire"},
                        "location": {"type": "object", "properties": {
                            "district": {"type": "string"},
                            "state": {"type": "string"},
                        }},
                        "required_skills": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "language": {
                    "type": "string",
                    "description": "ISO 639-1 code from volunteer's languages",
                },
                "channel": {
                    "type": "string",
                    "enum": ["whatsapp", "sms", "call_script"],
                },
                "urgency": {"type": "string"},
            },
            "required": ["volunteer_id", "crisis_context", "language", "channel"],
        },
    },
    {
        "name": "save_response_plan",
        "description": "Finalize and save a response plan to Firestore. Call this when matching is complete.",
        "parameters": {
            "type": "object",
            "properties": {
                "threat_id": {"type": "string"},
                "matched_volunteers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "volunteer_id": {"type": "string"},
                            "match_score": {"type": "number"},
                            "match_reasons": {"type": "array", "items": {"type": "string"}},
                            "assigned_role": {"type": "string"},
                        },
                    },
                },
                "outreach_messages": {"type": "object"},
                "reasoning": {"type": "string"},
            },
            "required": ["threat_id", "matched_volunteers", "reasoning"],
        },
    },
]


# ─────────────────────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────────────────────

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers."""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def execute_search_semantic(query: str, top_k: int = 50) -> list[dict]:
    """Search volunteers semantically using embeddings."""
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.firestore_client import get_all_volunteers
    from shared.embeddings import semantic_search
    
    volunteers = get_all_volunteers()
    results = semantic_search(query, volunteers, top_k=top_k)
    
    return [
        {
            "volunteer_id": vol.get("id"),
            "name": vol.get("name"),
            "skills": vol.get("skills", []),
            "location": vol.get("location", {}),
            "languages": vol.get("languages", []),
            "similarity_score": round(score, 3),
        }
        for vol, score in results
    ]


def execute_filter_geography(
    volunteer_ids: list[str],
    center_lat: float,
    center_lon: float,
    radius_km: float,
) -> list[dict]:
    """Filter volunteers by distance from crisis center."""
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.firestore_client import get_volunteer
    
    results = []
    for vid in volunteer_ids:
        vol = get_volunteer(vid)
        if not vol:
            continue
        
        vol_lat = vol.get("location", {}).get("lat", 0)
        vol_lon = vol.get("location", {}).get("lon", 0)
        
        if vol_lat == 0 and vol_lon == 0:
            continue
        
        distance = haversine_distance(center_lat, center_lon, vol_lat, vol_lon)
        
        if distance <= radius_km:
            results.append({
                "volunteer_id": vid,
                "name": vol.get("name"),
                "distance_km": round(distance, 1),
            })
    
    results.sort(key=lambda x: x["distance_km"])
    return results


def execute_filter_availability(
    volunteer_ids: list[str],
    time_window_hours: int,
    day_of_week: str = None,
) -> list[dict]:
    """Filter volunteers by availability."""
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.firestore_client import get_volunteer
    
    now = datetime.now(timezone.utc)
    current_day = day_of_week or now.strftime("%A").lower()
    
    results = []
    for vid in volunteer_ids:
        vol = get_volunteer(vid)
        if not vol:
            continue
        
        availability = vol.get("availability", {})
        
        # Check day availability
        available_days = [d.lower() for d in availability.get("days", [])]
        hours = availability.get("hours", "")
        
        # If no availability specified, assume available (better than excluding)
        if not available_days or current_day in available_days or "24x7" in hours.lower():
            results.append({
                "volunteer_id": vid,
                "name": vol.get("name"),
                "availability": hours or "not specified",
            })
    
    return results


def execute_filter_language(
    volunteer_ids: list[str],
    required_languages: list[str],
    require_all: bool = False,
) -> list[dict]:
    """Filter volunteers by language capability."""
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.firestore_client import get_volunteer
    
    required_set = set(lang.lower() for lang in required_languages)
    
    results = []
    for vid in volunteer_ids:
        vol = get_volunteer(vid)
        if not vol:
            continue
        
        vol_languages = set(lang.lower() for lang in vol.get("languages", []))
        
        if require_all:
            match = required_set.issubset(vol_languages)
        else:
            match = bool(required_set & vol_languages)
        
        if match:
            matched_langs = list(required_set & vol_languages)
            results.append({
                "volunteer_id": vid,
                "name": vol.get("name"),
                "languages": vol.get("languages", []),
                "matched_languages": matched_langs,
            })
    
    return results


def execute_rank_volunteers(
    volunteer_ids: list[str],
    crisis_context: dict,
) -> list[dict]:
    """
    Rank volunteers by match quality.
    Score = weighted combination of distance, skill overlap, language fit.
    """
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.firestore_client import get_volunteer
    
    required_skills = set(crisis_context.get("required_skills", []))
    preferred_langs = set(crisis_context.get("preferred_languages", []))
    crisis_lat = crisis_context.get("lat", 0)
    crisis_lon = crisis_context.get("lon", 0)
    urgency = crisis_context.get("urgency", "medium")
    
    # Urgency weights
    urgency_weights = {
        "critical": {"distance": 0.4, "skills": 0.35, "language": 0.25},
        "high": {"distance": 0.35, "skills": 0.35, "language": 0.3},
        "medium": {"distance": 0.3, "skills": 0.4, "language": 0.3},
        "low": {"distance": 0.25, "skills": 0.4, "language": 0.35},
    }
    weights = urgency_weights.get(urgency, urgency_weights["medium"])
    
    ranked = []
    for vid in volunteer_ids:
        vol = get_volunteer(vid)
        if not vol:
            continue
        
        # Distance score (closer = higher)
        vol_lat = vol.get("location", {}).get("lat", 0)
        vol_lon = vol.get("location", {}).get("lon", 0)
        if vol_lat and vol_lon and crisis_lat and crisis_lon:
            distance = haversine_distance(crisis_lat, crisis_lon, vol_lat, vol_lon)
            distance_score = max(0, 1 - (distance / 50))  # 50km = 0 score
        else:
            distance = 999
            distance_score = 0.0
        
        # Skill overlap score
        vol_skills = set(vol.get("skills", []))
        if required_skills:
            skill_score = len(vol_skills & required_skills) / len(required_skills)
        else:
            skill_score = 0.5  # No requirements = neutral
        
        # Language score
        vol_langs = set(vol.get("languages", []))
        if preferred_langs:
            lang_score = len(vol_langs & preferred_langs) / len(preferred_langs)
        else:
            lang_score = 0.5
        
        # Composite score
        total_score = (
            weights["distance"] * distance_score
            + weights["skills"] * skill_score
            + weights["language"] * lang_score
        )
        
        # Build match reasons
        reasons = []
        if distance < 5:
            reasons.append(f"within {distance:.0f}km")
        elif distance < 15:
            reasons.append(f"{distance:.0f}km away")
        
        matched_skills = vol_skills & required_skills
        if matched_skills:
            reasons.append(f"has {', '.join(matched_skills)}")
        
        matched_langs = vol_langs & preferred_langs
        if matched_langs:
            reasons.append(f"speaks {', '.join(matched_langs)}")
        
        ranked.append({
            "volunteer_id": vid,
            "name": vol.get("name"),
            "match_score": round(total_score, 3),
            "match_reasons": reasons,
            "distance_km": round(distance, 1),
            "skills": list(vol_skills),
            "languages": list(vol_langs),
        })
    
    ranked.sort(key=lambda x: x["match_score"], reverse=True)
    return ranked


def execute_generate_outreach(
    volunteer_id: str,
    crisis_context: dict,
    language: str,
    channel: str,
    urgency: str = "high",
) -> dict:
    """Generate a personalized outreach message for a volunteer."""
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.firestore_client import get_volunteer
    from shared.gemini_client import generate_text
    
    vol = get_volunteer(volunteer_id)
    if not vol:
        return {"error": f"Volunteer {volunteer_id} not found"}
    
    # Use Gemini for natural, personalized message generation
    prompt = f"""Generate a {channel} outreach message for a volunteer during a crisis.

Volunteer:
- Name: {vol.get('name')}
- Skills: {', '.join(vol.get('skills', []))}
- Languages: {', '.join(vol.get('languages', []))}
- Location: {vol.get('location', {}).get('district', '')}, {vol.get('location', {}).get('state', '')}

Crisis:
- Type: {crisis_context.get('type', 'emergency')}
- Location: {crisis_context.get('location', {}).get('district', '')}, {crisis_context.get('location', {}).get('state', '')}
- Urgency: {urgency}
- Required Skills: {', '.join(crisis_context.get('required_skills', []))}

LANGUAGE: Write the message in {language} (ISO 639-1 code: ml=Malayalam, hi=Hindi, ta=Tamil, en=English)
TONE: Urgent but respectful. NGO volunteers are not employees.
FORMAT: WhatsApp-ready with emojis. Include clear YES/NO response mechanism.
KEEP IT UNDER 200 WORDS.

Return ONLY the message text, no explanation."""
    
    message = generate_text(
        prompt=prompt,
        temperature=0.3,
        max_tokens=1024,
    )
    
    return {
        "volunteer_id": volunteer_id,
        "volunteer_name": vol.get("name"),
        "language": language,
        "channel": channel,
        "message": message.strip(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def execute_save_plan(
    threat_id: str,
    matched_volunteers: list[dict],
    outreach_messages: dict = None,
    reasoning: str = "",
    mode: str = "pre_staged",
) -> dict:
    """Save a response plan to Firestore."""
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.firestore_client import create_plan, update_threat
    
    plan_data = {
        "threat_id": threat_id,
        "status": mode,
        "matched_volunteers": matched_volunteers,
        "outreach_messages": outreach_messages or {},
        "coordinator_reasoning": reasoning,
        "timeline": [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": f"Response plan created ({mode})",
                "actor": "coordinator",
            }
        ],
    }
    
    plan_id = create_plan(plan_data)
    
    # Update the threat with the plan reference
    update_threat(threat_id, {
        "pre_staged_plan_id": plan_id,
        "status": "pre_staged" if mode == "pre_staged" else "confirmed",
    })
    
    return {"plan_id": plan_id, "status": mode, "matched_count": len(matched_volunteers)}


# Tool name → implementation mapping
TOOL_IMPLEMENTATIONS = {
    "search_volunteers_semantic": execute_search_semantic,
    "filter_by_geography": execute_filter_geography,
    "filter_by_availability": execute_filter_availability,
    "filter_by_language": execute_filter_language,
    "rank_volunteers": execute_rank_volunteers,
    "generate_outreach_message": execute_generate_outreach,
    "save_response_plan": execute_save_plan,
}
