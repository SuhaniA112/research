"""Embedding diagnostics on synthetic vectors with known geometry."""

import numpy as np
import pytest

from eval import embedding_diagnostics as d


def test_norm_stats_and_normalize() -> None:
    x = np.array([[3.0, 4.0], [0.0, 2.0]])
    stats = d.norm_stats(x)
    assert stats["max"] == pytest.approx(5.0)
    assert stats["min"] == pytest.approx(2.0)
    assert np.allclose(np.linalg.norm(d.l2_normalize(x), axis=1), 1.0)


def test_anisotropy_distinguishes_cone_from_isotropic() -> None:
    rng = np.random.default_rng(0)
    isotropic = rng.normal(size=(400, 32))
    cone = isotropic * 0.1 + np.ones(32)  # everything near one direction
    iso = d.anisotropy(isotropic)
    narrow = d.anisotropy(cone)
    assert abs(iso["mean_pairwise_cosine"]) < 0.05
    assert narrow["mean_pairwise_cosine"] > 0.9
    assert narrow["mean_vector_norm"] > iso["mean_vector_norm"]


def test_pairwise_sample_is_exact_for_small_inputs() -> None:
    x = np.eye(3)
    sims = d.pairwise_cosine_sample(x)
    assert sims.shape == (3,)
    assert np.allclose(sims, 0.0)


def test_pca_finds_dominant_axis_and_effective_dim() -> None:
    rng = np.random.default_rng(1)
    x = np.zeros((200, 5))
    x[:, 0] = rng.normal(scale=10, size=200)
    x[:, 1] = rng.normal(scale=0.1, size=200)
    result = d.pca(x, n_components=2)
    assert result["projection"].shape == (200, 2)
    assert result["explained_variance_ratio"][0] > 0.99
    assert 1.0 <= result["effective_dim"] < 1.1


def test_hubness_flags_a_hub() -> None:
    rng = np.random.default_rng(2)
    # Points scattered around a shared direction; the hub *is* that direction,
    # so it is closer to every point than the points are to each other.
    x = np.ones(16) + rng.normal(size=(100, 16))
    x[0] = np.ones(16)
    result = d.hubness(x, k=5)
    assert result["top_hub_index"] == 0
    assert result["max_share"] > 0.3
    assert result["skewness"] > 1


def test_roc_auc_and_threshold_sweep() -> None:
    assert d.roc_auc([0.9, 0.8], [0.1, 0.2]) == 1.0
    assert d.roc_auc([0.1], [0.9]) == 0.0
    assert d.roc_auc([0.5], [0.5]) == 0.5
    assert d.roc_auc([], [0.1]) is None

    rows = d.threshold_sweep([0.8, 0.6], [0.5, 0.2], thresholds=[0.55])
    assert rows[0]["precision"] == 1.0
    assert rows[0]["recall"] == 1.0
    assert rows[0]["distance_threshold"] == pytest.approx(0.45)


def test_query_separation() -> None:
    docs = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]])
    queries = np.array([[1.0, 0.1]])
    result = d.query_separation(queries, docs, [{0}])
    assert len(result["relevant_similarities"]) == 1
    assert len(result["irrelevant_similarities"]) == 2
    assert result["roc_auc"] == 1.0
    assert result["share_positive_margin"] == 1.0

    with pytest.raises(ValueError):
        d.query_separation(queries, docs, [{0}, {1}])


def test_histogram_bins() -> None:
    h = d.histogram([0.0, 0.5, 0.99], bins=2, lo=0.0, hi=1.0)
    assert h["counts"] == [1, 2]
    assert h["edges"] == [0.0, 0.5, 1.0]
