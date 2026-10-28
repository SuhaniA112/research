"""Tune feature weights against golden-set relevance judgments (pure numpy).

Each query is a dict: ``ids`` (candidate paper ids), ``features`` (one dict of
feature -> value|None per candidate) and ``relevant`` ({id: gain}). Weights are
searched on a simplex grid; leave-one-out cross-validation gives an honest score.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from itertools import combinations

import numpy as np

from eval import metrics


def to_matrix(query: dict, features: Sequence[str]) -> np.ndarray:
    """Candidates x features, NaN where a feature is unknown."""
    return np.array(
        [[np.nan if f.get(name) is None else float(f[name]) for name in features] for f in query["features"]],
        dtype=np.float64,
    )


def composite_scores(matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Weighted mean over known features per row; -inf when nothing is known."""
    known = ~np.isnan(matrix)
    w = np.where(known, weights[None, :], 0.0)
    den = w.sum(axis=1)
    num = np.nansum(matrix * w, axis=1)
    out = np.full(len(matrix), -np.inf)
    np.divide(num, den, out=out, where=den > 0)
    return out


def rank_ids(query: dict, matrix: np.ndarray, weights: np.ndarray) -> list:
    order = np.argsort(-composite_scores(matrix, weights), kind="stable")
    return [query["ids"][i] for i in order]


def evaluate(queries: Sequence[dict], matrices: Sequence[np.ndarray], weights: np.ndarray, k: int = 10) -> dict:
    ndcg, rr, recall = [], [], []
    for q, m in zip(queries, matrices):
        ranked = rank_ids(q, m, weights)
        ndcg.append(metrics.ndcg_at_k(ranked, q["relevant"], k))
        rr.append(metrics.reciprocal_rank(ranked, q["relevant"]))
        recall.append(metrics.recall_at_k(ranked, q["relevant"], k))
    return {f"ndcg@{k}": float(np.mean(ndcg)), "mrr": float(np.mean(rr)), f"recall@{k}": float(np.mean(recall))}


def simplex_grid(n: int, step: float) -> Iterator[np.ndarray]:
    """All weight vectors of length n with entries in multiples of step summing to 1."""
    units = round(1 / step)
    for bars in combinations(range(units + n - 1), n - 1):
        parts = np.diff((-1, *bars, units + n - 1)) - 1
        yield parts / units


def grid_search(
    queries: Sequence[dict],
    matrices: Sequence[np.ndarray],
    n_features: int,
    *,
    step: float = 0.1,
    k: int = 10,
    objective: str | None = None,
) -> tuple[np.ndarray, dict]:
    """Best weights by the objective (default nDCG@k); ties keep the earlier, simpler vector."""
    key = objective or f"ndcg@{k}"
    best_w, best = None, None
    for w in simplex_grid(n_features, step):
        res = evaluate(queries, matrices, w, k)
        if best is None or res[key] > best[key] + 1e-12:
            best_w, best = w, res
    return best_w, best


def leave_one_out(
    queries: Sequence[dict],
    matrices: Sequence[np.ndarray],
    n_features: int,
    *,
    step: float = 0.1,
    k: int = 10,
) -> dict:
    """Tune on all-but-one query, score the held-out one; mean over folds."""
    if len(queries) < 2:
        return {}
    held = []
    for i in range(len(queries)):
        train_q = [q for j, q in enumerate(queries) if j != i]
        train_m = [m for j, m in enumerate(matrices) if j != i]
        w, _ = grid_search(train_q, train_m, n_features, step=step, k=k)
        held.append(evaluate([queries[i]], [matrices[i]], w, k))
    return {name: float(np.mean([h[name] for h in held])) for name in held[0]}
