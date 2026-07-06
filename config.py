"""
Configuration constants for the Knowledge Gap Tutor.

All secrets are loaded from environment variables (see .env.example).
All tunable parameters (mastery thresholds, model name, max retries) live here.
"""

from __future__ import annotations

import os

# ─── LLM Configuration ─────────────────────────────────────────────────────────
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.5-flash")

# ─── API Keys (fetched securely from environment) ──────────────────────────────
def get_google_api_key() -> str:
    """Fetch GOOGLE_API_KEY from environment or raise."""
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing required environment variable: GOOGLE_API_KEY. "
            "Set it in your .env file -- never hardcode it."
        )
    return key

def get_youtube_api_key() -> str:
    """Optional; ResourceFinder will gracefully skip YouTube if missing."""
    return os.environ.get("YOUTUBE_API_KEY", "")

def get_web_search_api_key() -> str:
    """Optional; ResourceFinder will gracefully skip web search if missing."""
    return os.environ.get("WEB_SEARCH_API_KEY", "")

# ─── Mastery Logic ─────────────────────────────────────────────────────────────
MASTERY_THRESHOLD = 0.75  # must answer ≥75% of questions correctly to pass a subtopic
MAX_RETRIES_PER_SUBTOPIC = 2  # after failing twice, mark as "needs-review" and move on

# ─── Quiz Generation ───────────────────────────────────────────────────────────
QUESTIONS_PER_SUBTOPIC = 3  # recall, applied, conceptual mix
MIN_QUESTIONS_FOR_MASTERY = 2  # need at least this many correct

# ─── Resource Discovery ────────────────────────────────────────────────────────
MAX_CANDIDATE_RESOURCES = 4  # ResourceFinder returns this many raw candidates
MAX_CURATED_RESOURCES = 2    # Curator picks top 2 for the learner

# ─── MCP Server Connection ─────────────────────────────────────────────────────
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "")  # e.g., "http://localhost:8080"

# ─── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
