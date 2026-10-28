"""Tune relevance-model weights on the golden set, validated with leave-one-out.

Compares raw vector similarity (baseline), the current weights, and the best grid
weights. Usage: npm run eval:tune -- --project-id <uuid> [--step 0.1] [--k 10] [--write]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import numpy as np

from app.core.database import AsyncSessionLocal
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.services.recommendation import features as feat
from app.services.recommendation.ranking import unit
from app.services.recommendation.service import project_text
from eval import weight_tuning as wt
from eval._wiring import build_voyage_client

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
RESULTS_DIR = Path(__file__).parent / "results"
FEATURES = list(feat.FEATURES)


def _weights_vec(weights: dict) -> np.ndarray:
    return np.array([float(weights.get(name, 0.0)) for name in FEATURES])


async def build_queries(project_id: UUID, items: list[dict]) -> tuple[list[dict], dict]:
    """One query per golden item; candidates are all papers saved to the project."""
    async with AsyncSessionLocal() as session:
        project = await ProjectRepository(session).get_by_id(project_id)
        if project is None:
            raise SystemExit(f"Project {project_id} not found")
        papers = await ProjectPaperRepository(session).list_papers_for_project(project_id)
        chunks = await ChunkRepository(session).get_for_papers([p.id for p in papers])

    papers = [p for p in papers if p.id in chunks and chunks[p.id].embedding is not None]
    if len(papers) < 2:
        raise SystemExit("Need at least two embedded saved papers in the project.")
    vecs = unit(np.stack([np.asarray(chunks[p.id].embedding, dtype=np.float64) for p in papers]))
    by_key = {(p.source, p.external_id): p.id for p in papers}

    voyage = build_voyage_client()
    embedded = await voyage.embed([project_text(project)] + [i["question"] for i in items], input_type="query")
    project_vec, question_vecs = unit(embedded[0])[0], unit(embedded[1:])

    # Similarity to the other saved papers (self excluded).
    pair = vecs @ vecs.T
    np.fill_diagonal(pair, -np.inf)
    saved_sim = pair.max(axis=1)
    semantic = vecs @ project_vec
    now_year = datetime.now().year
    base_context = [*(project.topics or []), *(project.keywords or [])]

    queries = []
    for item, qvec in zip(items, question_vecs):
        refs = item.get("relevant") or [{"source": item["source"], "external_id": item["external_id"]}]
        relevant = {by_key[(r["source"], r["external_id"])]: float(r.get("grade", 1))
                    for r in refs if (r["source"], r["external_id"]) in by_key}
        if not relevant:
            continue
        context = feat.tokens([*base_context, item["question"]])
        search = vecs @ qvec
        queries.append({
            "id": item["id"],
            "ids": [p.id for p in papers],
            "relevant": relevant,
            "features": [
                {
                    "search": feat.similarity_feature(float(search[i])),
                    "semantic": feat.similarity_feature(float(semantic[i])),
                    "saved": feat.similarity_feature(float(saved_sim[i])),
                    "recency": feat.recency_feature(p.year, now_year),
                    "citations": feat.citation_feature(p.citation_count),
                    "topic": feat.topic_feature(p.topics or [], context),
                }
                for i, p in enumerate(papers)
            ],
        })
    return queries, {"candidates": len(papers)}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project-id", type=UUID, default=None)
    parser.add_argument("--step", type=float, default=0.1, help="Grid step for weights (0.1 or 0.2).")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--write", action="store_true", help="Save tuned weights to weights.json.")
    args = parser.parse_args()

    data = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    items = data.get("items") or []
    project_id = args.project_id or (UUID(data["project_id"]) if data.get("project_id") else None)
    if not items or project_id is None:
        raise SystemExit("Golden set is empty or has no project_id; see README 'Retrieval evaluation'.")

    queries, info = await build_queries(project_id, items)
    if len(queries) < 2:
        raise SystemExit("Need at least two golden items whose papers are saved in the project.")
    matrices = [wt.to_matrix(q, FEATURES) for q in queries]
    k = args.k

    baseline_w = _weights_vec({"search": 1.0})  # raw vector similarity only
    current_w = _weights_vec(feat.load_weights())
    tuned_w, tuned_in_sample = wt.grid_search(queries, matrices, len(FEATURES), step=args.step, k=k)
    print(f"Tuning on {len(queries)} queries x {info['candidates']} candidates; running leave-one-out...")
    cv = wt.leave_one_out(queries, matrices, len(FEATURES), step=args.step, k=k)

    rows = {
        "baseline (vector similarity only)": wt.evaluate(queries, matrices, baseline_w, k),
        "current weights": wt.evaluate(queries, matrices, current_w, k),
        "tuned (in-sample)": tuned_in_sample,
        "tuned (leave-one-out)": cv,
    }
    print(f"\n{'':36} nDCG@{k}    MRR  Recall@{k}")
    for name, m in rows.items():
        print(f"{name:36} {m[f'ndcg@{k}']:.3f}  {m['mrr']:.3f}  {m[f'recall@{k}']:.3f}")
    tuned = {name: round(float(w), 4) for name, w in zip(FEATURES, tuned_w)}
    print("\nTuned weights:", ", ".join(f"{n}={w:.2f}" for n, w in tuned.items()))

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_id": str(project_id),
        "k": k,
        "step": args.step,
        "n_queries": len(queries),
        "n_candidates": info["candidates"],
        "metrics": rows,
        "weights": {
            "baseline": dict(zip(FEATURES, baseline_w.tolist())),
            "current": dict(zip(FEATURES, current_w.tolist())),
            "tuned": tuned,
        },
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"tuning-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {out}")

    if args.write:
        feat.save_weights(tuned, {"tuned_at": result["created_at"], "project_id": str(project_id),
                                  "n_queries": len(queries), "loo_cv": cv})
        print(f"Saved tuned weights to {feat.WEIGHTS_PATH} (restart the API to use them).")
    elif len(queries) < 8:
        print("Few queries: treat these weights as provisional before using --write.")


if __name__ == "__main__":
    asyncio.run(main())
