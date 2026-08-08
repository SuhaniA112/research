"""API validation and discovery endpoint tests with dependency overrides."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_discovery_search_service
from app.main import app
from app.models.user import User
from app.schemas.research_discovery import DiscoverySearchResponse


@pytest.fixture
def override_discovery_service():
    service = AsyncMock()
    user = User(
        id=uuid4(),
        email="search@example.com",
        full_name="Searcher",
        hashed_password="x",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    async def _search(body, **kwargs):
        return DiscoverySearchResponse(
            query=body.query,
            normalized_query=(body.query or "").strip().casefold() or "fallback",
            search_execution_id=uuid4(),
            matched_topic_id=uuid4(),
            topic_match_type="new",
            cache_hit=False,
            cache_miss_reason="no_matching_topic",
            external_search_performed=True,
            providers_attempted=["arxiv"],
            providers_succeeded=["arxiv"],
            providers_failed=[],
            results=[],
        )

    service.search.side_effect = _search
    app.dependency_overrides[get_discovery_search_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: user
    yield service, user
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_missing_auth_returns_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/research/search", json={"query": "graphs"}
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_limit_returns_422(override_discovery_service) -> None:
    _, user = override_discovery_service
    headers = {"X-User-ID": str(user.id)}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/research/search",
            headers=headers,
            json={"query": "graphs", "limit": 0},
        )
    assert response.status_code == 422

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/research/search",
            headers=headers,
            json={"query": "graphs", "limit": 999},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_success(override_discovery_service) -> None:
    _, user = override_discovery_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/research/search",
            headers={"X-User-ID": str(user.id)},
            json={"query": "contextual retrieval", "limit": 10, "force_refresh": False},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "contextual retrieval"
    assert payload["external_search_performed"] is True
    assert "results" in payload
    # Privacy: response must not expose user/project fields.
    assert "user_id" not in payload
    assert "project" not in payload
    assert "project_id" not in payload
