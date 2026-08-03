from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import json
import os
import pickle
import warnings

from .models import AlbumSnapshot, LibraryBackup, PlaylistSnapshot, TrackSnapshot


def snapshot_from_session(session: Any) -> LibraryBackup:
    tracks = tuple(TrackSnapshot.from_api(track) for track in session.user.favorites.tracks(limit=9999))
    albums = tuple(AlbumSnapshot.from_api(album) for album in session.user.favorites.albums(limit=9999))
    playlists = tuple(
        PlaylistSnapshot.from_api(playlist, playlist.tracks())
        for playlist in session.user.playlists()
    )
    return LibraryBackup(tracks=tracks, albums=albums, playlists=playlists)


def save_backup(backup: LibraryBackup, filename: str | Path) -> Path:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(backup.to_dict(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(temporary, path)
    return path


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
    path = Path(filename)
    with path.open("rb") as handle:
        prefix = handle.read(64).lstrip()
    if prefix.startswith((b"{", b"[")):
        with path.open("r", encoding="utf-8") as handle:
            return LibraryBackup.from_dict(json.load(handle))
    if not allow_unsafe_pickle:
        raise ValueError(
            "This appears to be a legacy pickle backup. Pickle can execute code while loading. "
            "Only load a file you trust, and pass --allow-unsafe-pickle to migrate it."
        )
    warnings.warn(
        "Loading a legacy pickle backup. Only trusted pickle files should be opened.",
        RuntimeWarning,
        stacklevel=2,
    )
    return _load_legacy_pickle(path)


def _load_legacy_pickle(path: Path) -> LibraryBackup:
    with path.open("rb") as handle:
        tracks = pickle.load(handle)  # noqa: S301 - explicit opt-in migration path
        albums = pickle.load(handle)  # noqa: S301
        playlists = pickle.load(handle)  # noqa: S301
        try:
            playlist_tracks = pickle.load(handle)  # noqa: S301
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


def migrate_backup(source: str | Path, destination: str | Path) -> Path:
    return save_backup(load_backup(source, allow_unsafe_pickle=True), destination)
