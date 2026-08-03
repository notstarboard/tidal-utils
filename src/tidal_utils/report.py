from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable
import csv
import json

from .compare import LibraryDiff


def _track_line(track) -> str:
    return f"{track.id}: '{track.title}' by '{track.display_artist()}'"


def _album_line(album) -> str:
    return f"{album.id}: '{album.title}' by '{album.display_artist()}'"


def format_text(diff: LibraryDiff) -> str:
    lines: list[str] = []

    def section(title: str, values: Iterable[str]) -> None:
        items = list(values)
        lines.extend([title, ""])
        lines.extend(items or ["None"])
        lines.append("")

    section("Removed albums:", (_album_line(album) for album in diff.removed_albums))
    section("Added albums:", (_album_line(album) for album in diff.added_albums))
    section("Removed tracks:", (_track_line(track) for track in diff.removed_tracks))
    section("Added tracks:", (_track_line(track) for track in diff.added_tracks))
    section("Removed playlists:", (playlist.title for playlist in diff.removed_playlists))
    section("Added playlists:", (playlist.title for playlist in diff.added_playlists))

    lines.extend(["Playlist changes:", ""])
    if not diff.playlist_changes:
        lines.extend(["None", ""])
    for playlist in diff.playlist_changes:
        lines.append(playlist.playlist_title)
        if playlist.order_changed:
            lines.append("  - Track order changed")
        for track in playlist.removed_tracks:
            lines.append(f"  - Removed: {_track_line(track)}")
        for track in playlist.added_tracks:
            lines.append(f"  - Added: {_track_line(track)}")
        for track in playlist.unavailable_tracks:
            lines.append(f"  - Unavailable: {_track_line(track)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(diff: LibraryDiff, filename: str | Path, output_format: str | None = None) -> Path:
    path = Path(filename)
    fmt = (output_format or path.suffix.lstrip(".") or "text").casefold()
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt in {"txt", "text"}:
        path.write_text(format_text(diff), encoding="utf-8")
    elif fmt == "json":
        path.write_text(json.dumps(diff.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    elif fmt == "csv":
        _write_csv(diff, path)
    elif fmt in {"html", "htm"}:
        body = escape(format_text(diff))
        path.write_text(
            "<!doctype html><html><head><meta charset='utf-8'><title>TIDAL library diff</title>"
            "<style>body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}"
            "pre{white-space:pre-wrap}</style></head><body><h1>TIDAL library diff</h1>"
            f"<pre>{body}</pre></body></html>\n",
            encoding="utf-8",
        )
    else:
        raise ValueError(f"Unsupported report format: {fmt}")
    return path


def _write_csv(diff: LibraryDiff, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["scope", "change", "playlist", "id", "title", "artists"],
        )
        writer.writeheader()
        for change, items in (("removed", diff.removed_tracks), ("added", diff.added_tracks)):
            for track in items:
                writer.writerow({"scope": "track", "change": change, "playlist": "", "id": track.id, "title": track.title, "artists": track.display_artist()})
        for change, items in (("removed", diff.removed_albums), ("added", diff.added_albums)):
            for album in items:
                writer.writerow({"scope": "album", "change": change, "playlist": "", "id": album.id, "title": album.title, "artists": album.display_artist()})
        for change, items in (("removed", diff.removed_playlists), ("added", diff.added_playlists)):
            for playlist in items:
                writer.writerow({"scope": "playlist", "change": change, "playlist": playlist.title, "id": playlist.id, "title": playlist.title, "artists": ""})
        for playlist in diff.playlist_changes:
            for change, items in (("removed", playlist.removed_tracks), ("added", playlist.added_tracks), ("unavailable", playlist.unavailable_tracks)):
                for track in items:
                    writer.writerow({"scope": "playlist_track", "change": change, "playlist": playlist.playlist_title, "id": track.id, "title": track.title, "artists": track.display_artist()})
            if playlist.order_changed:
                writer.writerow({"scope": "playlist", "change": "reordered", "playlist": playlist.playlist_title, "id": playlist.playlist_id, "title": playlist.playlist_title, "artists": ""})
