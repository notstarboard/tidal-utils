from __future__ import annotations

from tidal_utils.compare import compare_libraries
from tidal_utils.models import AlbumSnapshot, LibraryBackup, PlaylistSnapshot, TrackSnapshot


def track(identifier="1", title="Song", artist="Artist", available=True):
    return TrackSnapshot(identifier, title, (artist,), "Album", available)


def album(identifier="a", title="Album", artist="Artist"):
    return AlbumSnapshot(identifier, title, (artist,))


def test_empty_new_library_reports_everything_removed():
    old = LibraryBackup(tracks=(track(),), albums=(album(),))
    diff = compare_libraries(old, LibraryBackup())
    assert [item.title for item in diff.removed_tracks] == ["Song"]
    assert [item.title for item in diff.removed_albums] == ["Album"]


def test_duplicate_track_count_is_preserved():
    duplicate = track()
    old = LibraryBackup(tracks=(duplicate, duplicate))
    new = LibraryBackup(tracks=(duplicate,))
    diff = compare_libraries(old, new)
    assert len(diff.removed_tracks) == 1


def test_playlist_tracks_follow_playlist_identity_not_list_position():
    first = PlaylistSnapshot("one", "Zulu", tracks=(track("1", "First"),))
    second = PlaylistSnapshot("two", "Alpha", tracks=(track("2", "Second"),))
    reordered = LibraryBackup(playlists=(second, first))
    diff = compare_libraries(LibraryBackup(playlists=(first, second)), reordered)
    assert diff.playlist_changes == ()


def test_playlist_order_change_is_detected_without_false_additions():
    one = track("1", "One")
    two = track("2", "Two")
    old = LibraryBackup(playlists=(PlaylistSnapshot("p", "List", tracks=(one, two)),))
    new = LibraryBackup(playlists=(PlaylistSnapshot("p", "List", tracks=(two, one)),))
    diff = compare_libraries(old, new)
    assert diff.playlist_changes[0].order_changed is True
    assert diff.playlist_changes[0].removed_tracks == ()
    assert diff.playlist_changes[0].added_tracks == ()


def test_added_and_deleted_playlists_are_reported():
    old = LibraryBackup(playlists=(PlaylistSnapshot("old", "Old"),))
    new = LibraryBackup(playlists=(PlaylistSnapshot("new", "New"),))
    diff = compare_libraries(old, new)
    assert [item.title for item in diff.removed_playlists] == ["Old"]
    assert [item.title for item in diff.added_playlists] == ["New"]


def test_unavailable_playlist_track_is_reported():
    unavailable = track("x", "Unavailable", "Unknown Artist", False)
    old = LibraryBackup(playlists=(PlaylistSnapshot("p", "List"),))
    new = LibraryBackup(playlists=(PlaylistSnapshot("p", "List", tracks=(unavailable,)),))
    diff = compare_libraries(old, new)
    assert diff.playlist_changes[0].unavailable_tracks == (unavailable,)
