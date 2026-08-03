"""Compatibility wrapper for the historic compare_backups.py entry point."""

from __future__ import annotations

from tidal_utils.backup import create_backup, load_backup
from tidal_utils.client import log_in
from tidal_utils.compare import compare_libraries
from tidal_utils.models import AlbumSnapshot, LibraryBackup, PlaylistSnapshot, TrackSnapshot
from tidal_utils.report import format_text
import argparse


def build_parser():
    parser = argparse.ArgumentParser(description="Compare two TIDAL library backups.")
    parser.add_argument("backup_old")
    parser.add_argument("backup_new", nargs="?")
    parser.add_argument("--allow-unsafe-pickle", action="store_true")
    return parser


def compare_albums(albums_old, albums_new):
    old = LibraryBackup(albums=tuple(AlbumSnapshot.from_api(item) for item in albums_old))
    new = LibraryBackup(albums=tuple(AlbumSnapshot.from_api(item) for item in albums_new))
    return list(compare_libraries(old, new).removed_albums)


def compare_tracks(tracks_old, tracks_new):
    old = LibraryBackup(tracks=tuple(TrackSnapshot.from_api(item) for item in tracks_old))
    new = LibraryBackup(tracks=tuple(TrackSnapshot.from_api(item) for item in tracks_new))
    return list(compare_libraries(old, new).removed_tracks)


def compare_playlists(playlists_old, playlists_new, playlist_tracks_old, playlist_tracks_new):
    old_playlists = tuple(
        PlaylistSnapshot.from_api(playlist, playlist_tracks_old[index] if index < len(playlist_tracks_old) else [])
        for index, playlist in enumerate(playlists_old)
    )
    new_playlists = tuple(
        PlaylistSnapshot.from_api(playlist, playlist_tracks_new[index] if index < len(playlist_tracks_new) else [])
        for index, playlist in enumerate(playlists_new)
    )
    diff = compare_libraries(LibraryBackup(playlists=old_playlists), LibraryBackup(playlists=new_playlists))
    removed = []
    corresponding = []
    imperfect = []
    old_by_id = {playlist.id: playlist for playlist in playlists_old}
    new_by_id = {playlist.id: playlist for playlist in playlists_new}
    for change in diff.playlist_changes:
        for track in change.removed_tracks:
            removed.append(track)
            corresponding.append(old_by_id.get(change.playlist_id) or new_by_id.get(change.playlist_id))
        if change.unavailable_tracks:
            imperfect.append(new_by_id.get(change.playlist_id) or old_by_id.get(change.playlist_id))
    return removed, corresponding, [item for item in imperfect if item is not None]


def compare_backups(args, backup_old, backup_new):
    old = load_backup(backup_old, allow_unsafe_pickle=args.allow_unsafe_pickle)
    new = load_backup(backup_new, allow_unsafe_pickle=args.allow_unsafe_pickle)
    diff = compare_libraries(old, new)
    print(format_text(diff), end="")
    return diff


def main():
    args = build_parser().parse_args()
    if not args.backup_new:
        args.backup_new = str(create_backup(log_in()))
    compare_backups(args, args.backup_old, args.backup_new)


if __name__ == "__main__":
    main()
