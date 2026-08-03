from __future__ import annotations

import json
import pickle

import pytest

from tidal_utils.backup import load_backup, save_backup
from tidal_utils.models import AlbumSnapshot, LibraryBackup, PlaylistSnapshot, TrackSnapshot


def sample_backup():
    track = TrackSnapshot("1", "Song", ("Artist",), "Album", True, False, "LOSSLESS", "ISRC")
    album = AlbumSnapshot("2", "Album", ("Artist",), True, 10, False, "LOSSLESS")
    playlist = PlaylistSnapshot("3", "List", "Description", (track, track))
    return LibraryBackup(created_at="2026-08-03T00:00:00+00:00", tracks=(track,), albums=(album,), playlists=(playlist,))


def test_json_round_trip(tmp_path):
    path = save_backup(sample_backup(), tmp_path / "backup.json")
    assert load_backup(path) == sample_backup()
    assert json.loads(path.read_text())["format_version"] == 1


def test_future_version_is_rejected(tmp_path):
    path = tmp_path / "future.json"
    path.write_text('{"format_version": 999}')
    with pytest.raises(ValueError, match="newer"):
        load_backup(path)


def test_pickle_requires_explicit_opt_in(tmp_path):
    path = tmp_path / "legacy.pkl"
    with path.open("wb") as handle:
        pickle.dump([], handle)
        pickle.dump([], handle)
        pickle.dump([], handle)
    with pytest.raises(ValueError, match="legacy pickle"):
        load_backup(path)
    with pytest.warns(RuntimeWarning):
        assert load_backup(path, allow_unsafe_pickle=True).tracks == ()
