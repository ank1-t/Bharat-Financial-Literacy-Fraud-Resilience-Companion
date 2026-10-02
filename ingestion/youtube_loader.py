"""
ingestion/youtube_loader.py
────────────────────────────
Fetches transcripts from YouTube using youtube-transcript-api,
caches them locally in data/transcripts/, and chunks them into
overlapping windows preserving video timestamp metadata.

Each chunk is a dict:
  {
    "text":     str,
    "metadata": {
        "source":     str,    # e.g. "SEBI Official Video"
        "title":      str,    # Video title
        "video_id":   str,    # YouTube video ID
        "timestamp":  str,    # "MM:SS" of chunk start
        "start_sec":  float,  # raw seconds for sorting
        "type":       "youtube",
        "chunk_id":   str,
    }
  }
"""

import json
import logging
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

from config.settings import TRANSCRIPT_DIR, YOUTUBE_SOURCES, CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


def _seconds_to_timestamp(seconds: float) -> str:
    """Convert float seconds to 'MM:SS' string."""
    total = int(seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


def _fetch_transcript(video_id: str, languages: list[str]) -> list[dict] | None:
    """
    Fetch transcript from YouTube or load from local cache.

    Returns list of segment dicts: [{"text": str, "start": float, "duration": float}]
    """
    cache_path = TRANSCRIPT_DIR / f"{video_id}_transcript.json"

    # ── Cache hit ──────────────────────────────────────────────────────────────
    if cache_path.exists():
        logger.info(f"Loading cached transcript for video: {video_id}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ── Fetch from YouTube ─────────────────────────────────────────────────────
    try:
        logger.info(f"Fetching transcript from YouTube: {video_id}")
        if hasattr(YouTubeTranscriptApi, "get_transcript"):
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        else:
            ytt = YouTubeTranscriptApi()
            fetched = ytt.fetch(video_id, languages=languages)
            raw = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else list(fetched)
            transcript = []
            for item in raw:
                transcript.append({
                    "text": item.get("text", "") if isinstance(item, dict) else getattr(item, "text", ""),
                    "start": item.get("start", 0.0) if isinstance(item, dict) else getattr(item, "start", 0.0),
                    "duration": item.get("duration", 0.0) if isinstance(item, dict) else getattr(item, "duration", 0.0),
                })

        # Cache locally for future runs
        TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)

        logger.info(f"  → Cached transcript ({len(transcript)} segments)")
        return transcript

    except Exception as e:
        logger.warning(f"Could not fetch transcript from YouTube for {video_id}: {e}")
        return None


def _chunk_transcript(segments: list[dict], chunk_size: int, overlap: int) -> list[dict]:
    """
    Group transcript segments into overlapping text chunks.
    Each chunk preserves the start timestamp of its first segment.

    Returns list of {"text": str, "start_sec": float} dicts.
    """
    chunks = []
    words_buffer = []
    start_sec = segments[0]["start"] if segments else 0.0
    chunk_start_sec = start_sec

    for seg in segments:
        seg_words = seg["text"].split()
        words_buffer.extend(seg_words)

        if len(words_buffer) >= chunk_size:
            chunk_text = " ".join(words_buffer[:chunk_size])
            chunks.append({"text": chunk_text, "start_sec": chunk_start_sec})

            # Slide window with overlap
            words_buffer = words_buffer[chunk_size - overlap:]
            chunk_start_sec = seg["start"]

    # Handle remaining words
    if words_buffer:
        chunks.append({"text": " ".join(words_buffer), "start_sec": chunk_start_sec})

    return chunks


def load_youtube_source(source_config: dict) -> list[dict]:
    """
    Load, chunk, and format a single YouTube source into chunk dicts.

    Args:
        source_config: A dict from YOUTUBE_SOURCES (video_id, title, source_tag, languages).

    Returns:
        List of chunk dicts with text and metadata.
    """
    video_id = source_config["video_id"]
    segments = _fetch_transcript(video_id, source_config.get("languages", ["en", "hi"]))

    if not segments:
        return []

    raw_chunks = _chunk_transcript(segments, CHUNK_SIZE, CHUNK_OVERLAP)
    chunks = []
    for idx, raw in enumerate(raw_chunks):
        timestamp = _seconds_to_timestamp(raw["start_sec"])
        chunk_id = f"yt_{video_id}_c{idx}"
        chunks.append({
            "text": raw["text"],
            "metadata": {
                "source":     source_config["source_tag"],
                "title":      source_config["title"],
                "video_id":   video_id,
                "timestamp":  timestamp,
                "start_sec":  raw["start_sec"],
                "type":       "youtube",
                "chunk_id":   chunk_id,
                "watch_url":  f"https://youtu.be/{video_id}?t={int(raw['start_sec'])}",
            }
        })

    logger.info(f"YouTube '{source_config['title']}': {len(chunks)} chunks")
    return chunks


def load_all_youtube() -> list[dict]:
    """
    Load and chunk all YouTube sources defined in settings.YOUTUBE_SOURCES.

    Returns:
        Combined list of all chunks.
    """
    all_chunks = []
    for source_config in YOUTUBE_SOURCES:
        chunks = load_youtube_source(source_config)
        all_chunks.extend(chunks)

    logger.info(f"Total YouTube chunks loaded: {len(all_chunks)}")
    return all_chunks


def format_youtube_citation(metadata: dict) -> str:
    """
    Format a human-readable citation string from YouTube chunk metadata.

    Example: [Video: SEBI Official Video, Time 02:34]
    """
    return (
        f"[Video: {metadata.get('source', 'YouTube')}, "
        f"Time {metadata.get('timestamp', '00:00')}]"
        f" — youtu.be/{metadata.get('video_id', '')}?t={int(metadata.get('start_sec', 0))}"
    )
