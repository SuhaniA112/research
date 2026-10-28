"""Retrieval metrics used by eval/run_eval.py, checked against hand-computed values."""

import math

import pytest

from eval import metrics as m

RANKED = ["a", "b", "c", "d", "e"]
RELEVANT = {"b", "d", "z"}  # z is never retrieved


def test_precision_and_recall_at_k() -> None:
    assert m.precision_at_k(RANKED, RELEVANT, 1) == 0.0
    assert m.precision_at_k(RANKED, RELEVANT, 2) == 0.5
    assert m.precision_at_k(RANKED, RELEVANT, 5) == pytest.approx(2 / 5)
    # Denominator stays k even when fewer than k results came back.
    assert m.precision_at_k(["b"], RELEVANT, 5) == pytest.approx(1 / 5)

    assert m.recall_at_k(RANKED, RELEVANT, 2) == pytest.approx(1 / 3)
    assert m.recall_at_k(RANKED, RELEVANT, 5) == pytest.approx(2 / 3)
    assert m.recall_at_k(RANKED, set(), 5) == 0.0


def test_f1_and_hit() -> None:
    p, r = 2 / 5, 2 / 3
    assert m.f1_at_k(RANKED, RELEVANT, 5) == pytest.approx(2 * p * r / (p + r))
    assert m.hit_at_k(RANKED, RELEVANT, 1) == 0.0
    assert m.hit_at_k(RANKED, RELEVANT, 2) == 1.0


def test_reciprocal_rank_and_average_precision() -> None:
    assert m.first_relevant_rank(RANKED, RELEVANT) == 2
    assert m.reciprocal_rank(RANKED, RELEVANT) == 0.5
    assert m.reciprocal_rank(RANKED, RELEVANT, k=1) == 0.0
    assert m.reciprocal_rank(RANKED, {"q"}) == 0.0
    # Relevant at ranks 2 and 4: (1/2 + 2/4) / 3 relevant docs.
    assert m.average_precision(RANKED, RELEVANT) == pytest.approx((0.5 + 0.5) / 3)


def test_ndcg_binary_and_graded() -> None:
    expected_dcg = 1 / math.log2(3) + 1 / math.log2(5)
    ideal_dcg = 1 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)
    assert m.ndcg_at_k(RANKED, RELEVANT, 5) == pytest.approx(expected_dcg / ideal_dcg)
    assert m.ndcg_at_k(["b", "d"], {"b", "d"}, 2) == pytest.approx(1.0)

    graded = {"a": 1, "b": 3}
    # Wrong order scores below 1, right order scores exactly 1.
    assert m.ndcg_at_k(["a", "b"], graded, 2) < 1.0
    assert m.ndcg_at_k(["b", "a"], graded, 2) == pytest.approx(1.0)


def test_invalid_k_rejected() -> None:
    with pytest.raises(ValueError):
        m.precision_at_k(RANKED, RELEVANT, 0)


def test_evaluate_and_aggregate() -> None:
    rows = [
        m.evaluate_query(["x", "y"], {"x"}, ks=(1, 2)),
        m.evaluate_query(["y", "x"], {"x"}, ks=(1, 2)),
    ]
    assert rows[0]["first_relevant_rank"] == 1
    agg = m.aggregate(rows)
    assert agg["mrr"] == pytest.approx((1 + 0.5) / 2)
    assert agg["hit@1"] == 0.5
    assert agg["hit@2"] == 1.0
    assert agg["precision@1"] == 0.5
    assert "first_relevant_rank" not in agg
    assert m.aggregate([]) == {}


def test_precision_recall_curve() -> None:
    curve = m.precision_recall_curve([(RANKED, RELEVANT)], max_k=3)
    assert [p["k"] for p in curve] == [1, 2, 3]
    assert curve[1]["precision"] == 0.5
    assert curve[2]["recall"] == pytest.approx(1 / 3)
