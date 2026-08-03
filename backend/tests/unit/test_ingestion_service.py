"""Unit tests for merged IngestionService save/index behavior."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.paper import Paper
from app.schemas.indexing import PreparedChunk
from app.schemas.research_papers import IndPaper
from app.services.ingestion_service import IngestionService


def _paper(**kwargs) -> Paper:
    defaults = dict(
        id=uuid4(),
        source="arxiv",
        external_id="2401.00001",
        title="Contextual Retrieval for Scientific Literature",
        abstract="We study contextual retrieval over scholarly corpora.",
        authors=["Ada Lovelace"],
        year=2024,
        url="https://example.com/paper",
        pdf_url=None,
        topics=["retrieval"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Paper(**defaults)


def _ind_paper(**kwargs) -> IndPaper:
    defaults = dict(
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
    defaults.update(kwargs)
    return IndPaper(**defaults)


def _prepared_chunks(paper_id: str, count: int = 2) -> list[PreparedChunk]:
    return [
        PreparedChunk(
            chunk_id=f"{paper_id}:v1:{i:05d}",
            paper_id=paper_id,
            chunk_index=i,
            chunk_text=f"chunk text {i}",
            embedding_text=f"embedding text {i}",
            metadata={},
        )
        for i in range(count)
    ]


def _build_service(
    *,
    paper: Paper,
    paper_created: bool,
    link_created: bool,
    existing_chunk: MagicMock | None,
    prepared_chunks: list[PreparedChunk] | None = None,
) -> tuple[IngestionService, dict[str, AsyncMock]]:
    project_id = uuid4()
    project = MagicMock()
    project.id = project_id

    paper_repo = AsyncMock()
    paper_repo.upsert_from_ind_paper.return_value = (paper, paper_created)

    chunk_repo = AsyncMock()
    chunk_repo.get_for_paper.return_value = existing_chunk
    chunk_repo.create_many_for_paper.return_value = []

    project_paper_repo = AsyncMock()
    project_paper_repo.create_if_absent.return_value = (MagicMock(), link_created)

    project_repo = AsyncMock()
    project_repo.get_by_id.return_value = project

    voyage = AsyncMock()
    chunks = prepared_chunks if prepared_chunks is not None else _prepared_chunks(
        str(paper.id)
    )
    voyage.embed.return_value = [[0.1] * 1024 for _ in chunks]

    paper_indexer = AsyncMock()
    paper_indexer.prepare_chunks.return_value = chunks

    service = IngestionService(
        paper_repo,
        chunk_repo,
        project_paper_repo,
        project_repo,
        voyage,
        paper_indexer,
    )
    mocks = {
        "paper_repo": paper_repo,
        "chunk_repo": chunk_repo,
        "project_paper_repo": project_paper_repo,
        "project_repo": project_repo,
        "voyage": voyage,
        "paper_indexer": paper_indexer,
        "project_id": project_id,
        "prepared_chunks": chunks,
    }
    return service, mocks


@pytest.mark.asyncio
async def test_newly_created_paper_is_indexed_and_linked() -> None:
    paper = _paper()
    prepared = _prepared_chunks(str(paper.id), count=2)
    service, mocks = _build_service(
        paper=paper,
        paper_created=True,
        link_created=True,
        existing_chunk=None,
        prepared_chunks=prepared,
    )
    paper_in = _ind_paper()

    result = await service.save_paper_to_project(mocks["project_id"], paper_in)

    mocks["paper_repo"].upsert_from_ind_paper.assert_awaited_once_with(paper_in)
    mocks["chunk_repo"].get_for_paper.assert_not_awaited()
    mocks["paper_indexer"].prepare_chunks.assert_awaited_once_with(
        str(paper.id), paper_in
    )
    mocks["voyage"].embed.assert_awaited_once_with(
        [chunk.embedding_text for chunk in prepared],
        input_type="document",
    )
    mocks["chunk_repo"].create_many_for_paper.assert_awaited_once_with(
        paper.id,
        prepared,
        mocks["voyage"].embed.return_value,
    )
    mocks["project_paper_repo"].create_if_absent.assert_awaited_once_with(
        mocks["project_id"], paper.id
    )
    assert result.already_saved is False
    assert result.paper.id == paper.id


@pytest.mark.asyncio
async def test_existing_paper_with_chunks_skips_indexing() -> None:
    paper = _paper()
    existing_chunk = MagicMock()
    service, mocks = _build_service(
        paper=paper,
        paper_created=False,
        link_created=True,
        existing_chunk=existing_chunk,
    )
    paper_in = _ind_paper()

    result = await service.save_paper_to_project(mocks["project_id"], paper_in)

    mocks["paper_repo"].upsert_from_ind_paper.assert_awaited_once_with(paper_in)
    mocks["chunk_repo"].get_for_paper.assert_awaited_once_with(paper.id)
    mocks["paper_indexer"].prepare_chunks.assert_not_awaited()
    mocks["voyage"].embed.assert_not_awaited()
    mocks["chunk_repo"].create_many_for_paper.assert_not_awaited()
    mocks["project_paper_repo"].create_if_absent.assert_awaited_once_with(
        mocks["project_id"], paper.id
    )
    assert result.already_saved is False
    assert result.paper.id == paper.id


@pytest.mark.asyncio
async def test_existing_paper_without_chunks_is_backfilled() -> None:
    paper = _paper()
    prepared = _prepared_chunks(str(paper.id), count=2)
    service, mocks = _build_service(
        paper=paper,
        paper_created=False,
        link_created=True,
        existing_chunk=None,
        prepared_chunks=prepared,
    )
    paper_in = _ind_paper()

    result = await service.save_paper_to_project(mocks["project_id"], paper_in)

    mocks["paper_repo"].upsert_from_ind_paper.assert_awaited_once_with(paper_in)
    mocks["chunk_repo"].get_for_paper.assert_awaited_once_with(paper.id)
    mocks["paper_indexer"].prepare_chunks.assert_awaited_once_with(
        str(paper.id), paper_in
    )
    mocks["voyage"].embed.assert_awaited_once_with(
        [chunk.embedding_text for chunk in prepared],
        input_type="document",
    )
    mocks["chunk_repo"].create_many_for_paper.assert_awaited_once_with(
        paper.id,
        prepared,
        mocks["voyage"].embed.return_value,
    )
    assert result.already_saved is False
    assert result.paper.id == paper.id


@pytest.mark.asyncio
async def test_already_linked_paper_sets_already_saved_and_skips_reindex() -> None:
    paper = _paper()
    existing_chunk = MagicMock()
    service, mocks = _build_service(
        paper=paper,
        paper_created=False,
        link_created=False,
        existing_chunk=existing_chunk,
    )
    paper_in = _ind_paper()

    result = await service.save_paper_to_project(mocks["project_id"], paper_in)

    mocks["paper_repo"].upsert_from_ind_paper.assert_awaited_once_with(paper_in)
    mocks["chunk_repo"].get_for_paper.assert_awaited_once_with(paper.id)
    mocks["paper_indexer"].prepare_chunks.assert_not_awaited()
    mocks["voyage"].embed.assert_not_awaited()
    mocks["chunk_repo"].create_many_for_paper.assert_not_awaited()
    mocks["project_paper_repo"].create_if_absent.assert_awaited_once_with(
        mocks["project_id"], paper.id
    )
    assert result.already_saved is True
    assert result.paper.id == paper.id
