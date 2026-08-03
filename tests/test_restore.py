from __future__ import annotations

from tidal_utils.models import LibraryBackup, PlaylistSnapshot, TrackSnapshot
from tidal_utils.restore import build_restore_plan


class Favorites:
    def tracks(self, limit=9999):
        return []

    def albums(self, limit=9999):
        return []


class User:
    def __init__(self, playlists):
        self.favorites = Favorites()
        self._playlists = playlists

    def playlists(self):
        return self._playlists


class Session:
    def __init__(self, playlists):
        self.user = User(playlists)


class ApiTrack:
    def __init__(self, identifier, name):
        self.id = identifier
        self.name = name
        self.artist = type("Artist", (), {"name": "Artist"})()
        self.artists = [self.artist]
        self.album = type("Album", (), {"name": "Album"})()
        self.available = True
        self.explicit = False
        self.audio_quality = "LOSSLESS"
        self.isrc = None


class ApiPlaylist:
    id = "p"
    name = "List"
    description = ""

    def __init__(self, tracks):
        self._tracks = tracks

    def tracks(self):
        return self._tracks


def test_restore_plan_preserves_duplicate_counts():
    existing = ApiTrack("1", "Song")
    wanted = TrackSnapshot("1", "Song", ("Artist",), "Album")
    backup = LibraryBackup(playlists=(PlaylistSnapshot("p", "List", tracks=(wanted, wanted)),))
    plan = build_restore_plan(Session([ApiPlaylist([existing])]), backup, include_playlists=True)
    playlist_tracks = [action for action in plan if action.kind == "playlist_track"]
    assert len(playlist_tracks) == 1
