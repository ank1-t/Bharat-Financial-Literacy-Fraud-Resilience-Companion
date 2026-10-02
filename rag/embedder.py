"""
rag/embedder.py
────────────────
Thin wrapper around the Gemini text-embedding-004 model.
Handles both single texts and batched lists for efficient indexing.
"""

import logging
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# Configure the Gemini client once at import time
genai.configure(api_key=GEMINI_API_KEY)

# Maximum texts per batch (Gemini API limit)
_BATCH_SIZE = 100


def embed_texts(texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
    """
    Embed a list of texts using Gemini text-embedding-004.

    Args:
        texts:     List of strings to embed.
        task_type: "retrieval_document" for indexing, "retrieval_query" for queries.

    Returns:
        List of embedding vectors (list of floats).
    """
    if not texts:
        return []

    all_embeddings = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=batch,
                task_type=task_type,
            )
            # Result is {"embedding": [...]} for single or list of embeddings for batch
            embeddings = result.get("embedding", [])
            # Normalize: single string returns a flat list; batch returns list of lists
            if batch and isinstance(embeddings[0], float):
                embeddings = [embeddings]
            all_embeddings.extend(embeddings)
            logger.debug(f"Embedded batch {i // _BATCH_SIZE + 1}: {len(batch)} texts")
        except Exception as e:
            logger.error(f"Embedding error for batch {i}: {e}")
            raise

    return all_embeddings


def embed_query(query: str) -> list[float]:
    """
    Embed a single user query string for retrieval.

    Args:
        query: The user's question.

    Returns:
        Single embedding vector.
    """
    embeddings = embed_texts([query], task_type="retrieval_query")
    return embeddings[0] if embeddings else []
