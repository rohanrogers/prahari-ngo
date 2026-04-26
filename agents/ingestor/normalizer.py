"""
Skill and language normalization for the Ingestor Agent.
Maps raw extracted skills to a standard taxonomy for consistent querying.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Skill Taxonomy — from BLUEPRINT.md Section 6
# Keys are normalized identifiers, values are matching patterns
# ─────────────────────────────────────────────────────────────

SKILL_TAXONOMY: dict[str, list[str]] = {
    "first_aid": ["cpr", "first aid", "medical basics", "nursing", "prathamachikitsa"],
    "medical_professional": ["doctor", "nurse", "paramedic", "ayurveda", "dr", "mbbs"],
    "boat_operation": ["boat", "country boat", "fishing boat", "vallam", "canoe"],
    "driving": ["driver", "driving", "vehicle", "truck", "jeep"],
    "swimming": ["swim", "swimming", "diver", "underwater"],
    "cooking": ["cook", "cooking", "kitchen", "food preparation", "catering"],
    "language_translation": ["translator", "interpreter", "bilingual"],
    "logistics": ["logistics", "supply", "warehouse", "inventory"],
    "coordination": ["coordinator", "organizer", "leader", "supervisor"],
    "counseling": ["counselor", "psychologist", "mental health", "trauma"],
    "technical_rescue": ["rescue", "rope", "climbing", "ndrf trained"],
    "electrical": ["electrician", "wiring", "generator"],
    "construction": ["construction", "carpenter", "mason", "plumber"],
    "veterinary": ["vet", "veterinary", "animal rescue"],
    "social_work": ["social worker", "ngo experience", "field work"],
    "transport_vehicle": ["has car", "has jeep", "has truck", "pickup", "own vehicle"],
    "local_knowledge": ["know the area", "local guide", "backwaters", "familiar with"],
}

# ─────────────────────────────────────────────────────────────
# Language Normalization — ISO 639-1 mapping
# ─────────────────────────────────────────────────────────────

LANGUAGE_NORMALIZATION: dict[str, list[str]] = {
    "ml": ["malayalam", "മലയാളം", "malu"],
    "ta": ["tamil", "தமிழ்"],
    "hi": ["hindi", "हिंदी"],
    "en": ["english"],
    "kn": ["kannada", "ಕನ್ನಡ"],
    "te": ["telugu", "తెలుగు"],
}

# Pre-compile patterns for fast matching
_skill_patterns: dict[str, list[re.Pattern]] = {}
_language_patterns: dict[str, list[re.Pattern]] = {}


def _init_patterns():
    """Compile regex patterns for skill and language matching."""
    global _skill_patterns, _language_patterns
    
    if not _skill_patterns:
        for skill_key, keywords in SKILL_TAXONOMY.items():
            _skill_patterns[skill_key] = [
                re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords
            ]
    
    if not _language_patterns:
        for lang_code, keywords in LANGUAGE_NORMALIZATION.items():
            _language_patterns[lang_code] = [
                re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords
            ]


def normalize_skills(raw_skills: list[str]) -> list[str]:
    """
    Map raw extracted skills to normalized taxonomy keys.
    
    Args:
        raw_skills: List of raw skill strings from Gemini extraction
                    e.g., ["CPR trained", "has country boat", "can cook"]
    
    Returns:
        List of normalized skill keys
        e.g., ["first_aid", "boat_operation", "cooking"]
    """
    _init_patterns()
    
    normalized = set()
    
    for raw in raw_skills:
        raw_lower = raw.lower().strip()
        
        for skill_key, patterns in _skill_patterns.items():
            for pattern in patterns:
                if pattern.search(raw_lower):
                    normalized.add(skill_key)
                    break
    
    result = sorted(normalized)
    logger.debug(f"Normalized skills: {raw_skills} → {result}")
    return result


def normalize_languages(raw_languages: list[str]) -> list[str]:
    """
    Map raw language mentions to ISO 639-1 codes.
    
    Args:
        raw_languages: List of raw language strings
                       e.g., ["Malayalam", "English", "മലയാളം"]
    
    Returns:
        List of ISO 639-1 codes
        e.g., ["ml", "en"]
    """
    _init_patterns()
    
    normalized = set()
    
    for raw in raw_languages:
        raw_lower = raw.lower().strip()
        
        # Check if it's already an ISO code
        if raw_lower in LANGUAGE_NORMALIZATION:
            normalized.add(raw_lower)
            continue
        
        for lang_code, patterns in _language_patterns.items():
            for pattern in patterns:
                if pattern.search(raw_lower):
                    normalized.add(lang_code)
                    break
    
    result = sorted(normalized)
    logger.debug(f"Normalized languages: {raw_languages} → {result}")
    return result


def normalize_phone(raw_phone: str | None) -> str | None:
    """
    Normalize Indian phone numbers to a consistent format.
    
    Args:
        raw_phone: Raw phone string, e.g., "+91 98765 43210", "09876543210", "9876543210"
    
    Returns:
        Normalized 10-digit phone or None if invalid
    """
    if not raw_phone:
        return None
    
    # Strip everything except digits
    digits = re.sub(r"\D", "", raw_phone)
    
    # Remove country code prefixes
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    
    # Validate: must be exactly 10 digits starting with 6-9
    if len(digits) == 10 and digits[0] in "6789":
        return digits
    
    logger.debug(f"Invalid phone number discarded: {raw_phone}")
    return None


def detect_text_language(text: str) -> list[str]:
    """
    Detect languages present in text based on script detection.
    Used to infer languages when not explicitly stated.
    
    Args:
        text: Input text to analyze
    
    Returns:
        List of detected ISO 639-1 language codes
    """
    detected = set()
    
    # Malayalam Unicode range: U+0D00–U+0D7F
    if re.search(r'[\u0D00-\u0D7F]', text):
        detected.add("ml")
    
    # Tamil Unicode range: U+0B80–U+0BFF
    if re.search(r'[\u0B80-\u0BFF]', text):
        detected.add("ta")
    
    # Hindi/Devanagari Unicode range: U+0900–U+097F
    if re.search(r'[\u0900-\u097F]', text):
        detected.add("hi")
    
    # Kannada Unicode range: U+0C80–U+0CFF
    if re.search(r'[\u0C80-\u0CFF]', text):
        detected.add("kn")
    
    # Telugu Unicode range: U+0C00–U+0C7F
    if re.search(r'[\u0C00-\u0C7F]', text):
        detected.add("te")
    
    # If ASCII text is present, likely English
    if re.search(r'[a-zA-Z]{3,}', text):
        detected.add("en")
    
    return sorted(detected)
