"""
ingestion/pdf_loader.py
────────────────────────
Loads SEBI PDF files from data/pdfs/, extracts text page-by-page using PyMuPDF,
and chunks the text into overlapping windows while preserving page-number metadata.

Each chunk is a dict:
  {
    "text":     str,
    "metadata": {
        "source":     str,   # e.g. "SEBI Mutual Funds Guide"
        "title":      str,   # Document title
        "page":       int,   # 1-indexed page number
        "type":       "pdf",
        "chunk_id":   str,   # Unique identifier for deduplication
    }
  }
"""

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # PyMuPDF fallback
import logging
from pathlib import Path
from config.settings import PDF_DIR, SEBI_PDF_SOURCES, CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Naively chunk text by word count (approximates token count).
    Returns list of overlapping text windows.
    """
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def load_pdf(source_config: dict) -> list[dict]:
    """
    Load and chunk a single PDF file defined in source_config.

    Args:
        source_config: A dict from SEBI_PDF_SOURCES (filename, title, source_tag).

    Returns:
        List of chunk dicts with text and metadata.
    """
    filepath = PDF_DIR / source_config["filename"]
    if not filepath.exists():
        logger.warning(f"PDF not found, skipping: {filepath}")
        return []

    chunks = []
    try:
        doc = fitz.open(str(filepath))
        logger.info(f"Loaded PDF: {source_config['title']} ({len(doc)} pages)")

        for page_num in range(len(doc)):
            page = doc[page_num]
            raw_text = page.get_text("text")

            # Skip near-empty pages (headers/footers only)
            if len(raw_text.strip()) < 50:
                continue

            page_chunks = _chunk_text(raw_text, CHUNK_SIZE, CHUNK_OVERLAP)
            for idx, chunk_text in enumerate(page_chunks):
                chunk_id = f"{source_config['filename']}_p{page_num + 1}_c{idx}"
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "source":    source_config["source_tag"],
                        "title":     source_config["title"],
                        "page":      page_num + 1,
                        "type":      "pdf",
                        "chunk_id":  chunk_id,
                        "filename":  source_config["filename"],
                    }
                })
        doc.close()
        logger.info(f"  → Produced {len(chunks)} chunks from '{source_config['title']}'")

    except Exception as e:
        logger.error(f"Error loading PDF '{source_config['filename']}': {e}")

    return chunks


def load_all_pdfs() -> list[dict]:
    """
    Load and chunk all PDFs defined in settings.SEBI_PDF_SOURCES.

    Returns:
        Combined list of all chunks across all PDF files.
    """
    all_chunks = []
    for source_config in SEBI_PDF_SOURCES:
        chunks = load_pdf(source_config)
        all_chunks.extend(chunks)

    logger.info(f"Total PDF chunks loaded: {len(all_chunks)}")
    return all_chunks


def format_pdf_citation(metadata: dict) -> str:
    """
    Format a human-readable citation string from PDF chunk metadata.

    Example: [Source: SEBI Mutual Funds Guide, Pg 7]
    """
    return f"[Source: {metadata.get('source', 'SEBI Document')}, Pg {metadata.get('page', '?')}]"
