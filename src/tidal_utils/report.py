from __future__ import annotations

from html import escape
from io import StringIO
from pathlib import Path
from typing import Iterable
import csv
import json

from .compare import LibraryDiff
from .security import csv_safe, safe_display, secure_write_text


def _track_line(track) -> str:
    return f"{safe_display(track.id)}: '{safe_display(track.title)}' by '{safe_display(track.display_artist())}'"


def _album_line(album) -> str:
    return f"{safe_display(album.id)}: '{safe_display(album.title)}' by '{safe_display(album.display_artist())}'"


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
    section("Removed playlists:", (safe_display(playlist.title) for playlist in diff.removed_playlists))
    section("Added playlists:", (safe_display(playlist.title) for playlist in diff.added_playlists))

    lines.extend(["Playlist changes:", ""])
    if not diff.playlist_changes:
        lines.extend(["None", ""])
    for playlist in diff.playlist_changes:
        lines.append(safe_display(playlist.playlist_title))
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
    if fmt in {"txt", "text"}:
        return secure_write_text(path, format_text(diff))
    if fmt == "json":
        return secure_write_text(path, json.dumps(diff.to_dict(), indent=2, ensure_ascii=False) + "\n")
    if fmt == "csv":
        return secure_write_text(path, _format_csv(diff))
    if fmt in {"html", "htm"}:
        body = escape(format_text(diff))
        return secure_write_text(
            path,
            "<!doctype html><html><head><meta charset='utf-8'><title>TIDAL library diff</title>"
            "<style>body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}"
            "pre{white-space:pre-wrap}</style></head><body><h1>TIDAL library diff</h1>"
            f"<pre>{body}</pre></body></html>\n",
        )
    raise ValueError(f"Unsupported report format: {fmt}")


def _format_csv(diff: LibraryDiff) -> str:
    output = StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=["scope", "change", "playlist", "id", "title", "artists"],
    )
    writer.writeheader()

    def row(**values) -> dict[str, str]:
        return {key: csv_safe(value) for key, value in values.items()}

    for change, items in (("removed", diff.removed_tracks), ("added", diff.added_tracks)):
        for track in items:
            writer.writerow(row(scope="track", change=change, playlist="", id=track.id, title=track.title, artists=track.display_artist()))
    for change, items in (("removed", diff.removed_albums), ("added", diff.added_albums)):
        for album in items:
            writer.writerow(row(scope="album", change=change, playlist="", id=album.id, title=album.title, artists=album.display_artist()))
    for change, items in (("removed", diff.removed_playlists), ("added", diff.added_playlists)):
        for playlist in items:
            writer.writerow(row(scope="playlist", change=change, playlist=playlist.title, id=playlist.id, title=playlist.title, artists=""))
    for playlist in diff.playlist_changes:
        for change, items in (("removed", playlist.removed_tracks), ("added", playlist.added_tracks), ("unavailable", playlist.unavailable_tracks)):
            for track in items:
                writer.writerow(row(scope="playlist_track", change=change, playlist=playlist.playlist_title, id=track.id, title=track.title, artists=track.display_artist()))
        if playlist.order_changed:
            writer.writerow(row(scope="playlist", change="reordered", playlist=playlist.playlist_title, id=playlist.playlist_id, title=playlist.playlist_title, artists=""))
    return output.getvalue()
