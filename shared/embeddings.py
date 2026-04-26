"""
Shared embedding helpers for Prahari agents.
Uses Vertex AI text-embedding model for semantic search and deduplication.
"""

import os
import logging
import numpy as np
from typing import Union

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("PROJECT_ID", "prahari-ngo-rj")
REGION = os.environ.get("REGION", "asia-south1")

# Embedding model — 768-dimensional vectors
EMBEDDING_MODEL = "text-embedding-005"

_client = None


def _get_client() -> genai.Client:
    """Get or create the Gemini client for embeddings."""
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=REGION,
        )
    return _client


def generate_embedding(text: str) -> list[float]:
    """
    Generate a 768-dimensional embedding for a text string.
    Used for volunteer profile embeddings and semantic search queries.
    
    Args:
        text: Input text to embed (volunteer profile summary, search query, etc.)
    
    Returns:
        List of 768 floats
    """
    client = _get_client()
    
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    
    embedding = result.embeddings[0].values
    logger.debug(f"Generated embedding: {len(embedding)} dimensions for text[:{min(50, len(text))}]")
    return embedding


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.
    More efficient than individual calls for bulk ingestion.
    
    Args:
        texts: List of input texts
    
    Returns:
        List of embedding vectors
    """
    client = _get_client()
    
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
    )
    
    embeddings = [e.values for e in result.embeddings]
    logger.info(f"Generated {len(embeddings)} embeddings in batch")
    return embeddings


def cosine_similarity(vec_a: Union[list[float], np.ndarray], vec_b: Union[list[float], np.ndarray]) -> float:
    """
    Calculate cosine similarity between two embedding vectors.
    Used for deduplication (threshold > 0.92) and semantic search ranking.
    
    Args:
        vec_a: First embedding vector
        vec_b: Second embedding vector
    
    Returns:
        Cosine similarity score between -1.0 and 1.0
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot_product / (norm_a * norm_b))


def build_volunteer_profile_text(volunteer: dict) -> str:
    """
    Build a text representation of a volunteer for embedding.
    Combines name, skills, location, and languages into a searchable string.
    
    Args:
        volunteer: Volunteer dict from Firestore
    
    Returns:
        Concatenated profile text for embedding
    """
    parts = []
    
    if volunteer.get("name"):
        parts.append(f"Name: {volunteer['name']}")
    
    if volunteer.get("skills"):
        parts.append(f"Skills: {', '.join(volunteer['skills'])}")
    
    if volunteer.get("skills_raw"):
        parts.append(f"Raw skills: {', '.join(volunteer['skills_raw'])}")
    
    location = volunteer.get("location", {})
    if location:
        loc_parts = [location.get("city", ""), location.get("district", ""), location.get("state", "")]
        loc_str = ", ".join(p for p in loc_parts if p)
        if loc_str:
            parts.append(f"Location: {loc_str}")
    
    if volunteer.get("languages"):
        parts.append(f"Languages: {', '.join(volunteer['languages'])}")
    
    if volunteer.get("availability", {}).get("notes"):
        parts.append(f"Availability: {volunteer['availability']['notes']}")
    
    return " | ".join(parts)


def semantic_search(query: str, volunteers: list[dict], top_k: int = 50) -> list[tuple[dict, float]]:
    """
    Perform semantic search over volunteer profiles.
    Embeds the query, compares against pre-computed volunteer embeddings.
    
    Args:
        query: Natural language search query (e.g., "medical help for flood rescue")
        volunteers: List of volunteer dicts, each must have "embedding" field
        top_k: Maximum number of results to return
    
    Returns:
        List of (volunteer, similarity_score) tuples, sorted descending
    """
    query_embedding = generate_embedding(query)
    
    results = []
    for volunteer in volunteers:
        if not volunteer.get("embedding"):
            continue
        
        score = cosine_similarity(query_embedding, volunteer["embedding"])
        results.append((volunteer, score))
    
    # Sort by similarity descending
    results.sort(key=lambda x: x[1], reverse=True)
    
    return results[:top_k]
