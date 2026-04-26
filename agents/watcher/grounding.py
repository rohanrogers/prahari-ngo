"""
Gemini + Google Search grounding for the Watcher Agent.
Verifies correlated signals against live web data before emitting threats.
"""

import json
import logging

from .schemas import ThreatAssessment, EvidenceItem, ThreatLocation
from .prompts import WATCHER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def ground_threat(
    signals_json: str,
    base_confidence: float,
) -> ThreatAssessment:
    """
    Use Gemini with Google Search grounding to analyze correlated signals
    and produce a final threat assessment.
    
    Args:
        signals_json: JSON string of correlated signals
        base_confidence: Pre-computed confidence from multi-source agreement
    
    Returns:
        Complete ThreatAssessment with grounded facts
    """
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent))
    from shared.gemini_client import generate_with_grounding
    
    prompt = f"""SIGNALS:
{signals_json}

PRE-COMPUTED CONFIDENCE FROM MULTI-SOURCE AGREEMENT: {base_confidence}

Analyze these correlated signals. Use Google Search to verify if this is a real emerging crisis.
Return your assessment as JSON."""
    
    try:
        response = generate_with_grounding(
            prompt=prompt,
            system_instruction=WATCHER_SYSTEM_PROMPT,
            temperature=0.2,
        )
        
        # Parse Gemini response
        response_text = response.text
        
        # Try to extract JSON from response
        try:
            # Handle potential code block wrapping
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            data = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Gemini grounding response as JSON: {response_text[:200]}")
            # Return a conservative assessment
            return ThreatAssessment(
                is_real_threat=base_confidence >= 0.7,
                confidence=base_confidence,
                reasoning=f"Grounding analysis failed. Raw multi-source confidence: {base_confidence}",
            )
        
        # Build threat assessment from Gemini output
        location_data = data.get("location", {})
        evidence_data = data.get("evidence_chain", [])
        
        evidence = [
            EvidenceItem(
                source=e.get("source", "unknown"),
                timestamp=e.get("timestamp", ""),
                content=e.get("content", ""),
                url=e.get("url"),
                weight=e.get("weight", 0.5),
            )
            for e in evidence_data
        ]
        
        assessment = ThreatAssessment(
            is_real_threat=data.get("is_real_threat", False),
            type=data.get("type", "other"),
            severity=data.get("severity", 1),
            confidence=data.get("confidence", base_confidence),
            location=ThreatLocation(
                city=location_data.get("city", ""),
                district=location_data.get("district", ""),
                state=location_data.get("state", ""),
                lat=location_data.get("lat", 0.0),
                lon=location_data.get("lon", 0.0),
                radius_km=location_data.get("radius_km", 15.0),
            ),
            est_escalation_window_min=data.get("est_escalation_window_min", 60),
            reasoning=data.get("reasoning", ""),
            evidence_chain=evidence,
            grounded_facts=data.get("grounded_facts", []),
        )
        
        # Extract grounding metadata if available
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                grounding = candidate.grounding_metadata
                if hasattr(grounding, 'search_entry_point'):
                    logger.info(f"Grounding search used: {grounding.search_entry_point}")
        
        logger.info(
            f"Grounded assessment: type={assessment.type}, "
            f"confidence={assessment.confidence:.2f}, "
            f"grounded_facts={len(assessment.grounded_facts)}"
        )
        
        return assessment
        
    except Exception as e:
        logger.error(f"Grounding analysis failed: {e}")
        return ThreatAssessment(
            is_real_threat=base_confidence >= 0.7,
            confidence=base_confidence,
            reasoning=f"Grounding failed with error: {str(e)}. Falling back to base confidence.",
        )
