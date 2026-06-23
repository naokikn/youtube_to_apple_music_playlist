#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import CLEANED_TRACKS_JSON_PATH, LLM_TRACKS_JSON_PATH, SHORTCUTS_CSV_PATH, SHORTCUTS_TXT_PATH
from src.validate_tracks import validate_and_write_outputs


STATUSES = [
    "OK_APPLE_FOUND",
    "CHECK_MANUALLY",
    "NOT_FOUND_APPLE",
    "NOT_FOUND_MUSICBRAINZ",
    "DUPLICATE",
    "SKIP",
]


def main() -> int:
    try:
        counts = validate_and_write_outputs(
            LLM_TRACKS_JSON_PATH,
            CLEANED_TRACKS_JSON_PATH,
            SHORTCUTS_TXT_PATH,
            SHORTCUTS_CSV_PATH,
        )
    except Exception as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1

    print("ステータス別件数:")
    for status in STATUSES:
        print(f"  {status}: {counts.get(status, 0)}")
    print(f"出力: {CLEANED_TRACKS_JSON_PATH}")
    print(f"出力: {SHORTCUTS_TXT_PATH}")
    print(f"出力: {SHORTCUTS_CSV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
