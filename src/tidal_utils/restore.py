from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from .backup import snapshot_from_session
from .client import retry
from .compare import compare_libraries
from .models import LibraryBackup, normalize_text
from .security import redact_sensitive, safe_display, secure_write_text


@dataclass(frozen=True, slots=True)
class RestoreAction:
    kind: str
    id: str
    title: str
    playlist: str | None = None
    position: int | None = None


@dataclass(frozen=True, slots=True)
class RestoreResult:
    action: RestoreAction
    status: str
    error: str | None = None


def build_restore_plan(session: Any, backup: LibraryBackup, include_playlists: bool = False) -> list[RestoreAction]:
    current = snapshot_from_session(session)
    diff = compare_libraries(current, backup)
    plan = [RestoreAction("track", track.id, track.title) for track in diff.added_tracks]
    plan.extend(RestoreAction("album", album.id, album.title) for album in diff.added_albums)
    if include_playlists:
        current_by_name = {normalize_text(playlist.title): playlist for playlist in current.playlists}
        for playlist in backup.playlists:
            current_playlist = current_by_name.get(normalize_text(playlist.title))
            current_counts = Counter(track.match_key() for track in current_playlist.tracks) if current_playlist else Counter()
            if current_playlist is None:
                plan.append(RestoreAction("playlist", playlist.id, playlist.title))
            for position, track in enumerate(playlist.tracks):
                key = track.match_key()
                if current_counts[key]:
                    current_counts[key] -= 1
                else:
                    plan.append(RestoreAction("playlist_track", track.id, track.title, playlist.title, position))
    return plan


def format_restore_plan(plan: list[RestoreAction]) -> str:
    if not plan:
        return "The current library already contains every selected backup item.\n"
    return "\n".join(
        f"{action.kind}: {safe_display(action.title)} [{safe_display(action.id)}]"
        + (f" in '{safe_display(action.playlist)}' at position {action.position}" if action.playlist else "")
        for action in plan
    ) + "\n"


def _api_id(value: str):
    return int(value) if value.isdigit() else value


def apply_restore_plan(session: Any, plan: list[RestoreAction], attempts: int = 3) -> list[RestoreResult]:
    playlists = {normalize_text(playlist.name): playlist for playlist in session.user.playlists()}
    results: list[RestoreResult] = []
    for action in plan:
        try:
            if action.kind == "track":
                ok = retry(lambda: session.user.favorites.add_track(_api_id(action.id)), attempts)
            elif action.kind == "album":
                ok = retry(lambda: session.user.favorites.add_album(_api_id(action.id)), attempts)
            elif action.kind == "playlist":
                playlist = retry(lambda: session.user.create_playlist(action.title, "Restored by tidal-utils"), attempts)
                playlists[normalize_text(action.title)] = playlist
                ok = playlist is not None
            else:
                playlist = playlists.get(normalize_text(action.playlist))
                if playlist is None:
                    playlist = retry(lambda: session.user.create_playlist(action.playlist, "Restored by tidal-utils"), attempts)
                    playlists[normalize_text(action.playlist)] = playlist
                ok = retry(lambda: playlist.add(media_ids=[_api_id(action.id)], position=action.position), attempts)
            if not ok:
                raise RuntimeError("TIDAL rejected the restore operation")
            results.append(RestoreResult(action, "applied"))
        except Exception as exc:
            results.append(RestoreResult(action, "failed", redact_sensitive(exc)))
    return results


def write_restore_log(results: list[RestoreResult], filename: str | Path) -> Path:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    return secure_write_text(
        path,
        json.dumps(
            {"created_at": datetime.now(timezone.utc).isoformat(), "results": [asdict(result) for result in results]},
            indent=2,
            ensure_ascii=False,
        ) + "\n",
    )
