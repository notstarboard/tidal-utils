from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
import re
import unicodedata

FORMAT_VERSION = 1


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold().strip()
    return re.sub(r"\s+", " ", text)


def _artist_names(obj: Any) -> tuple[str, ...]:
    artists = getattr(obj, "artists", None)
    if artists:
        names = tuple(str(getattr(artist, "name", artist)) for artist in artists)
        if names:
            return names
    artist = getattr(obj, "artist", None)
    if artist is not None:
        return (str(getattr(artist, "name", artist)),)
    return ()


def _identifier(obj: Any) -> str:
    value = getattr(obj, "id", "")
    return "" if value is None else str(value)


def _optional_bool(obj: Any, name: str) -> bool | None:
    value = getattr(obj, name, None)
    return value if isinstance(value, bool) else None


@dataclass(frozen=True, slots=True)
class TrackSnapshot:
    id: str
    title: str
    artists: tuple[str, ...] = ()
    album: str = ""
    available: bool | None = None
    explicit: bool | None = None
    audio_quality: str | None = None
    isrc: str | None = None

    @classmethod
    def from_api(cls, track: Any) -> "TrackSnapshot":
        album = getattr(track, "album", None)
        return cls(
            id=_identifier(track),
            title=str(getattr(track, "name", getattr(track, "title", ""))),
            artists=_artist_names(track),
            album=str(getattr(album, "name", "")) if album is not None else "",
            available=_optional_bool(track, "available"),
            explicit=_optional_bool(track, "explicit"),
            audio_quality=(str(getattr(track, "audio_quality", "")) or None),
            isrc=(str(getattr(track, "isrc", "")) or None),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrackSnapshot":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", data.get("name", ""))),
            artists=tuple(str(value) for value in data.get("artists", ())),
            album=str(data.get("album", "")),
            available=data.get("available"),
            explicit=data.get("explicit"),
            audio_quality=data.get("audio_quality"),
            isrc=data.get("isrc"),
        )

    def match_key(self) -> tuple[str, tuple[str, ...]]:
        return normalize_text(self.title), tuple(sorted(normalize_text(a) for a in self.artists))

    def display_artist(self) -> str:
        return ", ".join(self.artists) or "Unknown Artist"


@dataclass(frozen=True, slots=True)
class AlbumSnapshot:
    id: str
    title: str
    artists: tuple[str, ...] = ()
    available: bool | None = None
    num_tracks: int | None = None
    explicit: bool | None = None
    audio_quality: str | None = None

    @classmethod
    def from_api(cls, album: Any) -> "AlbumSnapshot":
        num_tracks = getattr(album, "num_tracks", None)
        return cls(
            id=_identifier(album),
            title=str(getattr(album, "name", getattr(album, "title", ""))),
            artists=_artist_names(album),
            available=_optional_bool(album, "available"),
            num_tracks=num_tracks if isinstance(num_tracks, int) else None,
            explicit=_optional_bool(album, "explicit"),
            audio_quality=(str(getattr(album, "audio_quality", "")) or None),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AlbumSnapshot":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", data.get("name", ""))),
            artists=tuple(str(value) for value in data.get("artists", ())),
            available=data.get("available"),
            num_tracks=data.get("num_tracks"),
            explicit=data.get("explicit"),
            audio_quality=data.get("audio_quality"),
        )

    def match_key(self) -> tuple[str, tuple[str, ...]]:
        return normalize_text(self.title), tuple(sorted(normalize_text(a) for a in self.artists))

    def display_artist(self) -> str:
        return ", ".join(self.artists) or "Unknown Artist"


@dataclass(frozen=True, slots=True)
class PlaylistSnapshot:
    id: str
    title: str
    description: str = ""
    tracks: tuple[TrackSnapshot, ...] = ()

    @classmethod
    def from_api(cls, playlist: Any, tracks: Iterable[Any] | None = None) -> "PlaylistSnapshot":
        api_tracks = tracks if tracks is not None else playlist.tracks()
        return cls(
            id=_identifier(playlist),
            title=str(getattr(playlist, "name", getattr(playlist, "title", ""))),
            description=str(getattr(playlist, "description", "") or ""),
            tracks=tuple(TrackSnapshot.from_api(track) for track in api_tracks),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlaylistSnapshot":
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", data.get("name", ""))),
            description=str(data.get("description", "")),
            tracks=tuple(TrackSnapshot.from_dict(track) for track in data.get("tracks", ())),
        )

    def match_key(self) -> str:
        return normalize_text(self.title)


@dataclass(frozen=True, slots=True)
class LibraryBackup:
    format_version: int = FORMAT_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tracks: tuple[TrackSnapshot, ...] = ()
    albums: tuple[AlbumSnapshot, ...] = ()
    playlists: tuple[PlaylistSnapshot, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LibraryBackup":
        version = int(data.get("format_version", 0))
        if version > FORMAT_VERSION:
            raise ValueError(
                f"Backup format {version} is newer than supported format {FORMAT_VERSION}."
            )
        return cls(
            format_version=version or FORMAT_VERSION,
            created_at=str(data.get("created_at", "")),
            tracks=tuple(TrackSnapshot.from_dict(track) for track in data.get("tracks", ())),
            albums=tuple(AlbumSnapshot.from_dict(album) for album in data.get("albums", ())),
            playlists=tuple(PlaylistSnapshot.from_dict(playlist) for playlist in data.get("playlists", ())),
        )
