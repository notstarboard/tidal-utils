from __future__ import annotations

from collections import OrderedDict, defaultdict, deque
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID
import builtins
import json
import pickle  # noqa: S403  # nosec B403 - restricted compatibility loader for trusted legacy backups
import warnings

from .models import AlbumSnapshot, LibraryBackup, PlaylistSnapshot, TrackSnapshot
from .security import MAX_BACKUP_BYTES, secure_read_bytes, secure_write_text

_SAFE_BUILTINS = {
    "bool",
    "bytearray",
    "bytes",
    "complex",
    "dict",
    "float",
    "frozenset",
    "int",
    "list",
    "set",
    "str",
    "tuple",
}
_SAFE_GLOBALS = {
    ("collections", "OrderedDict"): OrderedDict,
    ("collections", "defaultdict"): defaultdict,
    ("collections", "deque"): deque,
    ("datetime", "date"): date,
    ("datetime", "datetime"): datetime,
    ("datetime", "time"): time,
    ("datetime", "timedelta"): timedelta,
    ("datetime", "timezone"): timezone,
    ("decimal", "Decimal"): Decimal,
    ("uuid", "UUID"): UUID,
}


class _LegacyTidalObject:
    """Inert attribute container used instead of constructing tidalapi classes."""

    def __new__(cls, *args: Any, **kwargs: Any) -> "_LegacyTidalObject":
        del args, kwargs
        return super().__new__(cls)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs

    def __setstate__(self, state: Any) -> None:
        if isinstance(state, dict):
            self.__dict__.update(state)
            return
        if isinstance(state, tuple) and len(state) == 2:
            instance_state, slot_state = state
            if isinstance(instance_state, dict):
                self.__dict__.update(instance_state)
            if isinstance(slot_state, dict):
                self.__dict__.update(slot_state)
            return
        raise pickle.UnpicklingError("Blocked unsupported legacy object state.")


class RestrictedLegacyUnpickler(pickle.Unpickler):
    """Extract legacy TIDAL object state without importing or running its classes."""

    def find_class(self, module: str, name: str) -> Any:
        if module == "builtins" and name in _SAFE_BUILTINS:
            return getattr(builtins, name)
        safe = _SAFE_GLOBALS.get((module, name))
        if safe is not None:
            return safe
        if module == "tidalapi" or module.startswith("tidalapi."):
            return _LegacyTidalObject
        raise pickle.UnpicklingError(f"Blocked unsafe pickle global: {module}.{name}")


def snapshot_from_session(session: Any) -> LibraryBackup:
    tracks = tuple(TrackSnapshot.from_api(track) for track in session.user.favorites.tracks(limit=9999))
    albums = tuple(AlbumSnapshot.from_api(album) for album in session.user.favorites.albums(limit=9999))
    playlists = tuple(
        PlaylistSnapshot.from_api(playlist, playlist.tracks())
        for playlist in session.user.playlists()
    )
    return LibraryBackup(tracks=tracks, albums=albums, playlists=playlists)


def save_backup(backup: LibraryBackup, filename: str | Path) -> Path:
    content = json.dumps(backup.to_dict(), indent=2, ensure_ascii=False) + "\n"
    return secure_write_text(filename, content)


def create_backup(
    session: Any,
    output_dir: str | Path = ".",
    filename: str | None = None,
    retain: int | None = None,
) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    name = filename or f"library_backup_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    path = save_backup(snapshot_from_session(session), output / name)
    if retain is not None and retain >= 0:
        backups = sorted(
            output.glob("library_backup_*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for stale in backups[retain:]:
            if stale != path:
                stale.unlink(missing_ok=True)
    return path


def load_backup(filename: str | Path, *, allow_unsafe_pickle: bool = False) -> LibraryBackup:
    path, data = secure_read_bytes(
        filename,
        label="backup file",
        max_bytes=MAX_BACKUP_BYTES,
    )
    prefix = data[:64].lstrip()
    if prefix.startswith((b"{", b"[")):
        try:
            payload = json.loads(data.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError(f"Backup JSON is not valid UTF-8: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Backup JSON must contain an object at the top level.")
        return LibraryBackup.from_dict(payload)
    if not allow_unsafe_pickle:
        raise ValueError(
            "This appears to be a legacy pickle backup. Pickle data is not safe by default. "
            "Only load a file you trust, and pass --allow-unsafe-pickle to use the restricted legacy loader."
        )
    warnings.warn(
        "Loading a legacy pickle backup with a restricted compatibility loader. "
        "Only trusted pickle files should be opened.",
        RuntimeWarning,
        stacklevel=2,
    )
    return _load_legacy_pickle(data)


def _restricted_load(handle) -> Any:
    return RestrictedLegacyUnpickler(handle).load()  # noqa: S301  # nosec B301


def _load_legacy_pickle(data: bytes) -> LibraryBackup:
    with BytesIO(data) as handle:
        tracks = _restricted_load(handle)
        albums = _restricted_load(handle)
        playlists = _restricted_load(handle)
        try:
            playlist_tracks = _restricted_load(handle)
        except EOFError:
            playlist_tracks = [[] for _ in playlists]
    snapshots = []
    for index, playlist in enumerate(playlists):
        tracks_for_playlist = playlist_tracks[index] if index < len(playlist_tracks) else []
        snapshots.append(PlaylistSnapshot.from_api(playlist, tracks_for_playlist))
    return LibraryBackup(
        tracks=tuple(TrackSnapshot.from_api(track) for track in tracks),
        albums=tuple(AlbumSnapshot.from_api(album) for album in albums),
        playlists=tuple(snapshots),
    )


def migrate_backup(
    source: str | Path,
    destination: str | Path,
    *,
    trust_legacy_pickle: bool = False,
) -> Path:
    if not trust_legacy_pickle:
        raise ValueError(
            "Legacy pickle migration requires --trust-legacy-pickle because pickle files may contain executable payloads."
        )
    return save_backup(load_backup(source, allow_unsafe_pickle=True), destination)
