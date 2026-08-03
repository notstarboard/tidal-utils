from __future__ import annotations

import csv
import os
import pickle
import sys
import types

import pytest

from tidal_utils.backup import load_backup, migrate_backup, save_backup
from tidal_utils.client import retry
from tidal_utils.compare import LibraryDiff
from tidal_utils.models import LibraryBackup, TrackSnapshot
from tidal_utils.report import write_report
from tidal_utils.security import MAX_BACKUP_BYTES, redact_sensitive, safe_display, secure_session_path


class MaliciousPickle:
    def __reduce__(self):
        return os.system, ("touch should-not-exist",)


def test_restricted_pickle_loader_blocks_arbitrary_code(tmp_path, monkeypatch):
    path = tmp_path / "malicious.pkl"
    with path.open("wb") as handle:
        pickle.dump(MaliciousPickle(), handle)
    monkeypatch.chdir(tmp_path)

    with pytest.warns(RuntimeWarning), pytest.raises(pickle.UnpicklingError, match="Blocked"):
        load_backup(path, allow_unsafe_pickle=True)

    assert not (tmp_path / "should-not-exist").exists()


def test_restricted_pickle_extracts_inert_tidal_state(tmp_path):
    module_name = "tidalapi"
    fake_module = types.ModuleType(module_name)
    class_name = "SecurityTestLegacyObject"
    legacy_type = type(class_name, (), {})
    legacy_type.__module__ = module_name
    setattr(fake_module, class_name, legacy_type)
    previous_module = sys.modules.get(module_name)
    sys.modules[module_name] = fake_module
    try:
        artist = legacy_type()
        artist.name = "Artist"
        album = legacy_type()
        album.id = "2"
        album.name = "Album"
        album.artist = artist
        track = legacy_type()
        track.id = "1"
        track.name = "Song"
        track.artist = artist
        track.album = album
        playlist = legacy_type()
        playlist.id = "3"
        playlist.name = "Playlist"
        path = tmp_path / "legacy.pkl"
        with path.open("wb") as handle:
            pickle.dump([track], handle)
            pickle.dump([album], handle)
            pickle.dump([playlist], handle)
            pickle.dump([[track]], handle)
    finally:
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module

    with pytest.warns(RuntimeWarning):
        backup = load_backup(path, allow_unsafe_pickle=True)

    assert backup.tracks[0].title == "Song"
    assert backup.albums[0].title == "Album"
    assert backup.playlists[0].tracks[0].title == "Song"


def test_migration_requires_explicit_trust(tmp_path):
    with pytest.raises(ValueError, match="trust-legacy-pickle"):
        migrate_backup(tmp_path / "old.pkl", tmp_path / "new.json")


def test_oversized_backup_is_rejected_before_parsing(tmp_path):
    path = tmp_path / "oversized.json"
    with path.open("wb") as handle:
        handle.truncate(MAX_BACKUP_BYTES + 1)
    with pytest.raises(ValueError, match="too large"):
        load_backup(path)


def test_backup_is_owner_only_on_posix(tmp_path):
    path = save_backup(LibraryBackup(), tmp_path / "backup.json")
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600


def test_backup_symlink_is_rejected(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("symbolic links are unavailable")
    target = tmp_path / "target.json"
    target.write_text('{"format_version": 1}')
    link = tmp_path / "backup.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are unavailable")
    with pytest.raises(ValueError, match="symbolic link"):
        load_backup(link)


def test_session_symlink_is_rejected(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("symbolic links are unavailable")
    target = tmp_path / "session-target.json"
    target.write_text("{}")
    link = tmp_path / "session.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are unavailable")
    with pytest.raises(ValueError, match="symbolic link"):
        secure_session_path(link)


def test_csv_fields_are_neutralized(tmp_path):
    track = TrackSnapshot("1", "=WEBSERVICE(\"https://example.invalid\")", ("@Artist",))
    path = write_report(LibraryDiff(added_tracks=(track,)), tmp_path / "report.csv")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["title"].startswith("'=")
    assert rows[0]["artists"].startswith("'@")


def test_terminal_controls_and_secrets_are_sanitized():
    assert safe_display("name\x1b[31m red\x00") == "name red"
    text = redact_sensitive("Authorization: Bearer-abc https://x.invalid/?access_token=secret")
    assert "Bearer-abc" not in text
    assert "secret" not in text
    assert text.count("[REDACTED]") == 2


def test_retry_rejects_invalid_attempt_count():
    with pytest.raises(ValueError, match="at least 1"):
        retry(lambda: None, attempts=0)
