from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
import re
import unicodedata

FORMAT_VERSION = 1
MAX_COLLECTION_ITEMS = 100_000
MAX_PLAYLISTS = 10_000
MAX_PLAYLIST_TRACKS = 100_000
MAX_TEXT_LENGTH = 10_000


def _text(value: Any, field_name: str) -> str:
    text = str(value if value is not None else "")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"{field_name} exceeds the {MAX_TEXT_LENGTH}-character limit.")
    return text


def _sequence(data: dict[str, Any], field_name: str, limit: int) -> list[Any] | tuple[Any, ...]:
    value = data.get(field_name, ())
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a JSON array.")
    if len(value) > limit:
        raise ValueError(f"{field_name} exceeds the {limit}-item limit.")
    return value


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
            id=_text(data.get("id", ""), "track id"),
            title=_text(data.get("title", data.get("name", "")), "track title"),
            artists=tuple(_text(value, "artist") for value in _sequence(data, "artists", 100)),
            album=_text(data.get("album", ""), "album title"),
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
            id=_text(data.get("id", ""), "album id"),
            title=_text(data.get("title", data.get("name", "")), "album title"),
            artists=tuple(_text(value, "artist") for value in _sequence(data, "artists", 100)),
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
            id=_text(data.get("id", ""), "playlist id"),
            title=_text(data.get("title", data.get("name", "")), "playlist title"),
            description=_text(data.get("description", ""), "playlist description"),
            tracks=tuple(TrackSnapshot.from_dict(track) for track in _sequence(data, "tracks", MAX_PLAYLIST_TRACKS)),
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
        if not isinstance(data, dict):
            raise ValueError("Backup data must be a JSON object.")
        version = int(data.get("format_version", 0))
        if version > FORMAT_VERSION:
            raise ValueError(
                f"Backup format {version} is newer than supported format {FORMAT_VERSION}."
            )
        tracks = _sequence(data, "tracks", MAX_COLLECTION_ITEMS)
        albums = _sequence(data, "albums", MAX_COLLECTION_ITEMS)
        playlists = _sequence(data, "playlists", MAX_PLAYLISTS)
        if not all(isinstance(item, dict) for item in (*tracks, *albums, *playlists)):
            raise ValueError("Backup collections must contain JSON objects.")
        return cls(
            format_version=version or FORMAT_VERSION,
            created_at=_text(data.get("created_at", ""), "created_at"),
            tracks=tuple(TrackSnapshot.from_dict(track) for track in tracks),
            albums=tuple(AlbumSnapshot.from_dict(album) for album in albums),
            playlists=tuple(PlaylistSnapshot.from_dict(playlist) for playlist in playlists),
        )
