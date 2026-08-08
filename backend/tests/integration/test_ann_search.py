"""Integration tests for ANN-friendly vector retrieval and HNSW index."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.models.chunk import Chunk
from app.models.paper import Paper
from app.models.project import Project
from app.models.user import User
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository

pytestmark = pytest.mark.integration


def _unit_vec(seed: int) -> list[float]:
    vec = [0.0] * 1024
    vec[seed % 1024] = 1.0
    return vec


@pytest.mark.asyncio
async def test_hnsw_index_exists_after_create_all(db_session) -> None:
    chunk_repo = ChunkRepository(db_session)
    # create_all in conftest builds model indexes including HNSW.
    assert await chunk_repo.hnsw_index_exists() is True


@pytest.mark.asyncio
async def test_search_global_orders_and_dedupes_papers(db_session) -> None:
    paper_repo = PaperRepository(db_session)
    chunk_repo = ChunkRepository(db_session)

    near = await paper_repo.create(
        Paper(
            source="arxiv",
            external_id="ann-near",
            title="Near Paper",
            abstract="near",
            authors=["A"],
            year=2024,
            topics=["ml"],
        )
    )
    far = await paper_repo.create(
        Paper(
            source="arxiv",
            external_id="ann-far",
            title="Far Paper",
            abstract="far",
            authors=["A"],
            year=2024,
            topics=["ml"],
        )
    )
    # Two chunks for near paper — best distance should win after dedupe.
    db_session.add_all(
        [
            Chunk(
                paper_id=near.id,
                chunk_index=0,
                text="near-a",
                embedding=_unit_vec(1),
            ),
            Chunk(
                paper_id=near.id,
                chunk_index=1,
                text="near-b",
                embedding=_unit_vec(1),
            ),
            Chunk(
                paper_id=far.id,
                chunk_index=0,
                text="far",
                embedding=_unit_vec(50),
            ),
        ]
    )
    await db_session.flush()

    query = _unit_vec(1)
    results = await chunk_repo.search_global(
        query, max_distance=2.0, limit=10, candidate_multiplier=10
    )
    assert len(results) == 2
    assert results[0][0].id == near.id
    assert results[0][1] <= results[1][1]
    paper_ids = [p.id for p, _ in results]
    assert paper_ids.count(near.id) == 1


@pytest.mark.asyncio
async def test_search_global_respects_threshold_and_limit(db_session) -> None:
    paper_repo = PaperRepository(db_session)
    chunk_repo = ChunkRepository(db_session)

    papers = []
    for i in range(5):
        paper = await paper_repo.create(
            Paper(
                source="arxiv",
                external_id=f"lim-{i}",
                title=f"Paper {i}",
                abstract="x",
                authors=["A"],
                year=2024,
                topics=["ml"],
            )
        )
        papers.append(paper)
        db_session.add(
            Chunk(
                paper_id=paper.id,
                chunk_index=0,
                text=f"t{i}",
                embedding=_unit_vec(i),
            )
        )
    await db_session.flush()

    query = _unit_vec(0)
    # Tight threshold: only very near neighbors.
    tight = await chunk_repo.search_global(
        query, max_distance=0.01, limit=10, candidate_multiplier=10
    )
    assert all(dist <= 0.01 for _, dist in tight)

    limited = await chunk_repo.search_global(
        query, max_distance=2.0, limit=2, candidate_multiplier=10
    )
    assert len(limited) == 2


@pytest.mark.asyncio
async def test_project_scoped_retrieval_excludes_other_projects(db_session) -> None:
    user_repo = UserRepository(db_session)
    user = await user_repo.create(
        User(
            email="ann@example.com",
            full_name="Ann",
            hashed_password="x",
            is_active=True,
        )
    )
    project_repo = ProjectRepository(db_session)
    project_a = await project_repo.create(
        Project(
            user_id=user.id,
            name="A",
            topics=["ml"],
            keywords=[],
            reading_level="graduate",
        )
    )
    project_b = await project_repo.create(
        Project(
            user_id=user.id,
            name="B",
            topics=["ml"],
            keywords=[],
            reading_level="graduate",
        )
    )
    paper_repo = PaperRepository(db_session)
    paper_a = await paper_repo.create(
        Paper(
            source="arxiv",
            external_id="pa",
            title="In A",
            abstract="a",
            authors=["A"],
            year=2024,
            topics=["ml"],
        )
    )
    paper_b = await paper_repo.create(
        Paper(
            source="arxiv",
            external_id="pb",
            title="In B",
            abstract="b",
            authors=["A"],
            year=2024,
            topics=["ml"],
        )
    )
    links = ProjectPaperRepository(db_session)
    await links.create_if_absent(project_a.id, paper_a.id)
    await links.create_if_absent(project_b.id, paper_b.id)

    # Identical embeddings — without project filter both would match equally.
    db_session.add_all(
        [
            Chunk(
                paper_id=paper_a.id,
                chunk_index=0,
                text="a",
                embedding=_unit_vec(7),
            ),
            Chunk(
                paper_id=paper_b.id,
                chunk_index=0,
                text="b",
                embedding=_unit_vec(7),
            ),
        ]
    )
    await db_session.flush()

    chunk_repo = ChunkRepository(db_session)
    hits = await chunk_repo.search_by_project(
        project_a.id,
        _unit_vec(7),
        max_distance=2.0,
        top_k=5,
        candidate_multiplier=10,
    )
    assert len(hits) == 1
    assert hits[0][0].paper_id == paper_a.id


@pytest.mark.asyncio
async def test_migration_creates_hnsw_index(test_database_url) -> None:
    if test_database_url is None:
        pytest.skip("TEST_DATABASE_URL not set")

    import asyncio
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.database import assert_safe_test_database_url

    assert_safe_test_database_url(test_database_url)

    async def _wipe() -> None:
        engine = create_async_engine(test_database_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(text("DROP SCHEMA public CASCADE"))
                await conn.execute(text("CREATE SCHEMA public"))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        finally:
            await engine.dispose()

    async def _index_exists() -> bool:
        engine = create_async_engine(test_database_url)
        try:
            async with engine.connect() as conn:
                row = await conn.execute(
                    text(
                        "SELECT 1 FROM pg_indexes "
                        "WHERE indexname = 'ix_chunks_embedding_hnsw'"
                    )
                )
                return row.scalar_one_or_none() is not None
        finally:
            await engine.dispose()

    await _wipe()
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", test_database_url)
    await asyncio.to_thread(command.upgrade, cfg, "head")
    assert await _index_exists() is True
