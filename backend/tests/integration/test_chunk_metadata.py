"""Integration tests for chunk page metadata persistence and Ask citations."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.chunk import Chunk
from app.models.paper import Paper
from app.models.project import Project
from app.models.user import User
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.schemas.ask import Citation
from app.schemas.indexing import PreparedChunk
from app.services.ask_service import AskService

pytestmark = pytest.mark.integration


def _unit_vec(seed: int) -> list[float]:
    vec = [0.0] * 1024
    vec[seed % 1024] = 1.0
    return vec


@pytest.mark.asyncio
async def test_page_number_survives_indexing_to_db(db_session) -> None:
    paper_repo = PaperRepository(db_session)
    chunk_repo = ChunkRepository(db_session)

    paper = await paper_repo.create(
        Paper(
            source="arxiv",
            external_id="meta-001",
            title="PDF Paper",
            abstract="Abstract text",
            authors=["A"],
            year=2024,
            topics=["ml"],
        )
    )
    prepared = [
        PreparedChunk(
            chunk_id=f"{paper.id}:v1:00000",
            paper_id=str(paper.id),
            chunk_index=0,
            chunk_text="Page seven content",
            embedding_text="Title: PDF Paper\n\nPage: 7\n\nContent:\nPage seven content",
            metadata={
                "page_number": 7,
                "content_type": "full_text",
                "indexer_version": "v1",
            },
        ),
        PreparedChunk(
            chunk_id=f"{paper.id}:v1:00001",
            paper_id=str(paper.id),
            chunk_index=1,
            chunk_text="Abstract-derived chunk",
            embedding_text="Content:\nAbstract-derived chunk",
            metadata={
                "page_number": None,
                "content_type": "abstract",
                "indexer_version": "v1",
            },
        ),
    ]
    rows = await chunk_repo.create_many_for_paper(
        paper.id, prepared, [_unit_vec(1), _unit_vec(2)]
    )
    assert rows[0].page_number == 7
    assert rows[0].content_type == "full_text"
    assert rows[0].indexer_version == "v1"
    assert rows[1].page_number is None
    assert rows[1].content_type == "abstract"

    reloaded = await chunk_repo.list_for_paper(paper.id)
    assert reloaded[0].page_number == 7
    assert reloaded[1].page_number is None


@pytest.mark.asyncio
async def test_ask_citations_include_page_number(db_session, mock_voyage) -> None:
    user = await UserRepository(db_session).create(
        User(
            email="cite@example.com",
            full_name="Cite",
            hashed_password="x",
            is_active=True,
        )
    )
    project = await ProjectRepository(db_session).create(
        Project(
            user_id=user.id,
            name="Cite Project",
            topics=["ml"],
            keywords=[],
            reading_level="graduate",
        )
    )
    paper = await PaperRepository(db_session).create(
        Paper(
            source="arxiv",
            external_id="cite-001",
            title="Cited Paper",
            abstract="Abstract",
            authors=["A"],
            year=2024,
            url="https://example.com/p",
            topics=["ml"],
        )
    )
    await ProjectPaperRepository(db_session).create_if_absent(project.id, paper.id)

    chunk = Chunk(
        paper_id=paper.id,
        chunk_index=0,
        text="Relevant chunk text about transformers.",
        embedding=_unit_vec(3),
        page_number=7,
        content_type="full_text",
        indexer_version="v1",
    )
    db_session.add(chunk)
    await db_session.flush()

    null_meta_chunk = Chunk(
        paper_id=paper.id,
        chunk_index=1,
        text="Title-only fallback chunk.",
        embedding=_unit_vec(4),
        page_number=None,
        content_type="title",
        indexer_version="v1",
    )
    db_session.add(null_meta_chunk)
    await db_session.flush()

    openrouter = AsyncMock()
    openrouter.chat_completion.return_value = (
        f"Transformers help.\nCITATIONS: [{chunk.id}]"
    )

    ask = AskService(
        ProjectRepository(db_session),
        ChunkRepository(db_session),
        mock_voyage,
        openrouter,
        max_distance=2.0,
        top_k=5,
    )
    response = await ask.ask(project.id, "What about transformers?", user_id=user.id)
    assert response.status == "answered"
    assert len(response.citations) == 1
    citation: Citation = response.citations[0]
    assert citation.page_number == 7
    assert citation.paper_id == paper.id
    assert citation.chunk_id == chunk.id


@pytest.mark.asyncio
async def test_ask_with_null_page_metadata_still_works(db_session, mock_voyage) -> None:
    user = await UserRepository(db_session).create(
        User(
            email="nullmeta@example.com",
            full_name="Null",
            hashed_password="x",
            is_active=True,
        )
    )
    project = await ProjectRepository(db_session).create(
        Project(
            user_id=user.id,
            name="Null Meta",
            topics=["ml"],
            keywords=[],
            reading_level="graduate",
        )
    )
    paper = await PaperRepository(db_session).create(
        Paper(
            source="arxiv",
            external_id="null-001",
            title="No Page Paper",
            abstract="Abstract only",
            authors=["A"],
            year=2024,
            topics=["ml"],
        )
    )
    await ProjectPaperRepository(db_session).create_if_absent(project.id, paper.id)
    chunk = Chunk(
        paper_id=paper.id,
        chunk_index=0,
        text="Abstract only chunk",
        embedding=_unit_vec(5),
        page_number=None,
        content_type=None,
        indexer_version=None,
    )
    db_session.add(chunk)
    await db_session.flush()

    openrouter = AsyncMock()
    openrouter.chat_completion.return_value = f"Answer.\nCITATIONS: [{chunk.id}]"

    ask = AskService(
        ProjectRepository(db_session),
        ChunkRepository(db_session),
        mock_voyage,
        openrouter,
        max_distance=2.0,
        top_k=5,
    )
    response = await ask.ask(project.id, "Summarize", user_id=user.id)
    assert response.status == "answered"
    assert response.citations[0].page_number is None
