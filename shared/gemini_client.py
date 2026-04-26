"""
Shared Gemini client for all Prahari agents.
Initializes Vertex AI / Gemini SDK with project-level configuration.
"""

import os
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Project configuration
PROJECT_ID = os.environ.get("PROJECT_ID", "prahari-ngo-rj")
REGION = os.environ.get("REGION", "asia-south1")

# Model identifiers
GEMINI_FLASH = "gemini-2.0-flash"
GEMINI_PRO = "gemini-2.0-pro"

# Initialize the client
_client = None


def get_client() -> genai.Client:
    """Get or create the Gemini client singleton."""
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=REGION,
        )
        logger.info(f"Gemini client initialized for project={PROJECT_ID}, region={REGION}")
    return _client


def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    model: str = GEMINI_FLASH,
    temperature: float = 0.1,
    max_tokens: int = 8192,
    response_mime_type: str | None = None,
) -> str:
    """
    Generate text using Gemini.
    
    Args:
        prompt: The user prompt
        system_instruction: Optional system instruction for the model
        model: Model identifier (default: Flash for speed)
        temperature: Sampling temperature (default: 0.1 for deterministic)
        max_tokens: Maximum output tokens
        response_mime_type: Optional MIME type for structured output (e.g., "application/json")
    
    Returns:
        Generated text string
    """
    client = get_client()
    
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
    )
    
    if response_mime_type:
        config.response_mime_type = response_mime_type
    
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    
    logger.info(f"Gemini response: model={model}, tokens_used={response.usage_metadata}")
    return response.text


def generate_multimodal(
    parts: list,
    system_instruction: str | None = None,
    model: str = GEMINI_FLASH,
    temperature: float = 0.1,
    max_tokens: int = 8192,
    response_mime_type: str | None = None,
) -> str:
    """
    Generate content from multimodal input (text + images/PDFs).
    
    Args:
        parts: List of content parts (text strings, Part objects for images/files)
        system_instruction: Optional system instruction
        model: Model identifier
        temperature: Sampling temperature
        max_tokens: Maximum output tokens
        response_mime_type: Optional MIME type for structured output
    
    Returns:
        Generated text string
    """
    client = get_client()
    
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
    )
    
    if response_mime_type:
        config.response_mime_type = response_mime_type
    
    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=config,
    )
    
    logger.info(f"Gemini multimodal response: model={model}")
    return response.text


def generate_with_tools(
    prompt: str,
    tools: list[dict],
    system_instruction: str | None = None,
    model: str = GEMINI_PRO,
    temperature: float = 0.2,
    max_tokens: int = 8192,
) -> types.GenerateContentResponse:
    """
    Generate content with function calling tools.
    Used by the Coordinator agent for semantic search, filtering, ranking.
    
    Args:
        prompt: The user prompt with crisis context
        tools: List of function tool definitions
        system_instruction: System instruction for the Coordinator
        model: Model identifier (default: Pro for complex reasoning)
        temperature: Sampling temperature
        max_tokens: Maximum output tokens
    
    Returns:
        Full response object (caller handles function call extraction)
    """
    client = get_client()
    
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
        tools=tools,
    )
    
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    
    logger.info(f"Gemini tool response: model={model}, candidates={len(response.candidates)}")
    return response


def generate_with_grounding(
    prompt: str,
    system_instruction: str | None = None,
    model: str = GEMINI_FLASH,
    temperature: float = 0.2,
    max_tokens: int = 8192,
) -> types.GenerateContentResponse:
    """
    Generate content with Google Search grounding.
    Used by the Watcher agent to verify threat signals against live data.
    
    Args:
        prompt: The analysis prompt with signal data
        system_instruction: System instruction for the Watcher
        model: Model identifier
        temperature: Sampling temperature
        max_tokens: Maximum output tokens
    
    Returns:
        Full response object (includes grounding metadata)
    """
    client = get_client()
    
    google_search_tool = types.Tool(
        google_search=types.GoogleSearch()
    )
    
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
        tools=[google_search_tool],
    )
    
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )
    
    logger.info(f"Gemini grounded response: model={model}")
    return response


def upload_file(file_path: str, mime_type: str | None = None) -> types.Part:
    """
    Upload a file (image, PDF) for multimodal processing.
    
    Args:
        file_path: Local path or GCS URI to the file
        mime_type: MIME type override
    
    Returns:
        Part object for use in generate_multimodal
    """
    client = get_client()
    
    if file_path.startswith("gs://"):
        return types.Part.from_uri(file_uri=file_path, mime_type=mime_type)
    
    uploaded = client.files.upload(path=file_path)
    logger.info(f"File uploaded: {file_path} → {uploaded.uri}")
    return types.Part.from_uri(file_uri=uploaded.uri, mime_type=uploaded.mime_type)
