"""
config/settings.py
──────────────────
Centralized configuration for the Bharat Financial Literacy & Fraud Resilience Companion.
All tuneable constants live here — change once, applies everywhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env file ─────────────────────────────────────────────────────────────
load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR  = DATA_DIR / "pdfs"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"

# ── Gemini LLM Config ──────────────────────────────────────────────────────────
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL      = "gemini-3.8-flash"
EMBEDDING_MODEL   = "models/gemini-embedding-001"
GEMINI_TEMPERATURE = 0.2   # Low temperature for factual, grounded answers

# ── RAG Config ─────────────────────────────────────────────────────────────────
CHUNK_SIZE        = 450    # approximate tokens per chunk
CHUNK_OVERLAP     = 60     # overlap tokens to preserve context across chunks
TOP_K_RETRIEVAL   = 5      # number of top chunks to retrieve per query

# ── ChromaDB Config ────────────────────────────────────────────────────────────
CHROMA_COLLECTION_NAME = "bharat_finlit_kb"

# ── Voice / Language Config ────────────────────────────────────────────────────
LANGUAGE_OPTIONS = {
    "हिंदी (Hindi)": "hi-IN",
    "English":        "en-IN",
}
DEFAULT_LANGUAGE_LABEL = "हिंदी (Hindi)"
DEFAULT_LANGUAGE_CODE  = "hi-IN"

# ── SEBI PDF Knowledge Base ────────────────────────────────────────────────────
# These PDFs must exist in data/pdfs/ — committed directly to the repo
SEBI_PDF_SOURCES = [
    {
        "filename": "sebi_investor_awareness_mutual_funds.pdf",
        "title":    "SEBI Investor Awareness — Mutual Funds",
        "source_tag": "SEBI Mutual Funds Guide",
    },
    {
        "filename": "sebi_investor_awareness_frauds.pdf",
        "title":    "SEBI Investor Awareness — Investment Frauds",
        "source_tag": "SEBI Fraud Awareness Guide",
    },
    {
        "filename": "sebi_saa_booklet.pdf",
        "title":    "SEBI Securities Awareness — Investor Rights",
        "source_tag": "SEBI Investor Rights Booklet",
    },
]

# ── YouTube Knowledge Base ─────────────────────────────────────────────────────
# Curated SEBI / NSE investor awareness videos with Hindi + English captions
YOUTUBE_SOURCES = [
    {
        "video_id":  "n_YOIINF01g",
        "title":     "SEBI — Investor Awareness: Beware of Frauds (Official)",
        "source_tag": "SEBI Official Video",
        "languages": ["hi", "en"],
    },
    {
        "video_id":  "0Jl-cJJBFdA",
        "title":     "NSE India — Understanding Mutual Funds for Beginners",
        "source_tag": "NSE Education Video",
        "languages": ["hi", "en"],
    },
]

# ── App Meta ───────────────────────────────────────────────────────────────────
APP_NAME    = "Bharat Financial Literacy & Fraud Resilience Companion"
APP_TAGLINE = "आपका विश्वसनीय वित्तीय साथी | Your Trusted Financial Companion"
APP_VERSION = "1.0.0-mvp"
