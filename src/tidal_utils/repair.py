from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from .client import retry
from .matching import choose_candidate, search_album_candidates, search_track_candidates
from .models import AlbumSnapshot, TrackSnapshot
from .security import redact_sensitive, safe_display, secure_write_text


@dataclass(frozen=True, slots=True)
class RepairAction:
    kind: str
    old_id: str
    old_title: str
    old_artist: str
    replacement_id: str | None
    replacement_title: str | None
    confidence: float
    playlist_id: str | None = None
    playlist_title: str | None = None
    position: int | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class OperationResult:
    action: RepairAction
    status: str
    error: str | None = None


def find_unavailable(session: Any) -> tuple[list[Any], list[Any], list[tuple[Any, int, Any]]]:
    albums = [album for album in session.user.favorites.albums(limit=9999) if not getattr(album, "available", True)]
    tracks = [track for track in session.user.favorites.tracks(limit=9999) if not getattr(track, "available", True)]
    playlist_tracks: list[tuple[Any, int, Any]] = []
    for playlist in session.user.playlists():
        for position, track in enumerate(playlist.tracks()):
            if not getattr(track, "available", True):
                playlist_tracks.append((playlist, position, track))
    return albums, tracks, playlist_tracks


def _interactive_pick(candidates, label: str):
    print(f"\nAmbiguous replacement for {safe_display(label)}:")
    for index, candidate in enumerate(candidates[:5], start=1):
        item = candidate.item
        artist = getattr(getattr(item, "artist", None), "name", "Unknown Artist")
        print(f"  {index}. {safe_display(getattr(item, 'name', ''))} — {safe_display(artist)} ({candidate.confidence:.0%})")
    response = input("Choose 1-5, or press Enter to skip: ").strip()
    if response.isdigit() and 1 <= int(response) <= min(5, len(candidates)):
        return candidates[int(response) - 1]
    return None


def build_repair_plan(
    session: Any,
    *,
    fuzzy: bool = False,
    minimum_confidence: float = 0.55,
    interactive: bool = False,
) -> list[RepairAction]:
    albums, tracks, playlist_tracks = find_unavailable(session)
    plan: list[RepairAction] = []

    for album in albums:
        snapshot = AlbumSnapshot.from_api(album)
        candidates = search_album_candidates(session, snapshot, fuzzy)
        selected = choose_candidate(candidates, minimum_confidence)
        if interactive and (selected is None or (len(candidates) > 1 and candidates[0].score == candidates[1].score)):
            selected = _interactive_pick(candidates, f"album '{snapshot.title}'")
        plan.append(_action("album", snapshot, selected))

    for track in tracks:
        snapshot = TrackSnapshot.from_api(track)
        candidates = search_track_candidates(session, snapshot, fuzzy)
        selected = choose_candidate(candidates, minimum_confidence)
        if interactive and (selected is None or (len(candidates) > 1 and candidates[0].score == candidates[1].score)):
            selected = _interactive_pick(candidates, f"track '{snapshot.title}'")
        plan.append(_action("track", snapshot, selected))

    for playlist, position, track in playlist_tracks:
        snapshot = TrackSnapshot.from_api(track)
        candidates = search_track_candidates(session, snapshot, fuzzy)
        selected = choose_candidate(candidates, minimum_confidence)
        if interactive and (selected is None or (len(candidates) > 1 and candidates[0].score == candidates[1].score)):
            selected = _interactive_pick(candidates, f"'{snapshot.title}' in '{playlist.name}'")
        plan.append(
            _action(
                "playlist_track",
                snapshot,
                selected,
                playlist_id=str(playlist.id),
                playlist_title=playlist.name,
                position=position,
            )
        )
    return plan


def _action(kind, snapshot, selected, **kwargs) -> RepairAction:
    item = selected.item if selected else None
    return RepairAction(
        kind=kind,
        old_id=snapshot.id,
        old_title=snapshot.title,
        old_artist=snapshot.display_artist(),
        replacement_id=str(getattr(item, "id", "")) if item is not None else None,
        replacement_title=str(getattr(item, "name", "")) if item is not None else None,
        confidence=selected.confidence if selected else 0.0,
        reason=", ".join(selected.reasons) if selected else "no candidate met the confidence threshold",
        **kwargs,
    )


def format_plan(plan: list[RepairAction]) -> str:
    if not plan:
        return "No unavailable items found.\n"
    lines = []
    for action in plan:
        scope = f" in '{safe_display(action.playlist_title)}'" if action.playlist_title else ""
        if action.replacement_id:
            lines.append(
                f"{action.kind}: '{safe_display(action.old_title)}' by '{safe_display(action.old_artist)}'{scope} -> "
                f"'{safe_display(action.replacement_title)}' [{safe_display(action.replacement_id)}] "
                f"({action.confidence:.0%}; {safe_display(action.reason)})"
            )
        else:
            lines.append(f"{action.kind}: '{safe_display(action.old_title)}' by '{safe_display(action.old_artist)}'{scope} -> NO MATCH")
    return "\n".join(lines) + "\n"


def _api_id(value: str):
    return int(value) if value.isdigit() else value


def apply_repair_plan(session: Any, plan: list[RepairAction], attempts: int = 3) -> list[OperationResult]:
    playlists = {str(playlist.id): playlist for playlist in session.user.playlists()}
    results: list[OperationResult] = []
    for action in plan:
        if not action.replacement_id:
            results.append(OperationResult(action, "skipped", "no replacement selected"))
            continue
        try:
            if action.kind == "album":
                added = retry(lambda: session.user.favorites.add_album(_api_id(action.replacement_id)), attempts)
                if not added:
                    raise RuntimeError("replacement album could not be added")
                removed = retry(lambda: session.user.favorites.remove_album(_api_id(action.old_id)), attempts)
            elif action.kind == "track":
                added = retry(lambda: session.user.favorites.add_track(_api_id(action.replacement_id)), attempts)
                if not added:
                    raise RuntimeError("replacement track could not be added")
                removed = retry(lambda: session.user.favorites.remove_track(_api_id(action.old_id)), attempts)
            else:
                playlist = playlists.get(action.playlist_id or "")
                if playlist is None:
                    raise RuntimeError("playlist no longer exists")
                added = retry(
                    lambda: playlist.add(media_ids=[_api_id(action.replacement_id)], position=action.position),
                    attempts,
                )
                if not added:
                    raise RuntimeError("replacement playlist track could not be added")
                removed = retry(lambda: playlist.remove_by_id(_api_id(action.old_id)), attempts)
            if not removed:
                raise RuntimeError("replacement was added but the unavailable item could not be removed")
            results.append(OperationResult(action, "applied"))
        except Exception as exc:
            results.append(OperationResult(action, "failed", redact_sensitive(exc)))
    return results


def write_operation_log(results: list[OperationResult], filename: str | Path) -> Path:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "results": [asdict(result) for result in results],
    }
    return secure_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
