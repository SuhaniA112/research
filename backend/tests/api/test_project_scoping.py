"""API tests for temporary X-User-ID project ownership scoping."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import (
    get_ask_service,
    get_current_user,
    get_ingestion_service,
    get_project_service,
)
from app.main import app
from app.models.user import User
from app.schemas.ask import AskResponse
from app.schemas.paper import PaperResponse, SavePaperResponse
from app.schemas.project import ProjectResponse


def _user(*, email: str = "a@example.com") -> User:
    return User(
        id=uuid4(),
        email=email,
        full_name="Test User",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _project_response(*, project_id=None, name: str = "Proj") -> ProjectResponse:
    now = datetime.now(timezone.utc)
    return ProjectResponse(
        id=project_id or uuid4(),
        name=name,
        description=None,
        created_at=now,
        updated_at=now,
        source_count=0,
        topics=["Machine Learning"],
        keywords=["imaging"],
        reading_level="graduate",
    )


@pytest.fixture
def user_a() -> User:
    return _user(email="a@example.com")


@pytest.fixture
def user_b() -> User:
    return _user(email="b@example.com")


@pytest.fixture
def project_owned_by_a(user_a: User) -> ProjectResponse:
    return _project_response(name="A's Project")


@pytest.mark.asyncio
async def test_user_a_can_create_list_read_project(
    user_a: User, project_owned_by_a: ProjectResponse
) -> None:
    project_service = AsyncMock()
    project_service.create_project.return_value = project_owned_by_a
    project_service.list_projects.return_value = [project_owned_by_a]
    project_service.get_project.return_value = project_owned_by_a

    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_project_service] = lambda: project_service

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"X-User-ID": str(user_a.id)}
            created = await client.post(
                "/api/v1/projects",
                headers=headers,
                json={
                    "name": "A's Project",
                    "topics": ["Machine Learning, Medical Imaging"],
                    "keywords": [],
                    "reading_level": "graduate",
                },
            )
            assert created.status_code == 201
            project_service.create_project.assert_awaited()
            assert (
                project_service.create_project.await_args.args[1] == user_a.id
            )

            listed = await client.get("/api/v1/projects", headers=headers)
            assert listed.status_code == 200
            assert len(listed.json()) == 1
            project_service.list_projects.assert_awaited_with(
                user_a.id, skip=0, limit=100
            )

            got = await client.get(
                f"/api/v1/projects/{project_owned_by_a.id}", headers=headers
            )
            assert got.status_code == 200
            project_service.get_project.assert_awaited_with(
                project_owned_by_a.id, user_a.id
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_user_b_cannot_access_user_a_project(
    user_a: User, user_b: User, project_owned_by_a: ProjectResponse
) -> None:
    from fastapi import HTTPException, status

    project_service = AsyncMock()
    project_service.list_projects.return_value = []

    async def _missing(*_args, **_kwargs):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    project_service.get_project.side_effect = _missing
    project_service.delete_project.side_effect = _missing

    ingestion = AsyncMock()
    ingestion.save_paper_to_project.side_effect = _missing
    ingestion.unsave_paper_from_project.side_effect = _missing
    ingestion.list_papers_for_project.side_effect = _missing

    ask = AsyncMock()
    ask.ask.side_effect = _missing

    app.dependency_overrides[get_current_user] = lambda: user_b
    app.dependency_overrides[get_project_service] = lambda: project_service
    app.dependency_overrides[get_ingestion_service] = lambda: ingestion
    app.dependency_overrides[get_ask_service] = lambda: ask

    transport = ASGITransport(app=app)
    headers = {"X-User-ID": str(user_b.id)}
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            listed = await client.get("/api/v1/projects", headers=headers)
            assert listed.status_code == 200
            assert listed.json() == []
            project_service.list_projects.assert_awaited_with(
                user_b.id, skip=0, limit=100
            )

            got = await client.get(
                f"/api/v1/projects/{project_owned_by_a.id}", headers=headers
            )
            assert got.status_code == 404

            save = await client.post(
                f"/api/v1/projects/{project_owned_by_a.id}/papers",
                headers=headers,
                json={
                    "paper": {
                        "title": "T",
                        "source": "arxiv",
                        "external_id": "x",
                        "authors": [],
                        "topics": [],
                    }
                },
            )
            assert save.status_code == 404

            unsave = await client.delete(
                f"/api/v1/projects/{project_owned_by_a.id}/papers/{uuid4()}",
                headers=headers,
            )
            assert unsave.status_code == 404

            ask_resp = await client.post(
                f"/api/v1/projects/{project_owned_by_a.id}/ask",
                headers=headers,
                json={"question": "What is this about?"},
            )
            assert ask_resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_user_a_can_save_and_ask(
    user_a: User, project_owned_by_a: ProjectResponse
) -> None:
    now = datetime.now(timezone.utc)
    paper = PaperResponse(
        id=uuid4(),
        source="arxiv",
        external_id="1",
        title="T",
        abstract=None,
        authors=[],
        year=None,
        url=None,
        pdf_url=None,
        topics=["ml"],
        created_at=now,
    )
    ingestion = AsyncMock()
    ingestion.save_paper_to_project.return_value = SavePaperResponse(
        paper=paper, already_saved=False
    )
    ask = AsyncMock()
    ask.ask.return_value = AskResponse(
        status="answered", answer="Because reasons.", citations=[]
    )

    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_ingestion_service] = lambda: ingestion
    app.dependency_overrides[get_ask_service] = lambda: ask

    transport = ASGITransport(app=app)
    headers = {"X-User-ID": str(user_a.id)}
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            save = await client.post(
                f"/api/v1/projects/{project_owned_by_a.id}/papers",
                headers=headers,
                json={
                    "paper": {
                        "title": "T",
                        "source": "arxiv",
                        "external_id": "1",
                        "authors": [],
                        "topics": ["ml"],
                    }
                },
            )
            assert save.status_code == 200
            assert ingestion.save_paper_to_project.await_args.args[2] == user_a.id

            ask_resp = await client.post(
                f"/api/v1/projects/{project_owned_by_a.id}/ask",
                headers=headers,
                json={"question": "Summarize?"},
            )
            assert ask_resp.status_code == 200
            assert ask.ask.await_args.kwargs["user_id"] == user_a.id
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_missing_user_header_returns_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/projects")
    assert response.status_code == 401
