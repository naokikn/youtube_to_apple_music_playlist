from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.models import DescriptionVideo, DescriptionsDocument
from src.utils import clean_string, read_text_file, write_json


@dataclass(frozen=True)
class ConvertStats:
    read_lines: int
    converted_videos: int
    skipped_lines: int


def load_jsonl_records(path: Path) -> tuple[list[dict[str, Any]], int, int]:
    if not path.exists():
        raise FileNotFoundError(f"yt-dlp JSONLファイルが見つかりません: {path}")

    records: list[dict[str, Any]] = []
    read_lines = 0
    skipped_lines = 0

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue
            read_lines += 1
            try:
                value = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                skipped_lines += 1
                print(
                    f"警告: {path} の {line_number} 行目をJSONとして読めないためスキップします: {exc}",
                    file=sys.stderr,
                )
                continue
            if not isinstance(value, dict):
                skipped_lines += 1
                print(
                    f"警告: {path} の {line_number} 行目がJSONオブジェクトではないためスキップします。",
                    file=sys.stderr,
                )
                continue
            records.append(value)

    return records, read_lines, skipped_lines


def fallback_video_url(record: dict[str, Any]) -> str:
    webpage_url = clean_string(record.get("webpage_url"))
    if webpage_url:
        return webpage_url
    original_url = clean_string(record.get("original_url"))
    if original_url:
        return original_url
    video_id = clean_string(record.get("id"))
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return ""


def to_int(value: Any, fallback: int) -> int:
    try:
        if value is None or value == "":
            return fallback
        return int(value)
    except (TypeError, ValueError):
        return fallback


def build_video_record(record: dict[str, Any], read_order: int) -> DescriptionVideo:
    return {
        "index": to_int(record.get("playlist_index"), read_order),
        "video_id": clean_string(record.get("id")),
        "video_title": clean_string(record.get("title")),
        "video_url": fallback_video_url(record),
        "description": "" if record.get("description") is None else str(record.get("description")),
    }


def build_descriptions_document(records: list[dict[str, Any]], playlist_url_fallback: str) -> DescriptionsDocument:
    first_record = records[0] if records else {}
    playlist_url = clean_string(first_record.get("playlist_webpage_url")) or playlist_url_fallback

    videos = [build_video_record(record, index) for index, record in enumerate(records, start=1)]
    videos.sort(key=lambda item: item["index"])

    return {
        "source": {
            "playlist_title": clean_string(first_record.get("playlist")),
            "playlist_url": playlist_url,
            "playlist_id": clean_string(first_record.get("playlist_id")),
            "source_format": "yt-dlp-jsonl",
        },
        "videos": videos,
    }


def convert_playlist_items_to_descriptions(
    playlist_items_path: Path,
    playlist_url_path: Path,
    output_path: Path,
) -> ConvertStats:
    playlist_url_fallback = read_text_file(playlist_url_path).strip()
    records, read_lines, skipped_lines = load_jsonl_records(playlist_items_path)
    document = build_descriptions_document(records, playlist_url_fallback)
    write_json(output_path, document)
    return ConvertStats(
        read_lines=read_lines,
        converted_videos=len(document["videos"]),
        skipped_lines=skipped_lines,
    )
