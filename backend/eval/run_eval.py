"""Score Retrieval (ranking metrics) and generation against golden_set.json.

Usage: npm run eval -- --project-id <uuid> [--k 1 3 5 10] [--skip-generation]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from eval import metrics
from eval._wiring import (
    build_ask_service,
    build_chunk_repo,
    build_paper_repo,
    build_voyage_client,
)

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
RESULTS_DIR = Path(__file__).parent / "results"

DEFAULT_KS = (1, 3, 5, 10)
# Chunks fetched per wanted paper, so collapsing chunks to papers still fills k slots.
CHUNKS_PER_PAPER = 8
# Cosine distance spans [0, 2]; ranking metrics look at the full ordering, ungated.
UNGATED_MAX_DISTANCE = 2.0


def load_golden_set() -> dict:
    with GOLDEN_SET_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def relevant_refs(item: dict) -> list[dict]:
    """Normalise a golden item's relevance judgments to [{source, external_id, grade}]."""
    if item.get("relevant"):
        return [
            {
                "source": ref["source"],
                "external_id": ref["external_id"],
                "grade": float(ref.get("grade", 1)),
            }
            for ref in item["relevant"]
        ]
    return [{"source": item["source"], "external_id": item["external_id"], "grade": 1.0}]


def collapse_to_papers(hits: list[tuple[Any, float]]) -> list[tuple[UUID, float]]:
    """Ranked (chunk, distance) hits -> ranked (paper_id, best distance), deduped."""
    best: dict[UUID, float] = {}
    order: list[UUID] = []
    for chunk, distance in hits:
        pid = chunk.paper_id
        if pid not in best:
            order.append(pid)
            best[pid] = float(distance)
        else:
            best[pid] = min(best[pid], float(distance))
    order.sort(key=lambda pid: best[pid])
    return [(pid, best[pid]) for pid in order]


async def score_generation(
    session, project_id: UUID, user_id: UUID, item: dict, relevant_ids: set[UUID], gated_hit: bool
) -> dict:
    ask_service = build_ask_service(session)
    response, retrieved_chunk_ids = await ask_service.ask(
        project_id, item["question"], user_id=user_id, debug=True
    )
    citation_paper_ids = {c.paper_id for c in response.citations}
    return {
        "status": response.status,
        "citations_within_retrieved": all(
            c.chunk_id in retrieved_chunk_ids for c in response.citations
        ),
        "false_refusal": response.status == "no_relevant_sources" and gated_hit,
        "possibly_hallucinated": (
            response.status == "answered"
            and bool(relevant_ids)
            and not (relevant_ids & citation_paper_ids)
        ),
    }


async def resolve_user_id(project_id: UUID, data: dict, cli_user_id: UUID | None) -> UUID | None:
    if cli_user_id is not None:
        return cli_user_id
    if data.get("user_id"):
        return UUID(data["user_id"])
    async with AsyncSessionLocal() as session:
        from app.repositories.project_repo import ProjectRepository

        project = await ProjectRepository(session).get_by_id(project_id)
        return project.user_id if project is not None else None


def print_summary(summary: dict, ks: tuple[int, ...], n: int, generation: dict | None) -> None:
    print("\n--- Retrieval (ranked papers, n=%d) ---" % n)
    header = f"{'k':>4} {'P@k':>7} {'R@k':>7} {'F1@k':>7} {'Hit@k':>7} {'nDCG@k':>7}"
    print(header)
    for k in ks:
        print(
            f"{k:>4} {summary[f'precision@{k}']:>7.3f} {summary[f'recall@{k}']:>7.3f} "
            f"{summary[f'f1@{k}']:>7.3f} {summary[f'hit@{k}']:>7.3f} {summary[f'ndcg@{k}']:>7.3f}"
        )
    print(f"MRR {summary['mrr']:.3f}   MAP {summary['map']:.3f}")
    print(
        f"Gated hit (distance <= {settings.retrieval_max_distance}, top {settings.retrieval_top_k} chunks): "
        f"{summary['gated_hit']:.0%}"
    )
    if generation:
        print("\n--- Generation ---")
        print(f"Citation validity: {generation['citation_validity']:.0%}")
        print(f"False refusals: {generation['false_refusals']}")
        print(f"Possibly hallucinated: {generation['possibly_hallucinated']}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--project-id", type=UUID, default=None)
    parser.add_argument(
        "--user-id",
        type=UUID,
        default=None,
        help="Project owner user id (required for Ask ownership checks)",
    )
    parser.add_argument("--k", type=int, nargs="+", default=list(DEFAULT_KS))
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Score retrieval only (no OpenRouter calls).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Where to write the JSON results (default: eval/results/run-<timestamp>.json).",
    )
    args = parser.parse_args()
    ks = tuple(sorted(set(args.k)))

    data = load_golden_set()
    items = data["items"]
    if not items:
        print(f"No golden set items found in {GOLDEN_SET_PATH}. Run generate_golden_set.py first.")
        return

    project_id = args.project_id or (UUID(data["project_id"]) if data["project_id"] else None)
    if project_id is None:
        print("No --project-id given and none stored in golden_set.json.")
        return

    user_id = None
    if not args.skip_generation:
        user_id = await resolve_user_id(project_id, data, args.user_id)
        if user_id is None:
            print("No --user-id given and project has no owner; use --skip-generation or pass --user-id.")
            return

    unreviewed = [i["id"] for i in items if not i.get("reviewed")]
    if unreviewed:
        print(f"WARNING: {len(unreviewed)} unreviewed item(s) in golden set: {unreviewed}")
        print("These are synthetic and not yet hand-verified; treat these numbers as provisional.\n")

    voyage = build_voyage_client()
    query_embeddings = await voyage.embed([i["question"] for i in items], input_type="query")

    max_k = max(ks)
    per_query: list[dict] = []
    ranked_for_curve: list[tuple[list[str], dict[str, float]]] = []
    generation_rows: list[dict] = []

    async with AsyncSessionLocal() as session:
        paper_repo = build_paper_repo(session)
        chunk_repo = build_chunk_repo(session)

        for item, embedding in zip(items, query_embeddings):
            gains: dict[UUID, float] = {}
            for ref in relevant_refs(item):
                paper = await paper_repo.get_by_source_and_external_id(
                    ref["source"], ref["external_id"]
                )
                if paper is None:
                    print(f"  [{item['id']}] WARNING: {ref['source']}/{ref['external_id']} not in DB")
                    continue
                gains[paper.id] = ref["grade"]

            hits = await chunk_repo.search_by_project(
                project_id,
                embedding,
                max_distance=UNGATED_MAX_DISTANCE,
                top_k=max_k * CHUNKS_PER_PAPER,
            )
            ranked = collapse_to_papers(hits)
            ranked_ids = [pid for pid, _ in ranked]

            gated = await chunk_repo.search_by_project(
                project_id,
                embedding,
                max_distance=settings.retrieval_max_distance,
                top_k=settings.retrieval_top_k,
            )
            gated_hit = any(chunk.paper_id in gains for chunk, _ in gated)

            row = metrics.evaluate_query(ranked_ids, gains, ks)
            titles = {}
            for pid, _ in ranked[:max_k]:
                paper = await paper_repo.get_by_id(pid)
                titles[pid] = paper.title if paper is not None else str(pid)

            record = {
                "id": item["id"],
                "question": item["question"],
                "reviewed": bool(item.get("reviewed")),
                "relevant": [str(pid) for pid in gains],
                "gated_hit": gated_hit,
                "metrics": row,
                "ranked": [
                    {
                        "paper_id": str(pid),
                        "title": titles[pid],
                        "similarity": round(1.0 - dist, 4),
                        "relevant": pid in gains,
                    }
                    for pid, dist in ranked[:max_k]
                ],
            }
            ranked_for_curve.append(
                ([str(pid) for pid in ranked_ids], {str(pid): g for pid, g in gains.items()})
            )

            if not args.skip_generation:
                gen = await score_generation(
                    session, project_id, user_id, item, set(gains), gated_hit
                )
                record["generation"] = gen
                generation_rows.append(gen)

            per_query.append(record)
            rank = row["first_relevant_rank"]
            print(
                f"[{item['id']}] first relevant rank={rank or '-'} "
                f"RR={row['rr']:.2f} gated={'HIT' if gated_hit else 'MISS'}"
                + (f" generation={record['generation']['status']}" if "generation" in record else "")
            )

    summary = metrics.aggregate([r["metrics"] for r in per_query])
    summary["gated_hit"] = sum(r["gated_hit"] for r in per_query) / len(per_query)

    generation_summary = None
    if generation_rows:
        generation_summary = {
            "citation_validity": sum(g["citations_within_retrieved"] for g in generation_rows)
            / len(generation_rows),
            "false_refusals": [r["id"] for r in per_query if r["generation"]["false_refusal"]],
            "possibly_hallucinated": [
                r["id"] for r in per_query if r["generation"]["possibly_hallucinated"]
            ],
        }

    print_summary(summary, ks, len(per_query), generation_summary)

    out = args.out or RESULTS_DIR / f"run-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "project_id": str(project_id),
                "embedding_model": settings.voyage_embedding_model,
                "ks": list(ks),
                "settings": {
                    "retrieval_max_distance": settings.retrieval_max_distance,
                    "retrieval_top_k": settings.retrieval_top_k,
                },
                "summary": summary,
                "pr_curve": metrics.precision_recall_curve(ranked_for_curve, max_k),
                "generation": generation_summary,
                "queries": per_query,
            },
            f,
            indent=2,
        )
    print(f"\nWrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
