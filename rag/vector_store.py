"""
rag/vector_store.py
────────────────────
ChromaDB in-memory vector store manager.
Handles collection creation, document upsert, and query.

Using in-memory client means the index is rebuilt each time the app starts
(ideal for lightweight in-memory deployment — fast with ~5 small PDFs + 2 videos).
"""

import logging
import chromadb
from typing import Any
from chromadb.config import Settings
from config.settings import CHROMA_COLLECTION_NAME

logger = logging.getLogger(__name__)

# ── Singleton in-memory client ─────────────────────────────────────────────────
_client: Any = None
_collection: Any = None


def _get_client() -> Any:
    global _client
    if _client is None:
        _client = chromadb.Client(Settings(anonymized_telemetry=False))
        logger.info("ChromaDB in-memory client initialized")
    return _client


def get_collection() -> Any:
    """Get or create the main knowledge base collection."""
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},   # cosine similarity for semantic search
        )
        logger.info(f"Collection '{CHROMA_COLLECTION_NAME}' ready")
    return _collection


def upsert_chunks(chunks: list[dict], embeddings: list[list[float]]) -> None:
    """
    Upsert document chunks and their embeddings into ChromaDB.

    Args:
        chunks:     List of {"text": str, "metadata": dict} dicts.
        embeddings: Parallel list of embedding vectors.
    """
    if not chunks:
        logger.warning("upsert_chunks called with empty chunk list")
        return

    collection = get_collection()
    ids       = [c["metadata"]["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # ChromaDB metadata values must be str/int/float/bool
    # Sanitize any None values
    safe_metadatas = []
    for meta in metadatas:
        safe_meta = {k: (v if v is not None else "") for k, v in meta.items()}
        safe_metadatas.append(safe_meta)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=safe_metadatas,
    )
    logger.info(f"Upserted {len(chunks)} chunks into '{CHROMA_COLLECTION_NAME}'")


def query_collection(
    query_embedding: list[float],
    top_k: int = 5,
    source_type: str | None = None,
) -> list[dict]:
    """
    Query the collection for semantically similar chunks.

    Args:
        query_embedding: Embedding vector of the user query.
        top_k:           Number of top results to return.
        source_type:     Optional filter — "pdf" or "youtube".

    Returns:
        List of result dicts: {"text": str, "metadata": dict, "distance": float}
    """
    collection = get_collection()
    where = {"type": source_type} if source_type else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    # Flatten ChromaDB result format into clean list
    output = []
    docs      = results.get("documents", [[]])[0]
    metas     = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        output.append({
            "text":     doc,
            "metadata": meta,
            "distance": dist,
        })

    logger.debug(f"Query returned {len(output)} results (top_k={top_k})")
    return output


def get_collection_count() -> int:
    """Return the number of documents currently in the collection."""
    return get_collection().count()


def reset_collection() -> None:
    """Drop and recreate the collection (useful for re-indexing)."""
    global _collection
    client = _get_client()
    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        pass
    _collection = None
    get_collection()
    logger.info("Collection reset complete")
