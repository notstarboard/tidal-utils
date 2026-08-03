"""Compatibility wrapper for the historic fix_unavailable.py entry point."""

from __future__ import annotations

import argparse

from tidal_utils.client import log_in
from tidal_utils.matching import fuzzy_title_match, parentheticals, strip_parentheticals
from tidal_utils.repair import apply_repair_plan, build_repair_plan, find_unavailable, format_plan, write_operation_log

__all__ = [
    "build_parser", "find_gray_albums", "find_gray_playlists", "find_gray_tracks",
    "is_fuzzy_match_album", "is_fuzzy_match_artist", "is_fuzzy_match_track",
    "is_valid", "log_in", "main", "parentheticals", "strip_parentheticals",
]


def build_parser():
    parser = argparse.ArgumentParser(description="Identify and optionally replace unavailable TIDAL items.")
    parser.add_argument("-f", action="store_true", help="Use fuzzy metadata matching.")
    parser.add_argument("-r", action="store_true", help="Apply replacements; otherwise run safely as a preview.")
    parser.add_argument("-p", action="store_true", help="Deprecated; playlist tracks are included automatically.")
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--session-file", default="tidal-session-oauth.json")
    parser.add_argument("--log", default="tidal_repair_log.json")
    return parser


def find_gray_albums(session):
    return find_unavailable(session)[0]


def find_gray_tracks(session):
    return find_unavailable(session)[1]


def find_gray_playlists(session):
    items = find_unavailable(session)[2]
    playlists = []
    tracks = []
    seen = set()
    for playlist, _, track in items:
        if str(playlist.id) not in seen:
            playlists.append(playlist)
            seen.add(str(playlist.id))
        tracks.append(track)
    return sorted(playlists, key=lambda item: item.name.casefold()), tracks


def is_fuzzy_match_album(album1, album2):
    return fuzzy_title_match(album1.name, album2.name)


def is_fuzzy_match_track(track1, track2):
    return fuzzy_title_match(track1.name, track2.name)


def is_fuzzy_match_artist(gray_obj, search_obj):
    reference = gray_obj.artist.name.casefold()
    return any(getattr(artist, "name", "").casefold() == reference for artist in search_obj.artists)


def is_valid(args):
    if args.p:
        print("WARNING: -p is deprecated; playlist tracks are included automatically.")
    if args.f and not args.r:
        print("INFO: fuzzy matching is being used for the dry-run preview.")
    return 0 <= args.min_confidence <= 1


def main():
    args = build_parser().parse_args()
    if not is_valid(args):
        raise SystemExit("--min-confidence must be between 0 and 1")
    session = log_in(args.session_file)
    plan = build_repair_plan(
        session,
        fuzzy=args.f,
        minimum_confidence=args.min_confidence,
        interactive=args.interactive,
    )
    print(format_plan(plan), end="")
    if not args.r:
        print("Dry run only. Re-run with -r to apply these operations.")
        return
    results = apply_repair_plan(session, plan)
    write_operation_log(results, args.log)
    print(f"Operation log: {args.log}")


if __name__ == "__main__":
    main()
