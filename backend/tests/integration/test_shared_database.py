"""PostgreSQL + pgvector integration tests.

Requires TEST_DATABASE_URL pointing at a database whose name contains 'test'.
Mocks Voyage and external providers; exercises real SQLAlchemy + pgvector.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models.chunk import Chunk
from app.models.paper import Paper
from app.models.project import Project
from app.models.project_paper import ProjectPaper
from app.models.search_execution import SearchExecution
from app.models.user import User
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.search_execution_repo import SearchExecutionRepository
from app.repositories.search_topic_paper_repo import SearchTopicPaperRepository
from app.repositories.search_topic_repo import SearchTopicRepository
from app.repositories.user_repo import UserRepository
from app.schemas.research_discovery import DiscoverySearchRequest
from app.schemas.research_papers import IndPaper
from app.services.discovery_search_service import DiscoverySearchService
from app.services.ingestion_service import IngestionService
from app.services.indexing.paper_indexer import PaperIndexer

pytestmark = pytest.mark.integration


def _unit_vec(seed: int) -> list[float]:
    vec = [0.0] * 1024
    vec[seed % 1024] = 1.0
    vec[(seed + 1) % 1024] = 0.1
    return vec


@pytest.mark.asyncio
async def test_global_paper_shared_across_projects(db_session) -> None:
    paper_repo = PaperRepository(db_session)
    chunk_repo = ChunkRepository(db_session)
    project_repo = ProjectRepository(db_session)
    project_paper_repo = ProjectPaperRepository(db_session)
    voyage = AsyncMock()
    voyage.api_key = "test-key"
    voyage.embed.return_value = [_unit_vec(1)]
    paper_summarizer = AsyncMock()
    paper_summarizer.summarize.return_value = None

    ingestion = IngestionService(
        paper_repo,
        chunk_repo,
        project_paper_repo,
        project_repo,
        voyage,
        PaperIndexer(),
        paper_summarizer,
    )

    p1 = await project_repo.create(
        Project(name="User A Project", topics=["AI/ML"], keywords=[], reading_level="graduate")
    )
    p2 = await project_repo.create(
        Project(name="User B Project", topics=["HCI"], keywords=[], reading_level="graduate")
    )

    ind = IndPaper(
        title="Shared Global Paper",
        abstract="Shared abstract for embedding.",
        authors=["A"],
        year=2024,
        source="arxiv",
        external_id="shared-001",
    )

    r1 = await ingestion.save_paper_to_project(p1.id, ind)
    r2 = await ingestion.save_paper_to_project(p2.id, ind)

    assert r1.paper.id == r2.paper.id

    paper_count = await db_session.scalar(select(func.count()).select_from(Paper))
    chunk_count = await db_session.scalar(select(func.count()).select_from(Chunk))
    link_count = await db_session.scalar(select(func.count()).select_from(ProjectPaper))

    assert paper_count == 1
    assert chunk_count == 1
    assert link_count == 2


@pytest.mark.asyncio
async def test_concurrent_paper_upsert_creates_one_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Two independent transactions race to upsert the same canonical Paper."""
    ind = IndPaper(
        title="Race Paper",
        abstract="Abstract",
        authors=["A"],
        year=2024,
        source="arxiv",
        external_id="race-001",
    )

    async def upsert_in_own_session() -> tuple[object, bool]:
        async with session_factory() as session:
            try:
                repo = PaperRepository(session)
                paper, created = await repo.upsert_from_ind_paper(ind)
                paper_id = paper.id
                await session.commit()
                return paper_id, created
            except Exception:
                await session.rollback()
                raise

    results = await asyncio.gather(
        upsert_in_own_session(),
        upsert_in_own_session(),
    )
    ids = {paper_id for paper_id, _ in results}
    assert len(ids) == 1
    assert sum(1 for _, created in results if created) == 1
    assert sum(1 for _, created in results if not created) == 1

    async with session_factory() as verify_session:
        count = await verify_session.scalar(
            select(func.count())
            .select_from(Paper)
            .where(Paper.source == "arxiv", Paper.external_id == "race-001")
        )
        assert count == 1


@pytest.mark.asyncio
async def test_paper_associated_with_multiple_topics(db_session) -> None:
    paper_repo = PaperRepository(db_session)
    topic_repo = SearchTopicRepository(db_session)
    topic_paper_repo = SearchTopicPaperRepository(db_session)

    paper, _ = await paper_repo.upsert_from_ind_paper(
        IndPaper(
            title="Multi-topic",
            abstract="a",
            authors=[],
            year=2021,
            source="arxiv",
            external_id="mt-1",
        )
    )
    t1, _ = await topic_repo.get_or_create_by_normalized_query(
        canonical_query="topic one",
        normalized_query="topic one",
        embedding=_unit_vec(2),
    )
    t2, _ = await topic_repo.get_or_create_by_normalized_query(
        canonical_query="topic two",
        normalized_query="topic two",
        embedding=_unit_vec(3),
    )
    await topic_paper_repo.upsert_association(
        search_topic_id=t1.id, paper_id=paper.id, semantic_relevance_score=0.9
    )
    await topic_paper_repo.upsert_association(
        search_topic_id=t2.id, paper_id=paper.id, semantic_relevance_score=0.8
    )

    assert await topic_paper_repo.count_for_topic(t1.id) == 1
    assert await topic_paper_repo.count_for_topic(t2.id) == 1


@pytest.mark.asyncio
async def test_discovery_cache_hit_and_execution_privacy(
    db_session, mock_voyage
) -> None:
    paper_repo = PaperRepository(db_session)
    chunk_repo = ChunkRepository(db_session)
    topic_repo = SearchTopicRepository(db_session)
    execution_repo = SearchExecutionRepository(db_session)
    topic_paper_repo = SearchTopicPaperRepository(db_session)
    user_repo = UserRepository(db_session)

    settings = Settings(
        app_env="test",
        search_cache_min_results=2,
        search_default_limit=2,
        search_cache_paper_similarity_threshold=0.5,
    )

    emb = _unit_vec(10)
    mock_voyage.embed.return_value = [emb]

    user_a = await user_repo.create(
        User(
            email=f"user-a-{uuid4()}@example.com",
            full_name="User A",
            hashed_password="hashed-a",
        )
    )
    user_b = await user_repo.create(
        User(
            email=f"user-b-{uuid4()}@example.com",
            full_name="User B",
            hashed_password="hashed-b",
        )
    )
    await db_session.flush()

    topic, _ = await topic_repo.get_or_create_by_normalized_query(
        canonical_query="neural ir",
        normalized_query="neural ir",
        embedding=emb,
    )
    topic.last_external_refresh_at = datetime.now(timezone.utc)
    await db_session.flush()

    paper_ids: list = []
    for i in range(3):
        paper, _ = await paper_repo.upsert_from_ind_paper(
            IndPaper(
                title=f"Neural IR {i}",
                abstract="neural information retrieval methods",
                authors=["A"],
                year=2024,
                source="arxiv",
                external_id=f"nir-{i}",
            )
        )
        paper_ids.append(paper.id)
        await chunk_repo.ensure_chunk_for_paper(
            paper.id, paper.abstract or paper.title, emb
        )
        await topic_paper_repo.upsert_association(
            search_topic_id=topic.id,
            paper_id=paper.id,
            semantic_relevance_score=0.95,
        )

    assert len(set(paper_ids)) == 3

    service = DiscoverySearchService(
        paper_repo=paper_repo,
        chunk_repo=chunk_repo,
        search_topic_repo=topic_repo,
        search_execution_repo=execution_repo,
        search_topic_paper_repo=topic_paper_repo,
        voyage_client=mock_voyage,
        settings=settings,
        provider_clients=[],
    )

    r1 = await service.search(
        DiscoverySearchRequest(query="neural ir", limit=2), user_id=user_a.id
    )
    r2 = await service.search(
        DiscoverySearchRequest(query="neural ir", limit=2), user_id=user_b.id
    )

    assert r1.cache_hit is True
    assert r2.cache_hit is True
    assert r1.search_execution_id != r2.search_execution_id
    assert r1.matched_topic_id == r2.matched_topic_id == topic.id

    # Both users reuse the same global papers / topic; responses stay private.
    exec_rows = (
        (
            await db_session.execute(
                select(SearchExecution).order_by(SearchExecution.created_at)
            )
        )
        .scalars()
        .all()
    )
    assert len(exec_rows) == 2
    assert {row.user_id for row in exec_rows} == {user_a.id, user_b.id}
    assert {row.search_topic_id for row in exec_rows} == {topic.id}

    paper_count = await db_session.scalar(select(func.count()).select_from(Paper))
    chunk_count = await db_session.scalar(select(func.count()).select_from(Chunk))
    assert paper_count == 3
    assert chunk_count == 3

    dumped = r1.model_dump()
    assert "user_id" not in dumped
    assert "raw_query" not in dumped or dumped.get("query") == "neural ir"
    # Another user's identity / private execution fields are never returned.
    assert user_b.id not in {
        dumped.get("search_execution_id"),
        dumped.get("matched_topic_id"),
    }
    assert "project" not in dumped
    assert "project_id" not in dumped


@pytest.mark.asyncio
async def test_unchanged_paper_skips_redundant_embedding(db_session) -> None:
    paper_repo = PaperRepository(db_session)
    chunk_repo = ChunkRepository(db_session)

    paper, created = await paper_repo.upsert_from_ind_paper(
        IndPaper(
            title="Embed Once",
            abstract="Stable abstract",
            authors=[],
            year=2020,
            source="arxiv",
            external_id="embed-1",
        )
    )
    assert created
    emb = _unit_vec(7)
    chunk, created_chunk = await chunk_repo.ensure_chunk_for_paper(
        paper.id, "Stable abstract", emb
    )
    assert created_chunk

    chunk2, created2 = await chunk_repo.ensure_chunk_for_paper(
        paper.id, "Stable abstract", emb
    )
    assert created2 is False
    assert chunk2.id == chunk.id

    count = await db_session.scalar(select(func.count()).select_from(Chunk))
    assert count == 1


@pytest.mark.asyncio
async def test_title_fallback_when_no_abstract(db_session) -> None:
    paper_repo = PaperRepository(db_session)
    chunk_repo = ChunkRepository(db_session)

    paper, _ = await paper_repo.upsert_from_ind_paper(
        IndPaper(
            title="Title Only Paper",
            abstract=None,
            authors=[],
            year=2019,
            source="dblp",
            external_id="dblp-1",
        )
    )
    emb = _unit_vec(8)
    chunk, _ = await chunk_repo.ensure_chunk_for_paper(paper.id, paper.title, emb)
    assert chunk.text == "Title Only Paper"
