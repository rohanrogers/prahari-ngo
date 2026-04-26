"""
Response plan generation orchestrator for the Coordinator Agent.
Manages the Gemini function calling loop that matches volunteers to crises.
"""

import sys
import json
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, PROJECT_ROOT)


async def run_coordinator(
    threat_data: dict,
    mode: str = "pre_staged",
    overrides: dict = None,
) -> dict:
    """
    Run the coordinator agent to create a response plan.
    
    Uses Gemini Pro with function calling to:
    1. Search volunteers semantically
    2. Filter by geography, availability, language
    3. Rank by match quality
    4. Generate outreach messages
    5. Save the plan
    
    Args:
        threat_data: Threat information from Firestore/Pub/Sub
        mode: "pre_staged" (auto) or "active" (confirmed)
        overrides: Optional parameter overrides from human confirmation
    
    Returns:
        Response plan summary
    """
    from shared.gemini_client import generate_with_tools, GEMINI_PRO
    from shared.firestore_client import log_agent_activity
    from .prompts import COORDINATOR_SYSTEM_PROMPT
    from .tools import COORDINATOR_TOOLS, TOOL_IMPLEMENTATIONS
    
    start_time = time.time()
    
    # Apply overrides
    if overrides:
        if "radius_km" in overrides:
            threat_data["location"]["radius_km"] = overrides["radius_km"]
        if "required_skills" in overrides:
            threat_data["required_skills"] = overrides["required_skills"]
    
    # Build the initial prompt
    max_matches = 15 if mode == "pre_staged" else 20
    
    prompt = f"""THREAT DETECTED — MODE: {mode.upper()}

Threat Details:
- Type: {threat_data.get('type', 'unknown')}
- Severity: {threat_data.get('severity', 3)}/5
- Confidence: {threat_data.get('confidence', 0.5)}
- Location: {json.dumps(threat_data.get('location', {}), indent=2)}
- Escalation Window: {threat_data.get('est_escalation_window_min', 60)} minutes

{'Required Skills: ' + json.dumps(overrides.get('required_skills', [])) if overrides and 'required_skills' in overrides else ''}

Find the top {max_matches} best-matched volunteers for this crisis.
Follow the workflow: semantic search → geo filter → availability → language → rank → outreach → save."""
    
    # Function calling loop
    tool_results = []
    max_iterations = 10
    iteration = 0
    final_result = None
    
    # Prepare tools in the format Gemini expects
    tool_declarations = []
    for tool in COORDINATOR_TOOLS:
        tool_declarations.append({
            "function_declarations": [tool]
        })
    
    conversation_history = [prompt]
    
    while iteration < max_iterations:
        iteration += 1
        
        try:
            response = generate_with_tools(
                prompt="\n".join(conversation_history),
                tools=tool_declarations,
                system_instruction=COORDINATOR_SYSTEM_PROMPT,
                model=GEMINI_PRO,
                temperature=0.2,
            )
            
            # Check if response contains function calls
            if not response.candidates:
                break
            
            candidate = response.candidates[0]
            
            # Check for function calls in the response
            has_function_call = False
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        has_function_call = True
                        func_call = part.function_call
                        func_name = func_call.name
                        func_args = dict(func_call.args) if func_call.args else {}
                        
                        logger.info(f"Coordinator calling: {func_name}({json.dumps(func_args)[:200]})")
                        
                        # Execute the tool
                        if func_name in TOOL_IMPLEMENTATIONS:
                            tool_fn = TOOL_IMPLEMENTATIONS[func_name]
                            result = tool_fn(**func_args)
                            tool_results.append({
                                "tool": func_name,
                                "args": func_args,
                                "result": result,
                            })
                            
                            # Track if this was the final save
                            if func_name == "save_response_plan":
                                final_result = result
                            
                            # Add result to conversation
                            conversation_history.append(
                                f"Tool '{func_name}' returned: {json.dumps(result, default=str)[:2000]}"
                            )
                        else:
                            conversation_history.append(
                                f"Tool '{func_name}' not found. Available: {list(TOOL_IMPLEMENTATIONS.keys())}"
                            )
            
            if not has_function_call:
                # Model finished generating — extract any text
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            logger.info(f"Coordinator final output: {part.text[:200]}")
                break
                
        except Exception as e:
            logger.error(f"Coordinator iteration {iteration} failed: {e}")
            conversation_history.append(f"Error: {str(e)}. Please continue with the next step.")
    
    # Log activity
    duration_ms = int((time.time() - start_time) * 1000)
    
    log_agent_activity(
        agent="coordinator",
        action=f"match_volunteers_{mode}",
        reasoning=f"Executed {len(tool_results)} tool calls over {iteration} iterations. "
                  f"Mode: {mode}. Tools used: {[t['tool'] for t in tool_results]}",
        input_summary=f"Threat: {threat_data.get('type')} in {threat_data.get('location', {}).get('district', 'unknown')}",
        output_summary=f"Plan created: {json.dumps(final_result, default=str)[:200]}" if final_result else "No plan saved",
        duration_ms=duration_ms,
        related_entity={
            "type": "threat",
            "id": threat_data.get("id", threat_data.get("threat_id", "")),
        },
    )
    
    return {
        "status": "completed",
        "mode": mode,
        "iterations": iteration,
        "tool_calls": len(tool_results),
        "plan": final_result,
        "duration_ms": duration_ms,
    }
