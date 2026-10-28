"""IR metrics: precision/recall/F1/hit/nDCG@k, MRR, MAP.

``ranked`` is a best-first list of ids; ``relevant`` is a set of ids or an
``{id: gain}`` map for graded nDCG.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterable, Mapping, Sequence
from statistics import mean

Relevance = Mapping[Hashable, float] | Iterable[Hashable]


def _gains(relevant: Relevance) -> dict[Hashable, float]:
    if isinstance(relevant, Mapping):
        return {doc: float(g) for doc, g in relevant.items() if float(g) > 0}
    return {doc: 1.0 for doc in relevant}


def _top(ranked: Sequence[Hashable], k: int | None) -> Sequence[Hashable]:
    if k is not None and k < 1:
        raise ValueError("k must be >= 1")
    return ranked if k is None else ranked[:k]


def precision_at_k(ranked: Sequence[Hashable], relevant: Relevance, k: int) -> float:
    """Share of the top-k slots filled by relevant documents (denominator is k)."""
    gains = _gains(relevant)
    top = _top(ranked, k)
    return sum(1 for doc in top if doc in gains) / k


def recall_at_k(ranked: Sequence[Hashable], relevant: Relevance, k: int | None) -> float:
    """Share of all relevant documents that appear in the top k."""
    gains = _gains(relevant)
    if not gains:
        return 0.0
    top = _top(ranked, k)
    return sum(1 for doc in top if doc in gains) / len(gains)


def hit_at_k(ranked: Sequence[Hashable], relevant: Relevance, k: int | None) -> float:
    """1.0 if any relevant document is in the top k, else 0.0."""
    gains = _gains(relevant)
    return 1.0 if any(doc in gains for doc in _top(ranked, k)) else 0.0


def f1_at_k(ranked: Sequence[Hashable], relevant: Relevance, k: int) -> float:
    p = precision_at_k(ranked, relevant, k)
    r = recall_at_k(ranked, relevant, k)
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def first_relevant_rank(ranked: Sequence[Hashable], relevant: Relevance) -> int | None:
    """1-based rank of the first relevant document, or None if none retrieved."""
    gains = _gains(relevant)
    for i, doc in enumerate(ranked, start=1):
        if doc in gains:
            return i
    return None


def reciprocal_rank(ranked: Sequence[Hashable], relevant: Relevance, k: int | None = None) -> float:
    rank = first_relevant_rank(_top(ranked, k), relevant)
    return 0.0 if rank is None else 1.0 / rank


def average_precision(ranked: Sequence[Hashable], relevant: Relevance, k: int | None = None) -> float:
    """Mean of precision@i over the ranks i where a relevant doc appears,
    normalised by the total number of relevant docs (so misses count as 0)."""
    gains = _gains(relevant)
    if not gains:
        return 0.0
    hits = 0
    total = 0.0
    for i, doc in enumerate(_top(ranked, k), start=1):
        if doc in gains:
            hits += 1
            total += hits / i
    return total / len(gains)


def dcg_at_k(ranked: Sequence[Hashable], relevant: Relevance, k: int | None) -> float:
    gains = _gains(relevant)
    return sum(
        (2 ** gains.get(doc, 0.0) - 1) / math.log2(i + 1)
        for i, doc in enumerate(_top(ranked, k), start=1)
    )


def ndcg_at_k(ranked: Sequence[Hashable], relevant: Relevance, k: int | None) -> float:
    """Normalised DCG with exponential gain; 1.0 = ideal ordering."""
    gains = _gains(relevant)
    if not gains:
        return 0.0
    ideal = sorted(gains, key=gains.__getitem__, reverse=True)
    ideal_dcg = dcg_at_k(ideal, gains, k)
    return 0.0 if ideal_dcg == 0 else dcg_at_k(ranked, gains, k) / ideal_dcg


def evaluate_query(
    ranked: Sequence[Hashable], relevant: Relevance, ks: Sequence[int] = (1, 3, 5, 10)
) -> dict[str, float | int | None]:
    """All per-query metrics at each cutoff, as a flat dict (e.g. ``precision@5``)."""
    row: dict[str, float | int | None] = {
        "rr": reciprocal_rank(ranked, relevant),
        "ap": average_precision(ranked, relevant),
        "first_relevant_rank": first_relevant_rank(ranked, relevant),
        "num_relevant": len(_gains(relevant)),
        "num_retrieved": len(ranked),
    }
    for k in ks:
        row[f"precision@{k}"] = precision_at_k(ranked, relevant, k)
        row[f"recall@{k}"] = recall_at_k(ranked, relevant, k)
        row[f"f1@{k}"] = f1_at_k(ranked, relevant, k)
        row[f"hit@{k}"] = hit_at_k(ranked, relevant, k)
        row[f"ndcg@{k}"] = ndcg_at_k(ranked, relevant, k)
    return row


def aggregate(rows: Sequence[Mapping[str, float | int | None]]) -> dict[str, float]:
    """Macro-average each numeric metric across queries.

    ``rr`` becomes MRR and ``ap`` becomes MAP. Count/rank columns are skipped.
    """
    skip = {"first_relevant_rank", "num_relevant", "num_retrieved"}
    if not rows:
        return {}
    keys = [k for k in rows[0] if k not in skip]
    out = {key: mean(float(r[key]) for r in rows) for key in keys}
    out["mrr"] = out.pop("rr")
    out["map"] = out.pop("ap")
    return out


def precision_recall_curve(
    rows_ranked: Sequence[tuple[Sequence[Hashable], Relevance]], max_k: int
) -> list[dict[str, float]]:
    """Macro-averaged precision and recall at every cutoff 1..max_k."""
    curve = []
    for k in range(1, max_k + 1):
        curve.append(
            {
                "k": k,
                "precision": mean(precision_at_k(r, rel, k) for r, rel in rows_ranked),
                "recall": mean(recall_at_k(r, rel, k) for r, rel in rows_ranked),
            }
        )
    return curve
