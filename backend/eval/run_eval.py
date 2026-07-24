"""Scores Retrieval and generation against golden_set.json, as two separately-reported
metrics (see CONTEXT.md's Eval decision: split, not blended, since they fail for different
reasons).

Usage:
    python -m eval.run_eval --project-id <uuid>
"""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from eval._wiring import build_ask_service, build_paper_repo, build_chunk_repo, build_voyage_client

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"


def load_golden_set() -> dict:
    with GOLDEN_SET_PATH.open() as f:
        return json.load(f)


async def score_retrieval_hit(project_id: UUID, item: dict) -> bool:
    async with AsyncSessionLocal() as session:
        paper_repo = build_paper_repo(session)
        chunk_repo = build_chunk_repo(session)
        voyage_client = build_voyage_client()

        expected_paper = await paper_repo.get_by_source_and_external_id(
            item["source"], item["external_id"]
        )
        if expected_paper is None:
            print(f"  [{item['id']}] WARNING: paper {item['source']}/{item['external_id']} not found in DB")
            return False

        [query_embedding] = await voyage_client.embed([item["question"]], input_type="query")
        results = await chunk_repo.search_by_project(
            project_id,
            query_embedding,
            max_distance=settings.retrieval_max_distance,
            top_k=settings.retrieval_top_k,
        )
        return any(chunk.paper_id == expected_paper.id for chunk, _ in results)


async def score_generation(project_id: UUID, item: dict, retrieval_hit: bool) -> dict:
    async with AsyncSessionLocal() as session:
        ask_service = build_ask_service(session)
        paper_repo = build_paper_repo(session)

        expected_paper = await paper_repo.get_by_source_and_external_id(
            item["source"], item["external_id"]
        )
        response, retrieved_chunk_ids = await ask_service.ask(
            project_id, item["question"], debug=True
        )

        citation_paper_ids = {c.paper_id for c in response.citations}
        citations_within_retrieved = all(
            c.chunk_id in retrieved_chunk_ids for c in response.citations
        )
        false_refusal = response.status == "no_relevant_sources" and retrieval_hit
        possibly_hallucinated = (
            response.status == "answered"
            and expected_paper is not None
            and expected_paper.id not in citation_paper_ids
        )

        return {
            "status": response.status,
            "citations_within_retrieved": citations_within_retrieved,
            "false_refusal": false_refusal,
            "possibly_hallucinated": possibly_hallucinated,
        }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", type=UUID, default=None)
    args = parser.parse_args()

    data = load_golden_set()
    items = data["items"]
    if not items:
        print(f"No golden set items found in {GOLDEN_SET_PATH}. Run generate_golden_set.py first.")
        return

    project_id = args.project_id or (UUID(data["project_id"]) if data["project_id"] else None)
    if project_id is None:
        print("No --project-id given and none stored in golden_set.json.")
        return

    unreviewed = [i["id"] for i in items if not i.get("reviewed")]
    if unreviewed:
        print(f"WARNING: {len(unreviewed)} unreviewed item(s) in golden set: {unreviewed}")
        print("These are synthetic and not yet hand-verified — treat these numbers as provisional.\n")

    hits = 0
    citation_valid = 0
    flagged: list[str] = []

    for item in items:
        hit = await score_retrieval_hit(project_id, item)
        hits += int(hit)

        gen = await score_generation(project_id, item, hit)
        citation_valid += int(gen["citations_within_retrieved"])

        flag_reasons = []
        if gen["false_refusal"]:
            flag_reasons.append("false_refusal")
        if gen["possibly_hallucinated"]:
            flag_reasons.append("possibly_hallucinated")
        if not gen["citations_within_retrieved"]:
            flag_reasons.append("citation_outside_retrieved_set")

        status_str = "HIT" if hit else "MISS"
        print(f"[{item['id']}] retrieval={status_str} generation={gen['status']}"
              + (f" FLAGGED({', '.join(flag_reasons)})" if flag_reasons else ""))
        if flag_reasons:
            flagged.append(item["id"])

    total = len(items)
    print("\n--- Summary ---")
    print(f"Retrieval hit@k: {hits}/{total} ({hits / total:.0%})")
    print(f"Citation validity: {citation_valid}/{total} ({citation_valid / total:.0%})")
    print(f"Flagged items: {flagged or 'none'}")


if __name__ == "__main__":
    asyncio.run(main())
