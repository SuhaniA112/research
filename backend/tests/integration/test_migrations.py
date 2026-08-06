"""Alembic migration tests: clean install and existing-schema upgrade.

These tests are synchronous so Alembic's asyncio.run() does not nest inside
pytest's event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import assert_safe_test_database_url
from app.models import Base
from app.models.chunk import Chunk
from app.models.paper import Paper
from app.models.project import Project
from app.models.project_paper import ProjectPaper
from app.models.user import User

pytestmark = pytest.mark.integration

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_EXPECTED_TABLES = {
    "users",
    "projects",
    "papers",
    "chunks",
    "project_papers",
    "search_topics",
    "search_executions",
    "search_topic_papers",
}

_BASELINE_TABLES = (
    User.__table__,
    Project.__table__,
    Paper.__table__,
    Chunk.__table__,
    ProjectPaper.__table__,
)


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _head_revision(cfg: Config) -> str:
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    return heads[0]


async def _wipe_public_schema(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    finally:
        await engine.dispose()


async def _list_public_tables(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT tablename FROM pg_tables " "WHERE schemaname = 'public'"
                    )
                )
            ).fetchall()
            return {row[0] for row in rows}
    finally:
        await engine.dispose()


async def _alembic_version(database_url: str) -> str | None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            return await conn.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        await engine.dispose()


def test_migration_clean_install_from_empty_database(test_database_url) -> None:
    """Empty database → alembic upgrade head creates the full schema."""
    if test_database_url is None:
        pytest.skip("TEST_DATABASE_URL not set")

    assert_safe_test_database_url(test_database_url)

    # Completely empty schema — no Base.metadata.create_all before Alembic.
    asyncio.run(_wipe_public_schema(test_database_url))

    cfg = _alembic_config(test_database_url)
    head = _head_revision(cfg)
    command.upgrade(cfg, "head")

    tables = asyncio.run(_list_public_tables(test_database_url))
    assert _EXPECTED_TABLES.issubset(tables)

    version = asyncio.run(_alembic_version(test_database_url))
    assert version == head
    assert version == "0002_project_interest_profile"

    # alembic current should report head (no unfinished upgrade).
    command.current(cfg)


def test_migration_upgrade_from_existing_baseline_schema(test_database_url) -> None:
    """Baseline tables already present → upgrade head is additive and safe."""
    if test_database_url is None:
        pytest.skip("TEST_DATABASE_URL not set")

    assert_safe_test_database_url(test_database_url)

    async def _prepare_baseline_only() -> None:
        engine = create_async_engine(test_database_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(text("DROP SCHEMA public CASCADE"))
                await conn.execute(text("CREATE SCHEMA public"))
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                # Simulate a pre-shared-search database (create_all / prior deploy).
                await conn.run_sync(
                    lambda sync_conn: Base.metadata.create_all(
                        sync_conn, tables=list(_BASELINE_TABLES)
                    )
                )
        finally:
            await engine.dispose()

    asyncio.run(_prepare_baseline_only())

    before = asyncio.run(_list_public_tables(test_database_url))
    assert "users" in before
    assert "papers" in before
    assert "chunks" in before
    assert "projects" in before
    assert "project_papers" in before
    assert "search_topics" not in before

    cfg = _alembic_config(test_database_url)
    head = _head_revision(cfg)
    # 0000 is idempotent (skips existing baseline); later revisions are additive.
    command.upgrade(cfg, "head")

    after = asyncio.run(_list_public_tables(test_database_url))
    assert _EXPECTED_TABLES.issubset(after)

    version = asyncio.run(_alembic_version(test_database_url))
    assert version == head
    assert version == "0002_project_interest_profile"
    command.current(cfg)
