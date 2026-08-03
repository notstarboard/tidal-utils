from __future__ import annotations

from datetime import datetime
import argparse
import json
import logging
import sys

from .backup import create_backup, load_backup, migrate_backup
from .client import log_in
from .compare import compare_libraries
from .repair import apply_repair_plan, build_repair_plan, find_unavailable, format_plan, write_operation_log
from .report import format_text, write_report
from .restore import apply_restore_plan, build_restore_plan, format_restore_plan, write_restore_log
from .security import redact_sensitive, safe_display


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tidal-utils", description="Back up, compare, repair, and restore a TIDAL library.")
    parser.add_argument("--version", action="version", version="tidal-utils 0.2.0")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase diagnostic logging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="Create a versioned JSON backup.")
    backup.add_argument("--output-dir", default=".")
    backup.add_argument("--filename")
    backup.add_argument("--retain", type=int)
    backup.add_argument("--session-file", default="tidal-session-oauth.json")
    backup.set_defaults(handler=_backup)

    compare = subparsers.add_parser("compare", help="Compare two backups.")
    compare.add_argument("backup_old")
    compare.add_argument("backup_new", nargs="?")
    compare.add_argument("--report")
    compare.add_argument("--format", choices=["text", "json", "csv", "html"])
    compare.add_argument("--allow-unsafe-pickle", action="store_true", help="Use the restricted loader for a trusted legacy pickle backup.")
    compare.add_argument("--session-file", default="tidal-session-oauth.json")
    compare.set_defaults(handler=_compare)

    migrate = subparsers.add_parser("migrate", help="Convert a trusted legacy pickle backup to JSON.")
    migrate.add_argument("source")
    migrate.add_argument("destination")
    migrate.add_argument(
        "--trust-legacy-pickle",
        action="store_true",
        required=True,
        help="Confirm that the legacy pickle came from a trusted source.",
    )
    migrate.set_defaults(handler=_migrate)

    scan = subparsers.add_parser("scan", help="List unavailable collection and playlist items.")
    scan.add_argument("--session-file", default="tidal-session-oauth.json")
    scan.add_argument("--json", action="store_true")
    scan.set_defaults(handler=_scan)

    repair = subparsers.add_parser("repair", help="Preview or apply replacements for unavailable items.")
    repair.add_argument("--apply", action="store_true", help="Apply the plan. Without this flag, only a dry run is shown.")
    repair.add_argument("--fuzzy", action="store_true")
    repair.add_argument("--min-confidence", type=float, default=0.55)
    repair.add_argument("--interactive", action="store_true")
    repair.add_argument("--attempts", type=int, default=3)
    repair.add_argument("--log")
    repair.add_argument("--session-file", default="tidal-session-oauth.json")
    repair.set_defaults(handler=_repair)

    restore = subparsers.add_parser("restore", help="Preview or restore missing items from a backup.")
    restore.add_argument("backup")
    restore.add_argument("--apply", action="store_true")
    restore.add_argument("--include-playlists", action="store_true")
    restore.add_argument("--attempts", type=int, default=3)
    restore.add_argument("--log")
    restore.add_argument("--allow-unsafe-pickle", action="store_true", help="Use the restricted loader for a trusted legacy pickle backup.")
    restore.add_argument("--session-file", default="tidal-session-oauth.json")
    restore.set_defaults(handler=_restore)
    return parser


def _backup(args) -> int:
    path = create_backup(log_in(args.session_file), args.output_dir, args.filename, args.retain)
    print(path)
    return 0


def _compare(args) -> int:
    new_path = args.backup_new
    if not new_path:
        new_path = create_backup(log_in(args.session_file))
        print(f"Created current backup: {new_path}", file=sys.stderr)
    old = load_backup(args.backup_old, allow_unsafe_pickle=args.allow_unsafe_pickle)
    new = load_backup(new_path, allow_unsafe_pickle=args.allow_unsafe_pickle)
    diff = compare_libraries(old, new)
    if args.report:
        print(write_report(diff, args.report, args.format))
    elif args.format == "json":
        print(json.dumps(diff.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_text(diff), end="")
    return 1 if diff.has_changes else 0


def _migrate(args) -> int:
    print(migrate_backup(args.source, args.destination, trust_legacy_pickle=args.trust_legacy_pickle))
    return 0


def _scan(args) -> int:
    albums, tracks, playlist_tracks = find_unavailable(log_in(args.session_file))
    if args.json:
        print(json.dumps({
            "albums": [{"id": str(item.id), "title": item.name} for item in albums],
            "tracks": [{"id": str(item.id), "title": item.name} for item in tracks],
            "playlist_tracks": [{"playlist": playlist.name, "position": position, "id": str(item.id), "title": item.name} for playlist, position, item in playlist_tracks],
        }, indent=2, ensure_ascii=False))
    else:
        print(f"Unavailable albums: {len(albums)}")
        for album in albums:
            print(f"  {safe_display(album.id)}: {safe_display(album.name)}")
        print(f"Unavailable collection tracks: {len(tracks)}")
        for track in tracks:
            print(f"  {safe_display(track.id)}: {safe_display(track.name)}")
        print(f"Unavailable playlist tracks: {len(playlist_tracks)}")
        for playlist, position, track in playlist_tracks:
            print(f"  {safe_display(playlist.name)} #{position + 1}: {safe_display(track.id)}: {safe_display(track.name)}")
    return 0


def _repair(args) -> int:
    if not 0 <= args.min_confidence <= 1:
        raise ValueError("--min-confidence must be between 0 and 1")
    if args.attempts < 1:
        raise ValueError("--attempts must be at least 1")
    session = log_in(args.session_file)
    plan = build_repair_plan(session, fuzzy=args.fuzzy, minimum_confidence=args.min_confidence, interactive=args.interactive)
    print(format_plan(plan), end="")
    if not args.apply:
        print("Dry run only. Re-run with --apply to perform these operations.")
        return 0
    results = apply_repair_plan(session, plan, args.attempts)
    log = args.log or f"tidal_repair_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    write_operation_log(results, log)
    failed = sum(result.status == "failed" for result in results)
    print(f"Applied: {sum(result.status == 'applied' for result in results)}; failed: {failed}; log: {log}")
    return 1 if failed else 0


def _restore(args) -> int:
    if args.attempts < 1:
        raise ValueError("--attempts must be at least 1")
    backup = load_backup(args.backup, allow_unsafe_pickle=args.allow_unsafe_pickle)
    session = log_in(args.session_file)
    plan = build_restore_plan(session, backup, args.include_playlists)
    print(format_restore_plan(plan), end="")
    if not args.apply:
        print("Dry run only. Re-run with --apply to perform these operations.")
        return 0
    results = apply_restore_plan(session, plan, args.attempts)
    log = args.log or f"tidal_restore_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    write_restore_log(results, log)
    failed = sum(result.status == "failed" for result in results)
    print(f"Applied: {sum(result.status == 'applied' for result in results)}; failed: {failed}; log: {log}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        return int(args.handler(args))
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(redact_sensitive(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
