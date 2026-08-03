from __future__ import annotations

from compare_backups import compare_albums, compare_tracks
from fix_unavailable import parentheticals

from conftest import Album, Artist, Track


def test_legacy_compare_functions_handle_empty_new_lists():
    artist = Artist("Artist")
    album = Album("a", "Album", artist)
    track = Track("t", "Song", artist, album)
    assert [item.title for item in compare_albums([album], [])] == ["Album"]
    assert [item.title for item in compare_tracks([track], [])] == ["Song"]


def test_legacy_parentheticals_is_flat():
    assert parentheticals("Song (Live) [Mix]") == ["Live", "Mix"]
