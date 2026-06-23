from __future__ import annotations

from typing import Any, Literal, TypedDict


TrackStatus = Literal[
    "OK_APPLE_FOUND",
    "CHECK_MANUALLY",
    "NOT_FOUND_APPLE",
    "NOT_FOUND_MUSICBRAINZ",
    "DUPLICATE",
    "SKIP",
]


class DescriptionSource(TypedDict):
    playlist_title: str
    playlist_url: str
    playlist_id: str
    source_format: str


class DescriptionVideo(TypedDict):
    index: int
    video_id: str
    video_title: str
    video_url: str
    description: str


class DescriptionsDocument(TypedDict):
    source: DescriptionSource
    videos: list[DescriptionVideo]


class MusicBrainzResult(TypedDict):
    found: bool
    score: int | None
    recording_id: str
    artist: str
    title: str
    isrcs: list[str]
    error: str


class ITunesResult(TypedDict):
    found: bool
    track_id: int | None
    artist_name: str
    track_name: str
    track_view_url: str
    error: str


JsonDict = dict[str, Any]
