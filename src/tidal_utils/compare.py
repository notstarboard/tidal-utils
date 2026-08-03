from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Any, Callable, Hashable, Iterable, TypeVar

from .models import AlbumSnapshot, LibraryBackup, PlaylistSnapshot, TrackSnapshot

T = TypeVar("T")


def _multiset_difference(
    old: Iterable[T], new: Iterable[T], key: Callable[[T], Hashable]
) -> tuple[list[T], list[T]]:
    old_buckets: dict[Hashable, deque[T]] = defaultdict(deque)
    new_buckets: dict[Hashable, deque[T]] = defaultdict(deque)
    for item in old:
        old_buckets[key(item)].append(item)
    for item in new:
        new_buckets[key(item)].append(item)

    removed: list[T] = []
    added: list[T] = []
    for item_key in old_buckets.keys() | new_buckets.keys():
        old_items = old_buckets[item_key]
        new_items = new_buckets[item_key]
        overlap = min(len(old_items), len(new_items))
        for _ in range(overlap):
            old_items.popleft()
            new_items.popleft()
        removed.extend(old_items)
        added.extend(new_items)
    return removed, added


@dataclass(frozen=True, slots=True)
class PlaylistDiff:
    playlist_id: str
    playlist_title: str
    removed_tracks: tuple[TrackSnapshot, ...] = ()
    added_tracks: tuple[TrackSnapshot, ...] = ()
    order_changed: bool = False
    unavailable_tracks: tuple[TrackSnapshot, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LibraryDiff:
    removed_tracks: tuple[TrackSnapshot, ...] = ()
    added_tracks: tuple[TrackSnapshot, ...] = ()
    removed_albums: tuple[AlbumSnapshot, ...] = ()
    added_albums: tuple[AlbumSnapshot, ...] = ()
    removed_playlists: tuple[PlaylistSnapshot, ...] = ()
    added_playlists: tuple[PlaylistSnapshot, ...] = ()
    playlist_changes: tuple[PlaylistDiff, ...] = ()

    @property
    def has_changes(self) -> bool:
        return any(
            (
                self.removed_tracks,
                self.added_tracks,
                self.removed_albums,
                self.added_albums,
                self.removed_playlists,
                self.added_playlists,
                self.playlist_changes,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _playlist_pairs(
    old: tuple[PlaylistSnapshot, ...], new: tuple[PlaylistSnapshot, ...]
) -> tuple[list[tuple[PlaylistSnapshot, PlaylistSnapshot]], list[PlaylistSnapshot], list[PlaylistSnapshot]]:
    new_id_indexes = {playlist.id: index for index, playlist in enumerate(new) if playlist.id}
    consumed: set[int] = set()
    pairs: list[tuple[PlaylistSnapshot, PlaylistSnapshot]] = []
    removed: list[PlaylistSnapshot] = []

    for old_playlist in old:
        match_index = new_id_indexes.get(old_playlist.id) if old_playlist.id else None
        if match_index in consumed:
            match_index = None
        if match_index is None:
            for index, candidate in enumerate(new):
                if index not in consumed and old_playlist.match_key() == candidate.match_key():
                    match_index = index
                    break
        if match_index is None:
            removed.append(old_playlist)
        else:
            pairs.append((old_playlist, new[match_index]))
            consumed.add(match_index)

    added = [playlist for index, playlist in enumerate(new) if index not in consumed]
    return pairs, removed, added


def compare_libraries(old: LibraryBackup, new: LibraryBackup) -> LibraryDiff:
    removed_tracks, added_tracks = _multiset_difference(old.tracks, new.tracks, TrackSnapshot.match_key)
    removed_albums, added_albums = _multiset_difference(old.albums, new.albums, AlbumSnapshot.match_key)
    pairs, removed_playlists, added_playlists = _playlist_pairs(old.playlists, new.playlists)

    playlist_changes: list[PlaylistDiff] = []
    for old_playlist, new_playlist in pairs:
        removed, added = _multiset_difference(
            old_playlist.tracks, new_playlist.tracks, TrackSnapshot.match_key
        )
        old_sequence = [track.match_key() for track in old_playlist.tracks]
        new_sequence = [track.match_key() for track in new_playlist.tracks]
        order_changed = Counter(old_sequence) == Counter(new_sequence) and old_sequence != new_sequence
        unavailable = tuple(
            track
            for track in new_playlist.tracks
            if track.available is False
            or (
                track.title.casefold() == "unavailable"
                and any(artist.casefold() == "unknown artist" for artist in track.artists)
            )
        )
        if removed or added or order_changed or unavailable:
            playlist_changes.append(
                PlaylistDiff(
                    playlist_id=new_playlist.id or old_playlist.id,
                    playlist_title=new_playlist.title or old_playlist.title,
                    removed_tracks=tuple(sorted(removed, key=lambda item: (item.display_artist(), item.title))),
                    added_tracks=tuple(sorted(added, key=lambda item: (item.display_artist(), item.title))),
                    order_changed=order_changed,
                    unavailable_tracks=unavailable,
                )
            )

    return LibraryDiff(
        removed_tracks=tuple(sorted(removed_tracks, key=lambda item: (item.display_artist(), item.title))),
        added_tracks=tuple(sorted(added_tracks, key=lambda item: (item.display_artist(), item.title))),
        removed_albums=tuple(sorted(removed_albums, key=lambda item: (item.display_artist(), item.title))),
        added_albums=tuple(sorted(added_albums, key=lambda item: (item.display_artist(), item.title))),
        removed_playlists=tuple(sorted(removed_playlists, key=lambda item: item.title.casefold())),
        added_playlists=tuple(sorted(added_playlists, key=lambda item: item.title.casefold())),
        playlist_changes=tuple(sorted(playlist_changes, key=lambda item: item.playlist_title.casefold())),
    )
