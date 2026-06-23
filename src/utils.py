from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"入力JSONファイルが見つかりません: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_csv_utf8_sig(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def is_invalid_track_text(value: Any) -> bool:
    text = clean_string(value)
    if not text:
        return True
    lowered = normalize_key(text)
    invalid_values = {"unknown", "null", "none", "n/a", "na", "-", "不明", "なし"}
    return lowered in invalid_values
