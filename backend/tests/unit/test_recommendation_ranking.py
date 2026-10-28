"""Recommendation ranking math."""

import numpy as np
import pytest

from app.services.recommendation import ranking as r


def test_centroid_and_unit() -> None:
    assert r.centroid([]) is None
    c = r.centroid([[2.0, 0.0], [0.0, 3.0]])
    assert np.allclose(c, [np.sqrt(0.5), np.sqrt(0.5)])
    assert np.allclose(np.linalg.norm(r.unit([[3.0, 4.0]]), axis=1), 1.0)


def test_score_candidates_uses_best_interest_and_saved() -> None:
    interests = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    candidates = np.array([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    saved = np.array([[0.0, 0.0, 1.0]])
    s = r.score_candidates(candidates, interests, saved)
    assert s["best_interest"][0] == 1
    assert s["interest"][0] == pytest.approx(1.0)
    assert s["saved"][1] == pytest.approx(1.0)
    assert s["score"][0] == pytest.approx(r.INTEREST_WEIGHT)
    assert s["score"][1] == pytest.approx(1 - r.INTEREST_WEIGHT)


def test_score_candidates_without_saved() -> None:
    s = r.score_candidates(np.eye(2), np.eye(2), None)
    assert np.isnan(s["saved"]).all()
    assert np.allclose(s["score"], s["interest"])


def test_mmr_prefers_diverse_items() -> None:
    # Two near-duplicates with the top scores, one distinct item slightly lower.
    vectors = np.array([[1.0, 0.0], [0.999, 0.01], [0.0, 1.0]])
    scores = np.array([0.9, 0.89, 0.8])
    assert r.mmr(vectors, scores, k=2) == [0, 2]
    assert r.mmr(vectors, scores, k=2, lam=1.0) == [0, 1]
    assert r.mmr(vectors, scores, k=0) == []


def test_to_percent_and_diversity() -> None:
    assert r.to_percent(0.456) == 46
    assert r.to_percent(1.7) == 100
    assert r.to_percent(None) is None
    assert r.to_percent(float("nan")) is None
    assert r.intra_list_diversity(np.eye(3)) == pytest.approx(1.0)
    assert r.intra_list_diversity(np.ones((3, 2))) == pytest.approx(0.0)


def test_blend_project_score_renormalises_missing_parts() -> None:
    assert r.blend_project_score(None, None, None) is None
    assert r.blend_project_score(None, 0.6, None) == pytest.approx(0.6)
    full = r.blend_project_score(1.0, 0.0, 0.0)
    assert full == pytest.approx(r.SEARCH_WEIGHT)
    no_search = r.blend_project_score(None, 1.0, 0.0)
    assert no_search == pytest.approx(r.PROJECT_WEIGHT / (r.PROJECT_WEIGHT + r.SAVED_WEIGHT))
