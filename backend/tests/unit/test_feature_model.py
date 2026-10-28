"""Weighted relevance features and weight tuning."""

import numpy as np
import pytest

from app.services.recommendation import features as f
from eval import weight_tuning as wt


def test_feature_functions() -> None:
    assert f.similarity_feature(1.4) == 1.0
    assert f.similarity_feature(None) is None
    assert f.recency_feature(2026, 2026) == 1.0
    assert f.recency_feature(2021, 2026) == pytest.approx(0.5)
    assert f.recency_feature(None, 2026) is None
    assert f.citation_feature(0) == 0.0
    assert f.citation_feature(10_000) == 1.0
    assert f.citation_feature(None) is None
    ctx = f.tokens(["medical image segmentation"])
    assert f.topic_feature(["Image Segmentation"], ctx) == pytest.approx(2 / 3)
    assert f.topic_feature([], ctx) is None
    assert f.topic_feature(["x"], set()) is None


def test_composite_renormalises_over_known_features() -> None:
    w = {"semantic": 0.6, "citations": 0.4}
    assert f.composite({"semantic": 0.5, "citations": None}, w) == pytest.approx(0.5)
    assert f.composite({"semantic": 1.0, "citations": 0.0}, w) == pytest.approx(0.6)
    assert f.composite({"semantic": None}, w) is None


def test_load_weights_merges_file_and_ignores_junk(tmp_path) -> None:
    path = tmp_path / "w.json"
    assert f.load_weights(path) == f.DEFAULT_WEIGHTS
    f.save_weights({"search": 1.0}, {"note": "t"}, path)
    loaded = f.load_weights(path)
    assert loaded["search"] == 1.0 and loaded["semantic"] == 0.0
    path.write_text("{not json", encoding="utf-8")
    assert f.load_weights(path) == f.DEFAULT_WEIGHTS


def test_simplex_grid_sums_to_one() -> None:
    grid = list(wt.simplex_grid(3, 0.5))
    assert len(grid) == 6
    assert all(np.isclose(w.sum(), 1.0) for w in grid)


def _queries():
    # Feature 0 = raw similarity (misleading), feature 1 = signal that finds the target.
    return [
        {"ids": ["a", "b", "c"], "relevant": {"c"},
         "features": [{"sim": 0.9, "sig": 0.0}, {"sim": 0.8, "sig": 0.1}, {"sim": 0.7, "sig": 1.0}]},
        {"ids": ["d", "e"], "relevant": {"e"},
         "features": [{"sim": 0.9, "sig": 0.0}, {"sim": 0.6, "sig": None}]},
    ]


def test_composite_scores_and_evaluate() -> None:
    qs = _queries()
    mats = [wt.to_matrix(q, ["sim", "sig"]) for q in qs]
    assert np.isnan(mats[1][1, 1])
    only_sim = wt.evaluate(qs, mats, np.array([1.0, 0.0]), k=3)
    assert only_sim["mrr"] == pytest.approx((1 / 3 + 1 / 2) / 2)
    empty = wt.composite_scores(np.array([[np.nan]]), np.array([1.0]))
    assert empty[0] == -np.inf


def test_grid_search_finds_the_useful_signal_and_loo_runs() -> None:
    qs = _queries()
    mats = [wt.to_matrix(q, ["sim", "sig"]) for q in qs]
    w, best = wt.grid_search(qs, mats, 2, step=0.1, k=3)
    assert w[1] > 0
    assert best["ndcg@3"] > wt.evaluate(qs, mats, np.array([1.0, 0.0]), k=3)["ndcg@3"]
    cv = wt.leave_one_out(qs, mats, 2, step=0.5, k=3)
    assert set(cv) == {"ndcg@3", "mrr", "recall@3"}
    assert wt.leave_one_out(qs[:1], mats[:1], 2) == {}
