from __future__ import annotations

from tidal_utils.matching import choose_candidate, fuzzy_title_match, parentheticals, rank_candidates, strip_parentheticals
from tidal_utils.models import TrackSnapshot

from conftest import Album, Artist, Track


def test_parentheticals_are_flat_and_non_greedy():
    assert parentheticals("Song (Live) [2024 Mix]") == ["Live", "2024 Mix"]
    assert strip_parentheticals("Song (Live) [2024 Mix]") == "Song"


def test_fuzzy_match_rejects_different_version_keywords():
    assert fuzzy_title_match("Song (Remastered)", "Song")
    assert not fuzzy_title_match("Song (Live)", "Song")


def test_empty_candidate_list_is_safe():
    assert rank_candidates(TrackSnapshot("1", "Song", ("Artist",)), []) == []
    assert choose_candidate([], 0.5) is None


def test_exact_match_ranks_above_unrelated_candidate():
    artist = Artist("Artist")
    album = Album("a", "Album", artist)
    exact = Track("1", "Song", artist, album)
    unrelated_artist = Artist("Other")
    unrelated = Track("2", "Different", unrelated_artist, Album("b", "Else", unrelated_artist))
    ranked = rank_candidates(TrackSnapshot("old", "Song", ("Artist",), "Album"), [unrelated, exact])
    assert ranked[0].item is exact
    assert ranked[0].confidence > ranked[1].confidence
