"""
tests/test_rag.py
──────────────────
Unit tests for the RAG pipeline components.
Uses mock objects to avoid requiring live Gemini API and ChromaDB.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestPdfLoader:
    """Tests for PDF ingestion module."""

    def test_chunk_text_basic(self):
        from ingestion.pdf_loader import _chunk_text
        text = " ".join([f"word{i}" for i in range(1000)])
        chunks = _chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) > 1
        # Each chunk should be <= 100 words (approximately)
        for chunk in chunks:
            word_count = len(chunk.split())
            assert word_count <= 110  # allow small buffer

    def test_chunk_text_overlap(self):
        from ingestion.pdf_loader import _chunk_text
        words = [f"w{i}" for i in range(20)]
        text = " ".join(words)
        chunks = _chunk_text(text, chunk_size=10, overlap=3)
        # Second chunk should start 7 words after first chunk starts
        first_words  = chunks[0].split()
        second_words = chunks[1].split()
        # Check overlap: last 3 words of first chunk appear in second chunk
        assert first_words[-3] in second_words

    def test_chunk_text_empty_string(self):
        from ingestion.pdf_loader import _chunk_text
        chunks = _chunk_text("", chunk_size=100, overlap=10)
        assert chunks == []

    def test_format_pdf_citation(self):
        from ingestion.pdf_loader import format_pdf_citation
        meta = {"source": "SEBI Mutual Funds Guide", "page": 7}
        citation = format_pdf_citation(meta)
        assert "SEBI Mutual Funds Guide" in citation
        assert "Pg 7" in citation
        assert citation.startswith("[Source:")

    def test_load_pdf_missing_file(self):
        from ingestion.pdf_loader import load_pdf
        result = load_pdf({"filename": "nonexistent_file.pdf", "title": "Test", "source_tag": "Test"})
        assert result == []


class TestYouTubeLoader:
    """Tests for YouTube transcript ingestion module."""

    def test_seconds_to_timestamp(self):
        from ingestion.youtube_loader import _seconds_to_timestamp
        assert _seconds_to_timestamp(0)    == "00:00"
        assert _seconds_to_timestamp(60)   == "01:00"
        assert _seconds_to_timestamp(90)   == "01:30"
        assert _seconds_to_timestamp(3600) == "60:00"
        assert _seconds_to_timestamp(125)  == "02:05"

    def test_chunk_transcript_basic(self):
        from ingestion.youtube_loader import _chunk_transcript
        segments = [
            {"text": f"word{i} " * 10, "start": float(i), "duration": 1.0}
            for i in range(100)
        ]
        chunks = _chunk_transcript(segments, chunk_size=50, overlap=5)
        assert len(chunks) > 1
        assert all("text" in c and "start_sec" in c for c in chunks)

    def test_format_youtube_citation(self):
        from ingestion.youtube_loader import format_youtube_citation
        meta = {"source": "SEBI Official Video", "timestamp": "02:34", "video_id": "abc123", "start_sec": 154.0}
        citation = format_youtube_citation(meta)
        assert "SEBI Official Video" in citation
        assert "02:34" in citation
        assert "abc123" in citation


class TestRetriever:
    """Tests for the retrieval module."""

    def test_format_context_block_empty(self):
        from rag.retriever import format_context_block
        result = format_context_block([])
        assert "No relevant context" in result

    def test_format_context_block_pdf(self):
        from rag.retriever import format_context_block
        results = [{
            "text": "Mutual funds pool money from investors.",
            "metadata": {"type": "pdf", "source": "SEBI Guide", "page": 5},
            "distance": 0.1
        }]
        context = format_context_block(results)
        assert "SEBI Guide" in context
        assert "Pg 5" in context
        assert "Mutual funds" in context

    def test_format_context_block_youtube(self):
        from rag.retriever import format_context_block
        results = [{
            "text": "Never invest in guaranteed return schemes.",
            "metadata": {"type": "youtube", "source": "SEBI Video", "timestamp": "01:23"},
            "distance": 0.15
        }]
        context = format_context_block(results)
        assert "SEBI Video" in context
        assert "01:23" in context


class TestGenerator:
    """Tests for the RAG generator module."""

    def test_extract_citations_pdf(self):
        from rag.generator import extract_citations
        answer = (
            "Mutual funds are regulated by SEBI. "
            "[Source: SEBI Mutual Funds Guide, Pg 5] "
            "They offer diversification. [Video: SEBI Official Video, Time 02:34]"
        )
        citations = extract_citations(answer)
        assert len(citations) == 2
        assert any("Source:" in c for c in citations)
        assert any("Video:" in c for c in citations)

    def test_extract_citations_empty(self):
        from rag.generator import extract_citations
        answer = "This answer has no citations."
        citations = extract_citations(answer)
        assert citations == []

    def test_no_api_key_returns_error_message(self):
        from rag.generator import generate_answer
        with patch("rag.generator.GEMINI_API_KEY", ""):
            result = generate_answer("test query", "test context")
            assert "GEMINI_API_KEY" in result or "not configured" in result.lower()
