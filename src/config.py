from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
WORKFLOW_DIR = PROJECT_ROOT / "workflow"
EXAMPLES_DIR = PROJECT_ROOT / "examples"

WORKFLOW_INPUT_DIR = WORKFLOW_DIR / "00_input"
WORKFLOW_YTDLP_DIR = WORKFLOW_DIR / "01_ytdlp"
WORKFLOW_DESCRIPTIONS_DIR = WORKFLOW_DIR / "02_descriptions"
WORKFLOW_LLM_DIR = WORKFLOW_DIR / "03_llm"
WORKFLOW_VALIDATED_DIR = WORKFLOW_DIR / "04_validated"

PLAYLIST_URL_PATH = WORKFLOW_INPUT_DIR / "playlist_url.txt"
PLAYLIST_ITEMS_JSONL_PATH = WORKFLOW_YTDLP_DIR / "playlist_items.jsonl"
DESCRIPTIONS_JSON_PATH = WORKFLOW_DESCRIPTIONS_DIR / "descriptions.json"
LLM_TRACKS_JSON_PATH = WORKFLOW_LLM_DIR / "llm_tracks.json"
CLEANED_TRACKS_JSON_PATH = WORKFLOW_VALIDATED_DIR / "cleaned_tracks.json"
SHORTCUTS_TXT_PATH = WORKFLOW_VALIDATED_DIR / "shortcuts_tracks.txt"
SHORTCUTS_CSV_PATH = WORKFLOW_VALIDATED_DIR / "shortcuts_tracks.csv"

MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2/recording/"
ITUNES_SEARCH_API_URL = "https://itunes.apple.com/search"
MUSICBRAINZ_MIN_INTERVAL_SECONDS = 1.1
MUSICBRAINZ_OK_SCORE = 80

SHORTCUTS_INCLUDED_STATUSES = {"OK_APPLE_FOUND", "CHECK_MANUALLY"}


def get_musicbrainz_user_agent() -> str:
    user_agent = os.environ.get("MUSICBRAINZ_USER_AGENT", "").strip()
    if not user_agent:
        raise RuntimeError(
            "MUSICBRAINZ_USER_AGENT が未設定です。例: "
            'export MUSICBRAINZ_USER_AGENT="youtube-apple-music-playlist/0.1 (your-email@example.com)"'
        )
    return user_agent
