from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests

from src.config import (
    ITUNES_SEARCH_API_URL,
    MUSICBRAINZ_API_URL,
    MUSICBRAINZ_MIN_INTERVAL_SECONDS,
    MUSICBRAINZ_OK_SCORE,
    SHORTCUTS_INCLUDED_STATUSES,
    get_musicbrainz_user_agent,
)
from src.models import ITunesResult, JsonDict, MusicBrainzResult, TrackStatus
from src.utils import clean_string, is_invalid_track_text, normalize_key, read_json, write_csv_utf8_sig, write_json


def empty_musicbrainz_result(error: str = "") -> MusicBrainzResult:
    return {
        "found": False,
        "score": None,
        "recording_id": "",
        "artist": "",
        "title": "",
        "isrcs": [],
        "error": error,
    }


def empty_itunes_result(error: str = "") -> ITunesResult:
    return {
        "found": False,
        "track_id": None,
        "artist_name": "",
        "track_name": "",
        "track_view_url": "",
        "error": error,
    }


def compact_result_for_output(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "error" or value}


def build_musicbrainz_query(artist: str, title: str) -> str:
    escaped_title = title.replace('"', '\\"')
    escaped_artist = artist.replace('"', '\\"')
    return f'recording:"{escaped_title}" AND artist:"{escaped_artist}"'


def extract_artist_credit(recording: dict[str, Any]) -> str:
    artist_credit = recording.get("artist-credit")
    if not isinstance(artist_credit, list):
        return ""
    parts: list[str] = []
    for item in artist_credit:
        if isinstance(item, dict):
            artist = item.get("artist")
            if isinstance(artist, dict):
                name = clean_string(artist.get("name"))
                if name:
                    parts.append(name)
            joinphrase = clean_string(item.get("joinphrase"))
            if joinphrase:
                parts.append(joinphrase)
        elif isinstance(item, str):
            parts.append(item)
    return "".join(parts).strip()


def musicbrainz_search_recording(
    session: requests.Session,
    artist: str,
    title: str,
    user_agent: str,
) -> MusicBrainzResult:
    params = {
        "query": build_musicbrainz_query(artist, title),
        "fmt": "json",
        "limit": 5,
    }
    headers = {"User-Agent": user_agent}
    try:
        response = session.get(MUSICBRAINZ_API_URL, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return empty_musicbrainz_result(f"MusicBrainz通信エラー: {exc}")
    except ValueError as exc:
        return empty_musicbrainz_result(f"MusicBrainzレスポンスをJSONとして読めません: {exc}")

    recordings = data.get("recordings", [])
    if not recordings:
        return empty_musicbrainz_result()

    first = recordings[0]
    score_value = first.get("score")
    try:
        score = int(score_value) if score_value is not None else None
    except (TypeError, ValueError):
        score = None

    isrcs_raw = first.get("isrcs", [])
    isrcs = [str(value) for value in isrcs_raw] if isinstance(isrcs_raw, list) else []

    return {
        "found": True,
        "score": score,
        "recording_id": clean_string(first.get("id")),
        "artist": extract_artist_credit(first),
        "title": clean_string(first.get("title")),
        "isrcs": isrcs,
        "error": "",
    }


def itunes_search_song(session: requests.Session, artist: str, title: str) -> ITunesResult:
    params = {
        "term": f"{artist} {title}",
        "country": "JP",
        "media": "music",
        "entity": "song",
        "limit": 5,
    }
    try:
        response = session.get(ITUNES_SEARCH_API_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return empty_itunes_result(f"iTunes Search API通信エラー: {exc}")
    except ValueError as exc:
        return empty_itunes_result(f"iTunes Search APIレスポンスをJSONとして読めません: {exc}")

    results = data.get("results", [])
    if not results:
        return empty_itunes_result()

    first = results[0]
    track_id = first.get("trackId")
    try:
        parsed_track_id = int(track_id) if track_id is not None else None
    except (TypeError, ValueError):
        parsed_track_id = None

    return {
        "found": True,
        "track_id": parsed_track_id,
        "artist_name": clean_string(first.get("artistName")),
        "track_name": clean_string(first.get("trackName")),
        "track_view_url": clean_string(first.get("trackViewUrl")),
        "error": "",
    }


def normalize_track(track: dict[str, Any]) -> tuple[str, str]:
    return clean_string(track.get("artist")), clean_string(track.get("title"))


def duplicate_key(artist: str, title: str) -> str:
    return f"{normalize_key(artist)}\u0000{normalize_key(title)}"


def determine_status(
    artist: str,
    title: str,
    is_duplicate: bool,
    musicbrainz: MusicBrainzResult,
    itunes: ITunesResult,
) -> TrackStatus:
    if is_invalid_track_text(artist) or is_invalid_track_text(title):
        return "SKIP"
    if is_duplicate:
        return "DUPLICATE"

    mb_found = bool(musicbrainz["found"])
    mb_score = musicbrainz.get("score")
    mb_ok = mb_found and mb_score is not None and mb_score >= MUSICBRAINZ_OK_SCORE
    itunes_found = bool(itunes["found"])

    if itunes_found and mb_ok:
        return "OK_APPLE_FOUND"
    if itunes_found:
        return "CHECK_MANUALLY"
    if mb_found:
        return "NOT_FOUND_APPLE"
    return "NOT_FOUND_MUSICBRAINZ"


def flatten_llm_tracks(llm_data: dict[str, Any]) -> list[dict[str, Any]]:
    videos = llm_data.get("videos", [])
    if not isinstance(videos, list):
        raise ValueError("output/llm_tracks.json の videos は配列である必要があります。")

    flattened: list[dict[str, Any]] = []
    for video in videos:
        if not isinstance(video, dict):
            continue
        tracks = video.get("tracks", [])
        if not isinstance(tracks, list):
            continue
        for track in tracks:
            if not isinstance(track, dict):
                continue
            flattened.append(
                {
                    "source_video_title": clean_string(video.get("video_title")),
                    "source_video_url": clean_string(video.get("video_url")),
                    "track": track,
                }
            )
    return flattened


def build_cleaned_track(
    source_video_title: str,
    source_video_url: str,
    track: dict[str, Any],
    raw_artist: str,
    raw_title: str,
    musicbrainz: MusicBrainzResult,
    itunes: ITunesResult,
    status: TrackStatus,
) -> JsonDict:
    clean_artist = raw_artist
    clean_title = raw_title
    shortcut_query = f"{clean_artist} - {clean_title}" if clean_artist and clean_title else ""
    return {
        "source_video_title": source_video_title,
        "source_video_url": source_video_url,
        "raw_artist": raw_artist,
        "raw_title": raw_title,
        "clean_artist": clean_artist,
        "clean_title": clean_title,
        "raw_text": clean_string(track.get("raw_text")),
        "timestamp": track.get("timestamp"),
        "llm_confidence": track.get("confidence"),
        "musicbrainz": compact_result_for_output(musicbrainz),
        "itunes": compact_result_for_output(itunes),
        "status": status,
        "shortcut_query": shortcut_query,
    }


def validate_tracks(llm_tracks_path: Path) -> tuple[JsonDict, Counter[str]]:
    user_agent = get_musicbrainz_user_agent()
    llm_data = read_json(llm_tracks_path)
    if not isinstance(llm_data, dict):
        raise ValueError("output/llm_tracks.json はJSONオブジェクトである必要があります。")

    flattened_tracks = flatten_llm_tracks(llm_data)
    seen_keys: set[str] = set()
    cleaned_tracks: list[JsonDict] = []
    counts: Counter[str] = Counter()
    session = requests.Session()
    last_musicbrainz_request_at = 0.0

    for item in flattened_tracks:
        track = item["track"]
        raw_artist, raw_title = normalize_track(track)
        is_invalid = is_invalid_track_text(raw_artist) or is_invalid_track_text(raw_title)
        key = duplicate_key(raw_artist, raw_title)
        is_duplicate = bool(key.strip("\u0000")) and key in seen_keys
        if not is_invalid:
            seen_keys.add(key)

        musicbrainz = empty_musicbrainz_result()
        itunes = empty_itunes_result()

        if not is_invalid:
            elapsed = time.monotonic() - last_musicbrainz_request_at
            if elapsed < MUSICBRAINZ_MIN_INTERVAL_SECONDS:
                time.sleep(MUSICBRAINZ_MIN_INTERVAL_SECONDS - elapsed)
            musicbrainz = musicbrainz_search_recording(session, raw_artist, raw_title, user_agent)
            last_musicbrainz_request_at = time.monotonic()
            itunes = itunes_search_song(session, raw_artist, raw_title)

        status = determine_status(raw_artist, raw_title, is_duplicate, musicbrainz, itunes)
        counts[status] += 1
        cleaned_tracks.append(
            build_cleaned_track(
                clean_string(item.get("source_video_title")),
                clean_string(item.get("source_video_url")),
                track,
                raw_artist,
                raw_title,
                musicbrainz,
                itunes,
                status,
            )
        )

    output = {
        "playlist_title": clean_string(llm_data.get("playlist_title")),
        "playlist_url": clean_string(llm_data.get("playlist_url")),
        "tracks": cleaned_tracks,
    }
    return output, counts


def write_cleaned_tracks_json(path: Path, data: JsonDict) -> None:
    write_json(path, data)


def write_shortcuts_txt(
    path: Path,
    cleaned_tracks: list[JsonDict],
    included_statuses: set[str] | None = None,
) -> None:
    included = included_statuses if included_statuses is not None else SHORTCUTS_INCLUDED_STATUSES
    lines = [
        clean_string(track.get("shortcut_query"))
        for track in cleaned_tracks
        if clean_string(track.get("status")) in included and clean_string(track.get("shortcut_query"))
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_shortcuts_csv(path: Path, cleaned_tracks: list[JsonDict]) -> None:
    fieldnames = [
        "status",
        "clean_artist",
        "clean_title",
        "shortcut_query",
        "source_video_title",
        "source_video_url",
        "itunes_artist",
        "itunes_title",
        "itunes_url",
        "musicbrainz_score",
    ]
    rows: list[dict[str, Any]] = []
    for track in cleaned_tracks:
        itunes = track.get("itunes") if isinstance(track.get("itunes"), dict) else {}
        musicbrainz = track.get("musicbrainz") if isinstance(track.get("musicbrainz"), dict) else {}
        rows.append(
            {
                "status": track.get("status", ""),
                "clean_artist": track.get("clean_artist", ""),
                "clean_title": track.get("clean_title", ""),
                "shortcut_query": track.get("shortcut_query", ""),
                "source_video_title": track.get("source_video_title", ""),
                "source_video_url": track.get("source_video_url", ""),
                "itunes_artist": itunes.get("artist_name", ""),
                "itunes_title": itunes.get("track_name", ""),
                "itunes_url": itunes.get("track_view_url", ""),
                "musicbrainz_score": musicbrainz.get("score", ""),
            }
        )
    write_csv_utf8_sig(path, rows, fieldnames)


def validate_and_write_outputs(
    llm_tracks_path: Path,
    cleaned_tracks_path: Path,
    shortcuts_txt_path: Path,
    shortcuts_csv_path: Path,
) -> Counter[str]:
    cleaned_data, counts = validate_tracks(llm_tracks_path)
    tracks = cleaned_data["tracks"]
    write_cleaned_tracks_json(cleaned_tracks_path, cleaned_data)
    write_shortcuts_txt(shortcuts_txt_path, tracks)
    write_shortcuts_csv(shortcuts_csv_path, tracks)
    return counts
