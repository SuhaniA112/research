"""Ranking math for recommendations (pure numpy, no I/O)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

# Weight of "matches your interests" vs "like papers you saved" in the blended score.
INTEREST_WEIGHT = 0.7
# MMR trade-off: 1.0 = pure relevance, 0.0 = pure diversity.
MMR_LAMBDA = 0.75


def unit(rows: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
    """Row-normalise to unit length (zero rows stay zero)."""
    x = np.asarray(rows, dtype=np.float64)
    if x.ndim == 1:
        x = x[None, :]
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(norms == 0, 1.0, norms)


def centroid(rows: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray | None:
    """Unit mean direction of a set of vectors, or None if empty."""
    x = np.asarray(rows, dtype=np.float64)
    if x.size == 0:
        return None
    return unit(unit(x).mean(axis=0))[0]


def blend_scores(
    interest_sims: np.ndarray, saved_sims: np.ndarray | None
) -> np.ndarray:
    """Final relevance: best interest match, blended with similarity to saved papers."""
    if saved_sims is None:
        return interest_sims
    return INTEREST_WEIGHT * interest_sims + (1 - INTEREST_WEIGHT) * saved_sims


def score_candidates(
    candidates: np.ndarray,
    interests: np.ndarray,
    saved: np.ndarray | None,
) -> dict[str, np.ndarray]:
    """Cosine scores for each candidate.

    Returns ``interest`` (max over interest vectors), ``best_interest`` (argmax),
    ``saved`` (max over saved papers, or NaN) and the blended ``score``.
    """
    c = unit(candidates)
    by_interest = c @ unit(interests).T
    interest_sims = by_interest.max(axis=1)
    saved_sims = (c @ unit(saved).T).max(axis=1) if saved is not None and len(saved) else None
    return {
        "interest": interest_sims,
        "best_interest": by_interest.argmax(axis=1),
        "saved": saved_sims if saved_sims is not None else np.full(len(c), np.nan),
        "score": blend_scores(interest_sims, saved_sims),
    }


def mmr(
    vectors: np.ndarray, scores: np.ndarray, k: int, lam: float = MMR_LAMBDA
) -> list[int]:
    """Maximal Marginal Relevance: pick k items balancing score and novelty."""
    n = len(scores)
    if n == 0 or k <= 0:
        return []
    v = unit(vectors)
    sim = v @ v.T
    chosen: list[int] = []
    remaining = set(range(n))
    while remaining and len(chosen) < k:
        best, best_val = -1, -np.inf
        for i in remaining:
            redundancy = sim[i, chosen].max() if chosen else 0.0
            val = lam * scores[i] - (1 - lam) * redundancy
            if val > best_val:
                best, best_val = i, val
        chosen.append(best)
        remaining.remove(best)
    return chosen


# Find Sources ranking: the search matters most, then fit to the project.
SEARCH_WEIGHT, PROJECT_WEIGHT, SAVED_WEIGHT = 0.5, 0.35, 0.15


def blend_project_score(
    search: float | None, relevance: float | None, similarity: float | None
) -> float | None:
    """Weighted mean of the available scores (weights renormalised)."""
    parts = [
        (w, s)
        for w, s in ((SEARCH_WEIGHT, search), (PROJECT_WEIGHT, relevance), (SAVED_WEIGHT, similarity))
        if s is not None
    ]
    if not parts:
        return None
    return round(sum(w * s for w, s in parts) / sum(w for w, _ in parts), 4)


def to_percent(similarity: float | None) -> int | None:
    """Cosine similarity -> 0..100 for display."""
    if similarity is None or np.isnan(similarity):
        return None
    return int(round(max(0.0, min(1.0, float(similarity))) * 100))


def intra_list_diversity(vectors: np.ndarray) -> float:
    """Mean pairwise cosine distance of a result list (higher = more varied)."""
    v = unit(vectors)
    n = len(v)
    if n < 2:
        return 0.0
    sim = v @ v.T
    return float(1.0 - (sim.sum() - n) / (n * (n - 1)))
