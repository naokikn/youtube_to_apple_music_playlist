#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DESCRIPTIONS_JSON_PATH, PLAYLIST_ITEMS_JSONL_PATH, PLAYLIST_URL_PATH
from src.convert_yt_dlp_jsonl import convert_playlist_items_to_descriptions


def main() -> int:
    try:
        stats = convert_playlist_items_to_descriptions(
            PLAYLIST_ITEMS_JSONL_PATH,
            PLAYLIST_URL_PATH,
            DESCRIPTIONS_JSON_PATH,
        )
    except Exception as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1

    print(f"読み込んだJSONL行数: {stats.read_lines}")
    print(f"変換した動画数: {stats.converted_videos}")
    print(f"スキップした行数: {stats.skipped_lines}")
    print(f"出力: {DESCRIPTIONS_JSON_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
