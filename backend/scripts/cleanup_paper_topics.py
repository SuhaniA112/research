#!/usr/bin/env python3
"""One-off maintenance: sanitize paper topics and reindex affected PaperIndexer rows.

Safe by design:
  - does not wipe the database
  - does not truncate tables
  - does not reset Docker volumes
  - only removes known query contaminants and remaps arXiv codes
  - reindexes only papers that already have PaperIndexer chunks

Usage (from backend/):

    python -m scripts.cleanup_paper_topics --dry-run
    python -m scripts.cleanup_paper_topics
    python -m scripts.cleanup_paper_topics --reindex
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.chunk import Chunk
from app.models.paper import Paper
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.services.embeddings.voyage_client import VoyageEmbeddingClient
from app.services.generation.openrouter_client import OpenRouterClient
from app.services.indexing.paper_indexer import PaperIndexer
from app.services.ingestion_service import IngestionService
from app.services.summarization.paper_summarizer import PaperSummarizer
from app.services.taxonomy.paper_topics import sanitize_persisted_topic_fields


def _ensure_backend_on_path() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))


async def _cleanup(*, dry_run: bool, reindex: bool) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Paper))
        papers = list(result.scalars().all())

        changed: list[Paper] = []
        for paper in papers:
            clean_topics, clean_categories = sanitize_persisted_topic_fields(
                list(paper.topics or []),
                list(paper.source_categories or []),
            )
            if clean_topics == list(paper.topics or []) and clean_categories == list(
                paper.source_categories or []
            ):
                continue
            print(
                f"paper {paper.id} ({paper.source}/{paper.external_id})\n"
                f"  topics: {list(paper.topics or [])!r} -> {clean_topics!r}\n"
                f"  source_categories: {list(paper.source_categories or [])!r}"
                f" -> {clean_categories!r}"
            )
            if not dry_run:
                paper.topics = clean_topics
                paper.source_categories = clean_categories
            changed.append(paper)

        if dry_run:
            print(f"[dry-run] would update {len(changed)} paper(s)")
            return

        if changed:
            await session.commit()
            print(f"updated {len(changed)} paper(s)")
        else:
            print("no topic contamination found")

        if not reindex:
            print(
                "skipping reindex "
                "(pass --reindex to rebuild PaperIndexer embeddings)"
            )
            return

        # Reindex only papers that have PaperIndexer chunks
        # (topics were in embed text).
        changed_ids = {p.id for p in changed}
        chunk_rows = await session.execute(
            select(Chunk.paper_id)
            .where(Chunk.indexer_version.is_not(None))
            .distinct()
        )
        indexed_ids = {row[0] for row in chunk_rows.all()}
        to_reindex = [
            p for p in papers if p.id in changed_ids and p.id in indexed_ids
        ]
        for paper in to_reindex:
            await session.refresh(paper)

        if not to_reindex:
            print("no affected PaperIndexer papers to reindex")
            return

        ingestion = IngestionService(
            paper_repo=PaperRepository(session),
            chunk_repo=ChunkRepository(session),
            project_paper_repo=ProjectPaperRepository(session),
            project_repo=ProjectRepository(session),
            voyage_client=VoyageEmbeddingClient(
                api_key=settings.voyage_api_key,
                model=settings.voyage_embedding_model,
            ),
            paper_indexer=PaperIndexer(),
            paper_summarizer=PaperSummarizer(
                OpenRouterClient(
                    api_key=settings.openrouter_api_key,
                    model=settings.openrouter_model,
                )
            ),
        )

        total_chunks = 0
        for paper in to_reindex:
            n = await ingestion.reindex_paper(paper)
            print(f"reindexed {paper.id}: {n} chunk(s)")
            total_chunks += n
        await session.commit()
        print(f"reindexed {len(to_reindex)} paper(s), {total_chunks} chunk(s)")


def main() -> None:
    _ensure_backend_on_path()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned topic cleanups without writing",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="After cleanup, reindex only affected PaperIndexer papers",
    )
    args = parser.parse_args()
    asyncio.run(_cleanup(dry_run=args.dry_run, reindex=args.reindex))


if __name__ == "__main__":
    main()
