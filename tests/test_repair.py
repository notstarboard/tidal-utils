from __future__ import annotations

from tidal_utils.repair import RepairAction, apply_repair_plan


class Favorites:
    def __init__(self, add=True, remove=True):
        self.add = add
        self.remove = remove

    def add_track(self, identifier):
        return self.add

    def remove_track(self, identifier):
        return self.remove


class User:
    def __init__(self, favorites):
        self.favorites = favorites

    def playlists(self):
        return []


class Session:
    def __init__(self, favorites):
        self.user = User(favorites)


def action():
    return RepairAction("track", "1", "Old", "Artist", "2", "New", 0.9)


def test_apply_repair_records_add_failure():
    results = apply_repair_plan(Session(Favorites(add=False)), [action()], attempts=1)
    assert results[0].status == "failed"
    assert "could not be added" in results[0].error


def test_apply_repair_records_partial_failure():
    results = apply_repair_plan(Session(Favorites(add=True, remove=False)), [action()], attempts=1)
    assert results[0].status == "failed"
    assert "could not be removed" in results[0].error
