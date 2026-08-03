from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import re

from .models import AlbumSnapshot, TrackSnapshot, normalize_text

SKETCHY_KEYWORDS = {
    "acoustic", "cover", "edit", "instrumental", "live", "mix", "rediscovered",
    "redux", "reimagined", "re-imagined", "reprise", "stripped", "version", "ver.",
}


def parentheticals(value: str) -> list[str]:
    return [match.group(1) for match in re.finditer(r"[\[(]([^\])]*?)[\])]", value)]


def strip_parentheticals(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)|\[[^]]*\]", "", value)).strip()


def _keyword_signature(value: str) -> frozenset[str]:
    content = " ".join(parentheticals(normalize_text(value)))
    return frozenset(keyword for keyword in SKETCHY_KEYWORDS if keyword in content)


def fuzzy_title_match(left: str, right: str) -> bool:
    if normalize_text(strip_parentheticals(left)) != normalize_text(strip_parentheticals(right)):
        return False
    return _keyword_signature(left) == _keyword_signature(right)


@dataclass(frozen=True, slots=True)
class MatchCandidate:
    item: Any
    score: int
    confidence: float
    reasons: tuple[str, ...]


def score_track(reference: TrackSnapshot, candidate: Any, fuzzy: bool = False) -> MatchCandidate:
    candidate_snapshot = TrackSnapshot.from_api(candidate)
    score = 0
    reasons: list[str] = []
    artists_match = bool(set(map(normalize_text, reference.artists)) & set(map(normalize_text, candidate_snapshot.artists)))
    if normalize_text(reference.title) == normalize_text(candidate_snapshot.title) and artists_match:
        score += 64
        reasons.append("exact title and artist")
    elif fuzzy and fuzzy_title_match(reference.title, candidate_snapshot.title) and artists_match:
        score += 32
        reasons.append("fuzzy title and matching artist")
    if normalize_text(reference.album) == normalize_text(candidate_snapshot.album) and reference.album:
        score += 16
        reasons.append("exact album")
    elif fuzzy and reference.album and fuzzy_title_match(reference.album, candidate_snapshot.album):
        score += 8
        reasons.append("fuzzy album")
    if reference.explicit is not None and reference.explicit == candidate_snapshot.explicit:
        score += 2
    if reference.audio_quality and reference.audio_quality == candidate_snapshot.audio_quality:
        score += 1
    confidence = min(score / 83, 1.0)
    return MatchCandidate(candidate, score, confidence, tuple(reasons))


def score_album(reference: AlbumSnapshot, candidate: Any, fuzzy: bool = False) -> MatchCandidate:
    candidate_snapshot = AlbumSnapshot.from_api(candidate)
    score = 0
    reasons: list[str] = []
    artists_match = bool(set(map(normalize_text, reference.artists)) & set(map(normalize_text, candidate_snapshot.artists)))
    if normalize_text(reference.title) == normalize_text(candidate_snapshot.title) and artists_match:
        score += 32
        reasons.append("exact title and artist")
    elif fuzzy and fuzzy_title_match(reference.title, candidate_snapshot.title) and artists_match:
        score += 16
        reasons.append("fuzzy title and matching artist")
    if reference.num_tracks is not None and reference.num_tracks == candidate_snapshot.num_tracks:
        score += 8
    if reference.explicit is not None and reference.explicit == candidate_snapshot.explicit:
        score += 4
    if reference.audio_quality and reference.audio_quality == candidate_snapshot.audio_quality:
        score += 2
    confidence = min(score / 46, 1.0)
    return MatchCandidate(candidate, score, confidence, tuple(reasons))


def rank_candidates(reference: TrackSnapshot | AlbumSnapshot, candidates: Iterable[Any], fuzzy: bool = False) -> list[MatchCandidate]:
    scorer = score_track if isinstance(reference, TrackSnapshot) else score_album
    return sorted((scorer(reference, candidate, fuzzy) for candidate in candidates), key=lambda result: result.score, reverse=True)


def search_track_candidates(session: Any, reference: TrackSnapshot, fuzzy: bool = False, limit: int = 300) -> list[MatchCandidate]:
    from .client import require_tidalapi

    tidalapi = require_tidalapi()
    artist = reference.artists[0] if reference.artists else ""
    query = f"{strip_parentheticals(reference.title)} {artist}".strip()
    results = session.search(query=query, limit=limit, models=[tidalapi.media.Track]).get("tracks", [])
    return rank_candidates(reference, results, fuzzy)


def search_album_candidates(session: Any, reference: AlbumSnapshot, fuzzy: bool = False, limit: int = 300) -> list[MatchCandidate]:
    from .client import require_tidalapi

    tidalapi = require_tidalapi()
    artist = reference.artists[0] if reference.artists else ""
    query = f"{strip_parentheticals(reference.title)} {artist}".strip()
    results = session.search(query=query, limit=limit, models=[tidalapi.album.Album]).get("albums", [])
    return rank_candidates(reference, results, fuzzy)


def choose_candidate(candidates: list[MatchCandidate], minimum_confidence: float) -> MatchCandidate | None:
    if not candidates or candidates[0].confidence < minimum_confidence:
        return None
    return candidates[0]
