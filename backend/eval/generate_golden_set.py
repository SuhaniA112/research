"""Bootstraps golden_set.json with synthetic (question -> paper) pairs, sampled from the
Papers already saved to a given Project. Generated items are marked reviewed=false and are
meant to be hand-edited/verified before run_eval.py's numbers are trusted (see CONTEXT.md's
Eval decision: synthetic generation to bootstrap, hand-reviewed before trusting it).

Usage:
    python -m eval.generate_golden_set --project-id <uuid> --count 5
"""

import argparse
import asyncio
import json

import httpx
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.paper import Paper
from app.models.project_paper import ProjectPaper
from eval._wiring import build_openrouter_client

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"


async def sample_project_papers(project_id: UUID, count: int) -> list[Paper]:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Paper)
            .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
            .where(ProjectPaper.project_id == project_id)
            .order_by(func.random())
            .limit(count)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def generate_question(paper: Paper) -> str:
    client = build_openrouter_client()
    indexable_text = paper.abstract if paper.abstract else paper.title
    messages = [
        {
            "role": "system",
            "content": (
                "Given a paper's title and abstract, write exactly one question a reader "
                "would ask that this text answers. Reply with only the question, no preamble."
            ),
        },
        {"role": "user", "content": f"Title: {paper.title}\n\nText: {indexable_text}"},
    ]
    for attempt in range(4):
        try:
            return (await client.chat_completion(messages)).strip()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text.lower()
            if status == 429 and "per-day" in body:
                raise DailyLimitReached from exc
            if status not in (429, 502, 503) or attempt == 3:
                raise
            try:
                wait = float(exc.response.headers.get("retry-after", 0)) or 15.0 * (attempt + 1)
            except ValueError:
                wait = 15.0 * (attempt + 1)
            print(f"  OpenRouter {status}; retrying in {wait:.0f}s")
            await asyncio.sleep(min(wait, 120))
    raise RuntimeError("unreachable")


class DailyLimitReached(Exception):
    """Free-tier daily request cap hit; progress so far is kept."""


# Free models allow ~20 requests/minute.
REQUEST_SPACING_S = 3.5


def load_golden_set() -> dict:
    if GOLDEN_SET_PATH.exists():
        with GOLDEN_SET_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    return {
        "generated_at": None,
        "generator_model": None,
        "project_id": None,
        "items": [],
    }


def save_golden_set(data: dict) -> None:
    with GOLDEN_SET_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True, type=UUID)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate questions even for papers already present in the golden set.",
    )
    args = parser.parse_args()

    if not settings.openrouter_api_key.strip():
        raise SystemExit("OPENROUTER_API_KEY is empty in backend/.env (a free key works).")

    papers = await sample_project_papers(args.project_id, args.count)
    if not papers:
        print(f"No papers saved to project {args.project_id}. Save some papers first.")
        return

    data = load_golden_set()
    old_project = data.get("project_id")
    if data["items"] and old_project and old_project != str(args.project_id):
        # New project: archive the old set (git-ignored) and start fresh.
        archive = GOLDEN_SET_PATH.parent / "results" / f"golden_set-{old_project}.json"
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Archived previous project's golden set to {archive}")
        data = {**data, "items": []}
    existing_keys = {(item["source"], item["external_id"]) for item in data["items"]}
    next_index = len(data["items"]) + 1

    for paper in papers:
        key = (paper.source, paper.external_id)
        if key in existing_keys and not args.overwrite:
            continue

        try:
            question = await generate_question(paper)
        except DailyLimitReached:
            print("OpenRouter's free daily limit is used up; saved what was generated. "
                  "Rerun tomorrow to continue (already-done papers are skipped).")
            break
        except httpx.HTTPStatusError as exc:
            print(f"OpenRouter error {exc.response.status_code}; saved progress, rerun to continue.")
            break
        item = {
            "id": f"g{next_index}",
            "source": paper.source,
            "external_id": paper.external_id,
            "paper_title": paper.title,
            "question": question,
            "reviewed": False,
        }

        if key in existing_keys:
            data["items"] = [
                i for i in data["items"] if (i["source"], i["external_id"]) != key
            ]
        data["items"].append(item)
        existing_keys.add(key)
        next_index += 1
        print(f"[{item['id']}] {paper.title!r} -> {question}")
        data["project_id"] = str(args.project_id)
        save_golden_set(data)  # keep progress if a later request fails
        await asyncio.sleep(REQUEST_SPACING_S)

    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    data["generator_model"] = settings.openrouter_model
    data["project_id"] = str(args.project_id)
    save_golden_set(data)
    print(f"\nWrote {len(data['items'])} total item(s) to {GOLDEN_SET_PATH}")
    print(
        "Hand-review the generated questions and flip reviewed: true before trusting run_eval.py."
    )


if __name__ == "__main__":
    asyncio.run(main())
