"""
Embedding-based deduplication for the Ingestor Agent.
Implements 3-rule dedup strategy from BLUEPRINT.md Section 6:
  Rule 1: Exact phone match = definite duplicate
  Rule 2: Embedding cosine similarity > 0.92 + same district = likely duplicate
  Rule 3: Name fuzzy match > 0.85 + same district + overlapping skills
"""

import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


def fuzzy_ratio(s1: str, s2: str) -> float:
    """
    Calculate fuzzy string similarity ratio (0.0-1.0).
    Uses SequenceMatcher for name comparison.
    """
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1.lower().strip(), s2.lower().strip()).ratio()


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def is_duplicate(
    new_volunteer: dict,
    existing_volunteer: dict,
    cosine_fn=None,
) -> tuple[bool, float]:
    """
    Determine if new_volunteer is a duplicate of existing_volunteer.
    
    Implements the 3-rule dedup strategy:
      Rule 1: Exact phone match = definite duplicate (confidence 1.0)
      Rule 2: Embedding cosine > 0.92 + same district = likely duplicate
      Rule 3: Name fuzzy > 0.85 + same district + skill overlap > 0.3
    
    Args:
        new_volunteer: Dict with volunteer fields
        existing_volunteer: Dict with volunteer fields
        cosine_fn: Optional cosine similarity function (injected for testing)
    
    Returns:
        (is_dup: bool, confidence: float)
    """
    # Rule 1: Exact phone match
    new_phone = new_volunteer.get("phone")
    existing_phone = existing_volunteer.get("phone")
    if new_phone and existing_phone and new_phone == existing_phone:
        logger.info(f"Dedup: Phone match {new_phone}")
        return True, 1.0
    
    # Rule 2: Embedding similarity + same district
    new_embedding = new_volunteer.get("embedding")
    existing_embedding = existing_volunteer.get("embedding")
    new_district = new_volunteer.get("location", {}).get("district", "")
    existing_district = existing_volunteer.get("location", {}).get("district", "")
    same_district = (
        new_district and existing_district 
        and new_district.lower() == existing_district.lower()
    )
    
    if new_embedding and existing_embedding and cosine_fn:
        similarity = cosine_fn(new_embedding, existing_embedding)
        if similarity > 0.92 and same_district:
            logger.info(
                f"Dedup: Embedding match ({similarity:.3f}) + same district "
                f"({new_district}): {new_volunteer.get('name')} ≈ {existing_volunteer.get('name')}"
            )
            return True, similarity
    
    # Rule 3: Name fuzzy match + same district + skill overlap
    new_name = new_volunteer.get("name", "")
    existing_name = existing_volunteer.get("name", "")
    name_sim = fuzzy_ratio(new_name, existing_name)
    
    new_skills = set(new_volunteer.get("skills", []))
    existing_skills = set(existing_volunteer.get("skills", []))
    skill_overlap = jaccard_similarity(new_skills, existing_skills)
    
    if name_sim > 0.85 and same_district and skill_overlap > 0.3:
        combined = (name_sim + skill_overlap) / 2
        logger.info(
            f"Dedup: Name match ({name_sim:.2f}) + district ({new_district}) "
            f"+ skills ({skill_overlap:.2f}): {new_name} ≈ {existing_name}"
        )
        return True, combined
    
    return False, 0.0


def find_duplicates(
    new_volunteer: dict,
    existing_volunteers: list[dict],
    cosine_fn=None,
) -> list[tuple[dict, float]]:
    """
    Find all duplicates of a new volunteer in the existing set.
    
    Args:
        new_volunteer: The volunteer to check
        existing_volunteers: List of existing volunteer dicts
        cosine_fn: Cosine similarity function
    
    Returns:
        List of (existing_volunteer, confidence) tuples for matches
    """
    duplicates = []
    
    for existing in existing_volunteers:
        is_dup, confidence = is_duplicate(new_volunteer, existing, cosine_fn)
        if is_dup:
            duplicates.append((existing, confidence))
    
    # Sort by confidence descending
    duplicates.sort(key=lambda x: x[1], reverse=True)
    return duplicates
