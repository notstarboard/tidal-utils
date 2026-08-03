from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Artist:
    name: str


@dataclass
class Album:
    id: str
    name: str
    artist: Artist
    artists: list[Artist] = field(default_factory=list)
    available: bool = True
    num_tracks: int = 10
    explicit: bool = False
    audio_quality: str = "LOSSLESS"

    def __post_init__(self):
        if not self.artists:
            self.artists = [self.artist]


@dataclass
class Track:
    id: str
    name: str
    artist: Artist
    album: Album
    artists: list[Artist] = field(default_factory=list)
    available: bool = True
    explicit: bool = False
    audio_quality: str = "LOSSLESS"
    isrc: str | None = None

    def __post_init__(self):
        if not self.artists:
            self.artists = [self.artist]


@dataclass
class Playlist:
    id: str
    name: str
    items: list[Track]
    description: str = ""

    def tracks(self):
        return list(self.items)
