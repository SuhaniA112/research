"""API/unit coverage for project-aware discovery intent resolution."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_discovery_search_service
from app.core.config import Settings
from app.main import app
from app.models.project import Project
from app.models.search_execution import SearchExecution
from app.models.search_topic import SearchTopic
from app.models.user import User
from app.schemas.research_discovery import (
    DiscoverySearchRequest,
    DiscoverySearchResponse,
)
from app.services.discovery_search_service import DiscoverySearchService


def _settings() -> Settings:
    return Settings(
        app_env="test",
        search_cache_min_results=1,
        search_default_limit=5,
        search_ann_candidate_multiplier=10,
    )


def _user() -> User:
    return User(
        id=uuid4(),
        email="disc@example.com",
        full_name="Disc",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def override_discovery_service():
    service = AsyncMock()

    async def _search(body, **kwargs):
        return DiscoverySearchResponse(
            query=body.query or "Machine Learning",
            normalized_query=(body.query or "machine learning").strip().casefold(),
            search_execution_id=uuid4(),
            matched_topic_id=uuid4(),
            topic_match_type="new",
            cache_hit=False,
            cache_miss_reason="no_matching_topic",
            external_search_performed=True,
            providers_attempted=[],
            providers_succeeded=[],
            providers_failed=[],
            results=[],
        )

    service.search.side_effect = _search
    user = _user()
    app.dependency_overrides[get_discovery_search_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: user
    yield service, user
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_endpoint_requires_user(override_discovery_service) -> None:
    service, user = override_discovery_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/research/search",
            headers={"X-User-ID": str(user.id)},
            json={"query": "contextual retrieval", "limit": 10},
        )
    assert response.status_code == 200
    service.search.assert_awaited()
    assert service.search.await_args.kwargs["user_id"] == user.id
    payload = response.json()
    assert "user_id" not in payload
    assert "project_id" not in payload


@pytest.mark.asyncio
async def test_empty_query_with_project_id_is_accepted(
    override_discovery_service,
) -> None:
    service, user = override_discovery_service
    project_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/research/search",
            headers={"X-User-ID": str(user.id)},
            json={"query": "", "project_id": str(project_id), "limit": 10},
        )
    assert response.status_code == 200
    body = service.search.await_args.args[0]
    assert body.project_id == project_id
    assert body.query == ""


@pytest.mark.asyncio
async def test_resolve_empty_query_uses_project_topics(mock_voyage) -> None:
    user_id = uuid4()
    project = Project(
        id=uuid4(),
        user_id=user_id,
        name="P",
        topics=["Machine Learning", "Medical Imaging"],
        keywords=["Cancer Detection"],
        reading_level="graduate",
    )
    project_repo = AsyncMock()
    project_repo.get_for_user.return_value = project

    paper_repo = AsyncMock()
    paper_repo.session = AsyncMock()
    chunk_repo = AsyncMock()
    chunk_repo.search_global.return_value = []
    topic_repo = AsyncMock()
    topic = SearchTopic(
        id=uuid4(),
        canonical_query="Machine Learning, Medical Imaging, Cancer Detection",
        normalized_query="machine learning, medical imaging, cancer detection",
        embedding=[0.1] * 1024,
        last_external_refresh_at=None,
        external_refresh_count=0,
        last_result_count=0,
    )
    topic_repo.get_by_normalized_query.return_value = None
    topic_repo.find_similar.return_value = []
    topic_repo.get_or_create_by_normalized_query.return_value = (topic, True)
    topic_paper_repo = AsyncMock()
    topic_paper_repo.list_papers_for_topic.return_value = []
    execution_repo = AsyncMock()
    execution_repo.record.return_value = SearchExecution(
        id=uuid4(),
        search_topic_id=topic.id,
        raw_query="Machine Learning, Medical Imaging, Cancer Detection",
        normalized_query="machine learning, medical imaging, cancer detection",
        cache_hit=False,
        cache_miss_reason="no_matching_topic",
        external_search_performed=True,
        force_refresh=False,
        requested_limit=5,
        results_returned=0,
    )

    service = DiscoverySearchService(
        paper_repo=paper_repo,
        chunk_repo=chunk_repo,
        search_topic_repo=topic_repo,
        search_execution_repo=execution_repo,
        search_topic_paper_repo=topic_paper_repo,
        project_repo=project_repo,
        profile_repo=None,
        voyage_client=mock_voyage,
        settings=_settings(),
        provider_clients=[],
    )

    response = await service.search(
        DiscoverySearchRequest(query="", project_id=project.id, limit=5),
        user_id=user_id,
    )
    assert response.query == "Machine Learning, Medical Imaging, Cancer Detection"
    assert response.normalized_query == (
        "machine learning, medical imaging, cancer detection"
    )
    project_repo.get_for_user.assert_awaited_with(project.id, user_id)


@pytest.mark.asyncio
async def test_resolve_empty_query_project_ownership(mock_voyage) -> None:
    project_repo = AsyncMock()
    project_repo.get_for_user.return_value = None
    service = DiscoverySearchService(
        paper_repo=AsyncMock(),
        chunk_repo=AsyncMock(),
        search_topic_repo=AsyncMock(),
        search_execution_repo=AsyncMock(),
        search_topic_paper_repo=AsyncMock(),
        project_repo=project_repo,
        profile_repo=None,
        voyage_client=mock_voyage,
        settings=_settings(),
        provider_clients=[],
    )
    with pytest.raises(HTTPException) as exc:
        await service.search(
            DiscoverySearchRequest(query="", project_id=uuid4()),
            user_id=uuid4(),
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_empty_query_no_context_returns_422(mock_voyage) -> None:
    profile = MagicMock()
    profile.research_areas = []
    profile.keywords = []
    profile_repo = AsyncMock()
    profile_repo.ensure_singleton.return_value = profile

    service = DiscoverySearchService(
        paper_repo=AsyncMock(),
        chunk_repo=AsyncMock(),
        search_topic_repo=AsyncMock(),
        search_execution_repo=AsyncMock(),
        search_topic_paper_repo=AsyncMock(),
        project_repo=None,
        profile_repo=profile_repo,
        voyage_client=mock_voyage,
        settings=_settings(),
        provider_clients=[],
    )
    with pytest.raises(HTTPException) as exc:
        await service.search(DiscoverySearchRequest(query=""), user_id=uuid4())
    assert exc.value.status_code == 422
    assert "research" not in str(exc.value.detail).lower() or "must not" in str(
        exc.value.detail
    ).lower()


@pytest.mark.asyncio
async def test_explicit_query_ignores_project_concatenation(mock_voyage) -> None:
    user_id = uuid4()
    project = Project(
        id=uuid4(),
        user_id=user_id,
        name="P",
        topics=["Should Not Appear"],
        keywords=[],
        reading_level="graduate",
    )
    project_repo = AsyncMock()
    project_repo.get_for_user.return_value = project

    paper_repo = AsyncMock()
    paper_repo.session = AsyncMock()
    chunk_repo = AsyncMock()
    chunk_repo.search_global.return_value = []
    topic_repo = AsyncMock()
    topic = SearchTopic(
        id=uuid4(),
        canonical_query="graphs",
        normalized_query="graphs",
        embedding=[0.1] * 1024,
        last_external_refresh_at=None,
        external_refresh_count=0,
        last_result_count=0,
    )
    topic_repo.get_by_normalized_query.return_value = None
    topic_repo.find_similar.return_value = []
    topic_repo.get_or_create_by_normalized_query.return_value = (topic, True)
    topic_paper_repo = AsyncMock()
    topic_paper_repo.list_papers_for_topic.return_value = []
    execution_repo = AsyncMock()
    execution_repo.record.return_value = SearchExecution(
        id=uuid4(),
        search_topic_id=topic.id,
        raw_query="graphs",
        normalized_query="graphs",
        cache_hit=False,
        cache_miss_reason="no_matching_topic",
        external_search_performed=True,
        force_refresh=False,
        requested_limit=5,
        results_returned=0,
    )

    service = DiscoverySearchService(
        paper_repo=paper_repo,
        chunk_repo=chunk_repo,
        search_topic_repo=topic_repo,
        search_execution_repo=execution_repo,
        search_topic_paper_repo=topic_paper_repo,
        project_repo=project_repo,
        profile_repo=None,
        voyage_client=mock_voyage,
        settings=_settings(),
        provider_clients=[],
    )
    response = await service.search(
        DiscoverySearchRequest(query="graphs", project_id=project.id, limit=5),
        user_id=user_id,
    )
    assert response.query == "graphs"
    assert response.normalized_query == "graphs"
    project_repo.get_for_user.assert_not_awaited()
