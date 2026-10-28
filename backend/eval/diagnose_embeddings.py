"""Embedding diagnostics for a project's Retrieval index (or the whole database).

Pulls stored Chunk embeddings from Postgres, then reports geometry (norms,
anisotropy, effective dimensionality), hubness, a 2-D PCA layout of papers and,
when golden_set.json has items and a Voyage key is configured, how well
query→paper similarity separates relevant from irrelevant papers (ROC AUC and a
distance-threshold sweep for tuning ``retrieval_max_distance``).

Usage:
    npm run eval:diagnostics -- --project-id <uuid>
    python -m eval.diagnose_embeddings --all --max-chunks 5000

Render charts with ``npm run eval:report`` (eval/report.py).
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import numpy as np
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.chunk import Chunk
from app.models.paper import Paper
from app.models.project_paper import ProjectPaper
from eval import embedding_diagnostics as diag
from eval._wiring import build_voyage_client

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
RESULTS_DIR = Path(__file__).parent / "results"


async def load_chunks(project_id: UUID | None, max_chunks: int, seed: int):
    """Return (embeddings matrix, paper_ids per row, {paper_id: (title, topics, source)})."""
    async with AsyncSessionLocal() as session:
        stmt = select(Chunk.paper_id, Chunk.embedding).join(Paper, Chunk.paper_id == Paper.id)
        if project_id is not None:
            stmt = stmt.join(ProjectPaper, ProjectPaper.paper_id == Paper.id).where(
                ProjectPaper.project_id == project_id
            )
        rows = (await session.execute(stmt)).all()

        paper_ids = {pid for pid, _ in rows}
        papers = {}
        if paper_ids:
            result = await session.execute(
                select(Paper.id, Paper.title, Paper.topics, Paper.source, Paper.external_id).where(
                    Paper.id.in_(paper_ids)
                )
            )
            papers = {
                pid: {"title": title, "topics": list(topics or []), "source": source, "external_id": ext}
                for pid, title, topics, source, ext in result.all()
            }

    if len(rows) > max_chunks:
        rng = np.random.default_rng(seed)
        keep = rng.choice(len(rows), size=max_chunks, replace=False)
        rows = [rows[i] for i in sorted(keep)]

    matrix = np.asarray([np.asarray(emb, dtype=np.float64) for _, emb in rows])
    return matrix, [pid for pid, _ in rows], papers


def paper_centroids(matrix: np.ndarray, row_paper_ids: list[UUID]):
    order = list(dict.fromkeys(row_paper_ids))
    index = {pid: i for i, pid in enumerate(order)}
    sums = np.zeros((len(order), matrix.shape[1]))
    counts = np.zeros(len(order))
    for row, pid in zip(diag.l2_normalize(matrix), row_paper_ids):
        sums[index[pid]] += row
        counts[index[pid]] += 1
    return order, sums / counts[:, None], counts


async def golden_separation(matrix, row_paper_ids, papers, project_id):
    """Query→paper similarity (best chunk per paper, like Retrieval) for golden items."""
    if not GOLDEN_SET_PATH.exists() or not settings.voyage_api_key:
        return None
    data = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    items = data.get("items") or []
    if project_id is not None and data.get("project_id") and data["project_id"] != str(project_id):
        print("  golden_set.json is for a different project; skipping separation analysis.")
        return None
    if not items:
        return None

    key_to_pid = {(p["source"], p["external_id"]): pid for pid, p in papers.items()}
    order = list(dict.fromkeys(row_paper_ids))
    col = {pid: i for i, pid in enumerate(order)}
    group = np.array([col[pid] for pid in row_paper_ids])

    voyage = build_voyage_client()
    queries = np.asarray(
        await voyage.embed([i["question"] for i in items], input_type="query"), dtype=np.float64
    )
    chunk_sims = diag.l2_normalize(queries) @ diag.l2_normalize(matrix).T

    positives, negatives, margins = [], [], []
    for qi, item in enumerate(items):
        refs = item.get("relevant") or [{"source": item["source"], "external_id": item["external_id"]}]
        relevant_cols = {col[key_to_pid[(r["source"], r["external_id"])]]
                         for r in refs if (r["source"], r["external_id"]) in key_to_pid
                         and key_to_pid[(r["source"], r["external_id"])] in col}
        if not relevant_cols:
            continue
        paper_sims = np.full(len(order), -np.inf)
        np.maximum.at(paper_sims, group, chunk_sims[qi])
        mask = np.zeros(len(order), dtype=bool)
        mask[list(relevant_cols)] = True
        positives.extend(paper_sims[mask].tolist())
        negatives.extend(paper_sims[~mask].tolist())
        if (~mask).any():
            margins.append(float(paper_sims[mask].max() - paper_sims[~mask].max()))

    if not positives:
        return None
    return {
        "num_queries": len(margins) or len(items),
        "roc_auc": diag.roc_auc(positives, negatives),
        "mean_top_margin": float(np.mean(margins)) if margins else None,
        "share_positive_margin": float(np.mean([m > 0 for m in margins])) if margins else None,
        "relevant_hist": diag.histogram(positives),
        "irrelevant_hist": diag.histogram(negatives),
        "threshold_sweep": diag.threshold_sweep(positives, negatives),
        "current_distance_gate": settings.retrieval_max_distance,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--project-id", type=UUID)
    scope.add_argument("--all", action="store_true", help="Diagnose every stored chunk.")
    parser.add_argument("--max-chunks", type=int, default=3000, help="Random sample cap (pairwise steps are O(n^2)).")
    parser.add_argument("--hub-k", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    project_id = None if args.all else args.project_id
    matrix, row_paper_ids, papers = await load_chunks(project_id, args.max_chunks, args.seed)
    if matrix.size == 0:
        print("No embedded chunks found. Save papers to the project (with VOYAGE_API_KEY set) first.")
        return
    print(f"Loaded {matrix.shape[0]} chunks x {matrix.shape[1]} dims from {len(papers)} papers")

    order, centroids, counts = paper_centroids(matrix, row_paper_ids)
    chunk_pca = diag.pca(matrix, n_components=2)
    paper_pca = diag.pca(centroids, n_components=2) if len(order) >= 2 else None

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_id": str(project_id) if project_id else None,
        "embedding_model": settings.voyage_embedding_model,
        "num_chunks": int(matrix.shape[0]),
        "num_papers": len(order),
        "dimension": int(matrix.shape[1]),
        "norms": diag.norm_stats(matrix),
        "anisotropy": diag.anisotropy(matrix, seed=args.seed),
        "pairwise_cosine_hist": diag.histogram(diag.pairwise_cosine_sample(matrix, seed=args.seed)),
        "effective_dim": chunk_pca["effective_dim"],
        "explained_variance_top10": chunk_pca["explained_variance_ratio"][:10].tolist(),
        "hubness": diag.hubness(matrix, k=args.hub_k),
        "chunks_per_paper": diag.norm_stats(counts[:, None]) if len(counts) else None,
        "paper_projection": [
            {
                "paper_id": str(pid),
                "title": papers.get(pid, {}).get("title", str(pid)),
                "topic": (papers.get(pid, {}).get("topics") or ["(no topic)"])[0],
                "x": float(paper_pca["projection"][i, 0]),
                "y": float(paper_pca["projection"][i, 1]),
                "chunks": int(counts[i]),
            }
            for i, pid in enumerate(order)
        ]
        if paper_pca is not None
        else [],
        "golden_separation": await golden_separation(matrix, row_paper_ids, papers, project_id),
    }
    hub_idx = report["hubness"].get("top_hub_index")
    if hub_idx is not None:
        hub_pid = row_paper_ids[hub_idx]
        report["hubness"]["top_hub_paper"] = papers.get(hub_pid, {}).get("title", str(hub_pid))

    a = report["anisotropy"]
    print(f"Norms: mean {report['norms']['mean']:.3f} (min {report['norms']['min']:.3f}, max {report['norms']['max']:.3f})")
    print(f"Anisotropy: mean pairwise cosine {a['mean_pairwise_cosine']:.3f}, centroid norm {a['mean_vector_norm']:.3f}")
    print(f"Effective dimensionality: {report['effective_dim']:.1f} of {report['dimension']}")
    h = report["hubness"]
    print(f"Hubness (k={h['k']}): skew {h['skewness']:.2f}, top hub in {h['max_share']:.0%} of neighbour lists")
    sep = report["golden_separation"]
    if sep:
        best = max(sep["threshold_sweep"], key=lambda r: r["f1"])
        print(
            f"Golden separation: ROC AUC {sep['roc_auc']:.3f}; best F1 {best['f1']:.2f} at distance "
            f"<= {best['distance_threshold']} (current gate {sep['current_distance_gate']})"
        )

    out = args.out or RESULTS_DIR / f"diagnostics-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
