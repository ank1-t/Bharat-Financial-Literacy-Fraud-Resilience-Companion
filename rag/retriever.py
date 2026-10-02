"""
rag/retriever.py
─────────────────
Semantic retrieval layer. Embeds the user query and fetches
the most relevant chunks from ChromaDB.
"""

import logging
from rag.embedder import embed_query
from rag.vector_store import query_collection
from config.settings import TOP_K_RETRIEVAL

logger = logging.getLogger(__name__)


def retrieve(
    query: str,
    top_k: int = TOP_K_RETRIEVAL,
    source_type: str | None = None,
) -> list[dict]:
    """
    Retrieve the top-k most relevant knowledge base chunks for a user query.

    Args:
        query:       The user's question (Hindi or English).
        top_k:       How many chunks to return.
        source_type: Optional filter — "pdf" or "youtube" (None = both).

    Returns:
        List of result dicts: {"text": str, "metadata": dict, "distance": float}
    """
    if not query or not query.strip():
        logger.warning("retrieve called with empty query")
        return []

    logger.info(f"Retrieving top-{top_k} chunks for query: '{query[:80]}...'")
    query_embedding = embed_query(query)

    if not query_embedding:
        logger.error("Failed to generate query embedding")
        return []

    results = query_collection(query_embedding, top_k=top_k, source_type=source_type)
    logger.info(f"Retrieved {len(results)} chunks")
    return results


def format_context_block(results: list[dict]) -> str:
    """
    Format retrieved chunks into a structured context string for the LLM prompt.
    Each chunk includes its citation tag so the model can reference it.

    Args:
        results: List of result dicts from retrieve().

    Returns:
        Formatted context string.
    """
    if not results:
        return "No relevant context found in the knowledge base."

    context_parts = []
    for i, result in enumerate(results, 1):
        meta = result["metadata"]
        source_type = meta.get("type", "unknown")

        if source_type == "pdf":
            citation = f"[Source: {meta.get('source', 'SEBI')}, Pg {meta.get('page', '?')}]"
        elif source_type == "youtube":
            citation = (
                f"[Video: {meta.get('source', 'YouTube')}, "
                f"Time {meta.get('timestamp', '00:00')}]"
            )
        else:
            citation = f"[Source: {meta.get('source', 'Knowledge Base')}]"

        context_parts.append(
            f"--- Context {i} {citation} ---\n{result['text']}\n"
        )

    return "\n".join(context_parts)
