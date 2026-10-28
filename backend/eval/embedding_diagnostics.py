"""Embedding-space diagnostics for the Retrieval index.

Pure numpy functions (no DB / network), unit-tested in
tests/unit/test_embedding_diagnostics.py and driven by eval/diagnose_embeddings.py.

What they answer
----------------
- **Geometry**: are vectors unit-normalised? How anisotropic is the space (do all
  vectors crowd into a narrow cone, inflating every cosine similarity)? How many
  dimensions carry the variance (effective dimensionality)?
- **Hubness**: do a few chunks show up in almost everyone's nearest neighbours?
  Hubs get retrieved for unrelated queries and hurt precision.
- **Separation**: for golden questions, are similarities to relevant papers clearly
  above similarities to irrelevant ones (ROC AUC), and which distance threshold
  best splits them (used to tune ``retrieval_max_distance``)?
- **Projection**: a 2-D PCA layout for plotting papers / chunks.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def _as_matrix(vectors: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
    x = np.asarray(vectors, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] == 0:
        raise ValueError("expected a non-empty 2-D array of vectors")
    return x


def l2_normalize(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(norms == 0, 1.0, norms)


def _summary(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(values.mean()),
        "std": float(values.std()),
        "min": float(values.min()),
        "p50": float(np.percentile(values, 50)),
        "max": float(values.max()),
    }


def norm_stats(vectors) -> dict[str, float]:
    """Distribution of vector L2 norms (≈1.0 everywhere for normalised models)."""
    return _summary(np.linalg.norm(_as_matrix(vectors), axis=1))


def pairwise_cosine_sample(
    vectors, *, max_pairs: int = 20_000, seed: int = 0
) -> np.ndarray:
    """Cosine similarities for a random sample of distinct pairs (i < j)."""
    x = l2_normalize(_as_matrix(vectors))
    n = x.shape[0]
    if n < 2:
        return np.empty(0)
    total = n * (n - 1) // 2
    if total <= max_pairs:
        i, j = np.triu_indices(n, k=1)
    else:
        rng = np.random.default_rng(seed)
        i = rng.integers(0, n, size=max_pairs * 2)
        j = rng.integers(0, n, size=max_pairs * 2)
        keep = i != j
        i, j = i[keep][:max_pairs], j[keep][:max_pairs]
    return np.einsum("ij,ij->i", x[i], x[j])


def anisotropy(vectors, *, max_pairs: int = 20_000, seed: int = 0) -> dict[str, float]:
    """How much the unit vectors share a common direction.

    - ``mean_pairwise_cosine``: ~0 for an isotropic space; close to 1 when every
      vector points the same way (similarity scores then carry little signal).
    - ``mean_vector_norm``: length of the centroid of the unit vectors, another
      view of the same thing (0 = balanced, 1 = all identical).
    """
    x = l2_normalize(_as_matrix(vectors))
    sims = pairwise_cosine_sample(x, max_pairs=max_pairs, seed=seed)
    return {
        "mean_pairwise_cosine": float(sims.mean()) if sims.size else float("nan"),
        "std_pairwise_cosine": float(sims.std()) if sims.size else float("nan"),
        "mean_vector_norm": float(np.linalg.norm(x.mean(axis=0))),
    }


def pca(vectors, n_components: int = 2) -> dict[str, np.ndarray]:
    """PCA via SVD of mean-centred data.

    Returns ``projection`` (n x n_components), ``explained_variance_ratio`` for all
    components, and ``effective_dim`` (participation ratio of the eigenvalues:
    (sum λ)^2 / sum λ^2 — the number of "equally used" dimensions).
    """
    x = _as_matrix(vectors)
    centred = x - x.mean(axis=0)
    _, s, vt = np.linalg.svd(centred, full_matrices=False)
    eig = s**2
    total = eig.sum()
    ratio = eig / total if total > 0 else np.zeros_like(eig)
    k = min(n_components, vt.shape[0])
    return {
        "projection": centred @ vt[:k].T,
        "explained_variance_ratio": ratio,
        "effective_dim": float(total**2 / (eig**2).sum()) if total > 0 else 0.0,
    }


def hubness(vectors, *, k: int = 10) -> dict[str, float]:
    """k-occurrence statistics: N_k(x) = how many points list x among their k-NN.

    ``skewness`` > ~1 means a few hubs dominate neighbour lists; ``max_share`` is the
    fraction of points whose k-NN include the biggest hub (``top_hub_index``);
    ``antihub_share`` is the fraction never retrieved as anyone's neighbour.
    """
    x = l2_normalize(_as_matrix(vectors))
    n = x.shape[0]
    k = min(k, n - 1)
    if k < 1:
        return {"k": 0, "skewness": 0.0, "max_share": 0.0, "antihub_share": 1.0, "top_hub_index": None}
    sims = x @ x.T
    np.fill_diagonal(sims, -np.inf)
    neighbours = np.argpartition(-sims, kth=k - 1, axis=1)[:, :k]
    counts = np.bincount(neighbours.ravel(), minlength=n).astype(np.float64)
    std = counts.std()
    skew = float(((counts - counts.mean()) ** 3).mean() / std**3) if std > 0 else 0.0
    return {
        "k": k,
        "skewness": skew,
        "max_share": float(counts.max() / n),
        "antihub_share": float((counts == 0).mean()),
        "top_hub_index": int(counts.argmax()),
    }


def roc_auc(positive_scores: Sequence[float], negative_scores: Sequence[float]) -> float | None:
    """Probability a random relevant pair scores above a random irrelevant one
    (Mann–Whitney U; ties count half). None if either side is empty."""
    pos = np.asarray(positive_scores, dtype=np.float64)
    neg = np.asarray(negative_scores, dtype=np.float64)
    if pos.size == 0 or neg.size == 0:
        return None
    greater = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return float((greater + 0.5 * ties) / (pos.size * neg.size))


def threshold_sweep(
    positive_scores: Sequence[float],
    negative_scores: Sequence[float],
    thresholds: Sequence[float] | None = None,
) -> list[dict[str, float]]:
    """Precision / recall / F1 of the rule "similarity >= t means relevant".

    Cosine *distance* gate ``d <= D`` used by Ask is the same as ``similarity >= 1 - D``.
    """
    pos = np.asarray(positive_scores, dtype=np.float64)
    neg = np.asarray(negative_scores, dtype=np.float64)
    if thresholds is None:
        thresholds = np.round(np.arange(0.0, 1.0001, 0.05), 2)
    rows = []
    for t in thresholds:
        tp = float((pos >= t).sum())
        fp = float((neg >= t).sum())
        fn = float((pos < t).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "similarity_threshold": float(t),
                "distance_threshold": round(1.0 - float(t), 4),
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    return rows


def histogram(values: Sequence[float], *, bins: int = 20, lo: float = -0.2, hi: float = 1.0) -> dict:
    counts, edges = np.histogram(np.asarray(values, dtype=np.float64), bins=bins, range=(lo, hi))
    return {"counts": counts.tolist(), "edges": [round(float(e), 4) for e in edges]}


def query_separation(
    query_vectors, doc_vectors, relevance: Sequence[set[int]]
) -> dict:
    """Cosine similarities of each query to relevant vs irrelevant documents.

    ``relevance[q]`` is the set of row indices in ``doc_vectors`` relevant to query q.
    """
    q = l2_normalize(_as_matrix(query_vectors))
    d = l2_normalize(_as_matrix(doc_vectors))
    if len(relevance) != q.shape[0]:
        raise ValueError("relevance must have one entry per query")
    sims = q @ d.T
    pos: list[float] = []
    neg: list[float] = []
    margins: list[float] = []
    for qi, rel in enumerate(relevance):
        row = sims[qi]
        mask = np.zeros(row.shape[0], dtype=bool)
        mask[list(rel)] = True
        pos.extend(row[mask].tolist())
        neg.extend(row[~mask].tolist())
        if mask.any() and (~mask).any():
            margins.append(float(row[mask].max() - row[~mask].max()))
    return {
        "relevant_similarities": pos,
        "irrelevant_similarities": neg,
        "roc_auc": roc_auc(pos, neg),
        # >0: the best relevant doc beats every irrelevant one for that query.
        "mean_top_margin": float(np.mean(margins)) if margins else None,
        "share_positive_margin": float(np.mean([m > 0 for m in margins])) if margins else None,
    }
