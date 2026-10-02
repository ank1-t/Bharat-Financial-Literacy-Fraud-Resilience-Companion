# data/transcripts/
# ──────────────────────────────────────────────────────────────────────────────
# YouTube transcript JSON files are cached here after first fetch.
# Format: <video_id>_transcript.json
#
# Each file contains a list of segment objects:
# [{"text": "...", "start": 12.34, "duration": 3.21}, ...]
#
# These are fetched automatically by ingestion/youtube_loader.py on first run.
# Cached files are reused on subsequent runs to avoid repeated API calls.
