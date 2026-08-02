"""Shared pytest fixtures and test-database safety guards."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import assert_safe_test_database_url


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "integration: requires PostgreSQL+pgvector test database"
    )


@pytest.fixture
def test_database_url() -> str | None:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        return None
    assert_safe_test_database_url(url)
    return url


@pytest_asyncio.fixture
async def db_engine(
    test_database_url: str | None,
) -> AsyncGenerator[AsyncEngine, None]:
    if test_database_url is None:
        pytest.skip("TEST_DATABASE_URL not set")

    from app.models import Base

    engine = create_async_engine(test_database_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(
    db_engine: AsyncEngine,
) -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    yield factory


@pytest_asyncio.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()
            await session.close()


@pytest.fixture
def mock_voyage() -> AsyncMock:
    client = AsyncMock()

    async def _embed(
        texts: list[str], *, input_type: str = "document"
    ) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            seed = sum(ord(c) for c in text) % 97
            vectors.append([((seed + i) % 50) / 50.0 for i in range(8)] + [0.0] * 1016)
        return vectors

    client.embed.side_effect = _embed
    return client


@pytest.fixture
def sample_ind_paper():
    from app.schemas.research_papers import IndPaper

    return IndPaper(
        title="Contextual Retrieval for Scientific Literature",
        abstract="We study contextual retrieval over scholarly corpora.",
        authors=["Ada Lovelace"],
        year=2024,
        url="https://example.com/paper",
        pdf_url=None,
        source="arxiv",
        external_id="2401.00001",
        topics=["retrieval"],
    )
