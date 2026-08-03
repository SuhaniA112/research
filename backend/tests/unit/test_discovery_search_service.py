"""Unit tests for DiscoverySearchService with mocked repositories and providers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.models.paper import Paper
from app.models.search_execution import SearchExecution
from app.models.search_topic import SearchTopic
from app.schemas.research_discovery import DiscoverySearchRequest
from app.schemas.research_papers import IndPaper
from app.services.discovery_search_service import DiscoverySearchService, _Candidate


def _settings(**overrides) -> Settings:
    base = {
        "app_env": "test",
        "search_cache_paper_similarity_threshold": 0.60,
        "search_cache_topic_similarity_threshold": 0.85,
        "search_cache_min_results": 3,
        "search_cache_max_age_days": 14,
        "search_default_limit": 5,
        "search_max_limit": 50,
        "search_candidate_multiplier": 2,
    }
    base.update(overrides)
    return Settings(**base)


def _paper(**kwargs) -> Paper:
    defaults = dict(
        id=uuid4(),
        source="arxiv",
        external_id=str(uuid4()),
        title="Example Paper",
        abstract="An abstract about contextual retrieval.",
        authors=["Author"],
        year=2024,
        url="https://example.com",
        pdf_url=None,
        topics=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Paper(**defaults)


def _topic(**kwargs) -> SearchTopic:
    defaults = dict(
        id=uuid4(),
        canonical_query="contextual retrieval",
        normalized_query="contextual retrieval",
        embedding=[0.1] * 1024,
        last_external_refresh_at=datetime.now(timezone.utc),
        external_refresh_count=1,
        last_result_count=10,
    )
    defaults.update(kwargs)
    return SearchTopic(**defaults)


def _execution(**kwargs) -> SearchExecution:
    defaults = dict(
        id=uuid4(),
        search_topic_id=uuid4(),
        raw_query="q",
        normalized_query="q",
        cache_hit=True,
        cache_miss_reason=None,
        external_search_performed=False,
        force_refresh=False,
        requested_limit=5,
        results_returned=0,
    )
    defaults.update(kwargs)
    return SearchExecution(**defaults)


class FakeProvider:
    def __init__(self, papers: list[IndPaper] | Exception):
        self._papers = papers

    async def search(self, query: str, max_results: int = 10) -> list[IndPaper]:
        if isinstance(self._papers, Exception):
            raise self._papers
        return self._papers[:max_results]


class ArxivClient(FakeProvider):
    pass


class OpenAlexClient(FakeProvider):
    pass


class SemanticScholarClient(FakeProvider):
    pass


class DblpClient(FakeProvider):
    pass


@pytest.fixture
def repos():
    paper_repo = AsyncMock()
    paper_repo.session = AsyncMock()
    paper_repo.session.flush = AsyncMock()
    chunk_repo = AsyncMock()
    topic_repo = AsyncMock()
    execution_repo = AsyncMock()
    topic_paper_repo = AsyncMock()
    return paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo


def _build_service(repos, voyage, settings, providers=None) -> DiscoverySearchService:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    return DiscoverySearchService(
        paper_repo=paper_repo,
        chunk_repo=chunk_repo,
        search_topic_repo=topic_repo,
        search_execution_repo=execution_repo,
        search_topic_paper_repo=topic_paper_repo,
        voyage_client=voyage,
        settings=settings,
        provider_clients=providers or [],
    )


@pytest.mark.asyncio
async def test_cache_hit_skips_external_providers(repos, mock_voyage) -> None:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    settings = _settings()
    topic = _topic()
    papers = [
        _paper(title=f"Paper {i}", abstract="contextual retrieval scholarly")
        for i in range(5)
    ]

    topic_repo.get_by_normalized_query.return_value = topic
    chunk_repo.search_global.return_value = [(p, 0.2) for p in papers]
    topic_paper_repo.list_papers_for_topic.return_value = []
    execution_repo.record.return_value = _execution(
        search_topic_id=topic.id, cache_hit=True
    )

    provider = ArxivClient(Exception("should not be called"))
    service = _build_service(repos, mock_voyage, settings, [provider])

    response = await service.search(
        DiscoverySearchRequest(query="contextual retrieval", limit=5)
    )

    assert response.cache_hit is True
    assert response.external_search_performed is False
    assert response.providers_attempted == []
    assert len(response.results) == 5
    assert all(r.result_origin == "database" for r in response.results)
    execution_repo.record.assert_awaited()


@pytest.mark.asyncio
async def test_exact_normalized_query_reuses_topic(repos, mock_voyage) -> None:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    settings = _settings(search_cache_min_results=1)
    topic = _topic()
    paper = _paper()

    topic_repo.get_by_normalized_query.return_value = topic
    chunk_repo.search_global.return_value = [(paper, 0.1)]
    topic_paper_repo.list_papers_for_topic.return_value = []
    # Force refresh so we don't care about cache sufficiency for this assertion.
    execution_repo.record.return_value = _execution(search_topic_id=topic.id)

    service = _build_service(repos, mock_voyage, settings, [])
    response = await service.search(
        DiscoverySearchRequest(query="  contextual   retrieval ", force_refresh=True)
    )

    assert response.topic_match_type == "exact"
    assert response.matched_topic_id == topic.id
    assert response.normalized_query == "contextual retrieval"
    topic_repo.get_or_create_by_normalized_query.assert_not_called()


@pytest.mark.asyncio
async def test_semantic_topic_reuse(repos, mock_voyage) -> None:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    settings = _settings(search_cache_min_results=1)
    topic = _topic(normalized_query="contextual retrieval for literature")

    topic_repo.get_by_normalized_query.return_value = None
    topic_repo.find_similar.return_value = [(topic, 0.05)]
    chunk_repo.search_global.return_value = [(_paper(), 0.1)]
    topic_paper_repo.list_papers_for_topic.return_value = []
    execution_repo.record.return_value = _execution(search_topic_id=topic.id)

    service = _build_service(repos, mock_voyage, settings, [])
    response = await service.search(
        DiscoverySearchRequest(
            query="contextual literature retrieval", force_refresh=True
        )
    )

    assert response.topic_match_type == "semantic"
    assert response.matched_topic_id == topic.id
    topic_repo.get_or_create_by_normalized_query.assert_not_called()


@pytest.mark.asyncio
async def test_force_refresh_calls_providers(repos, mock_voyage) -> None:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    settings = _settings(search_cache_min_results=1)
    topic = _topic()
    papers = [_paper() for _ in range(5)]

    topic_repo.get_by_normalized_query.return_value = topic
    chunk_repo.search_global.return_value = [(p, 0.1) for p in papers]
    topic_paper_repo.list_papers_for_topic.return_value = []
    topic_repo.mark_external_refresh.return_value = topic
    execution_repo.record.return_value = _execution(
        search_topic_id=topic.id, cache_hit=False
    )

    ind = IndPaper(
        title="New Ext Paper",
        abstract="abstract",
        authors=["A"],
        year=2023,
        source="arxiv",
        external_id="ext-1",
    )
    paper_repo.upsert_from_ind_paper.return_value = (_paper(title=ind.title), True)
    chunk_repo.get_for_paper.return_value = None
    chunk_repo.ensure_chunk_for_paper.return_value = (MagicMock(), True)
    topic_paper_repo.upsert_association.return_value = (MagicMock(), True)

    provider = ArxivClient([ind])

    service = _build_service(repos, mock_voyage, settings, [provider])
    response = await service.search(
        DiscoverySearchRequest(
            query="contextual retrieval", limit=5, force_refresh=True
        )
    )

    assert response.cache_hit is False
    assert response.cache_miss_reason == "force_refresh"
    assert response.external_search_performed is True
    assert "arxiv" in response.providers_attempted
    assert "arxiv" in response.providers_succeeded


@pytest.mark.asyncio
async def test_low_similarity_triggers_fallback(repos, mock_voyage) -> None:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    settings = _settings(
        search_cache_min_results=1, search_cache_paper_similarity_threshold=0.9
    )
    topic = _topic()

    topic_repo.get_by_normalized_query.return_value = topic
    # distance 0.5 → similarity 0.5 < 0.9
    chunk_repo.search_global.return_value = [(_paper(), 0.5)]
    topic_paper_repo.list_papers_for_topic.return_value = []
    topic_repo.mark_external_refresh.return_value = topic
    execution_repo.record.return_value = _execution(search_topic_id=topic.id)
    paper_repo.upsert_from_ind_paper.return_value = (_paper(), False)
    # Matching abstract avoids a re-embed path in the service.
    chunk_repo.get_for_paper.return_value = MagicMock(text="a")
    topic_paper_repo.upsert_association.return_value = (MagicMock(), False)

    ind = IndPaper(
        title="P", abstract="a", authors=[], year=2020, source="arxiv", external_id="1"
    )
    provider = ArxivClient([ind])

    service = _build_service(repos, mock_voyage, settings, [provider])
    response = await service.search(
        DiscoverySearchRequest(query="contextual retrieval", limit=5)
    )

    assert response.cache_hit is False
    assert response.cache_miss_reason == "low_similarity"
    assert response.external_search_performed is True


@pytest.mark.asyncio
async def test_stale_topic_triggers_refresh(repos, mock_voyage) -> None:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    settings = _settings(search_cache_min_results=1, search_cache_max_age_days=7)
    topic = _topic(
        last_external_refresh_at=datetime.now(timezone.utc) - timedelta(days=30)
    )
    papers = [_paper() for _ in range(5)]

    topic_repo.get_by_normalized_query.return_value = topic
    chunk_repo.search_global.return_value = [(p, 0.1) for p in papers]
    topic_paper_repo.list_papers_for_topic.return_value = []
    topic_repo.mark_external_refresh.return_value = topic
    execution_repo.record.return_value = _execution(search_topic_id=topic.id)
    paper_repo.upsert_from_ind_paper.return_value = (papers[0], False)
    chunk_repo.get_for_paper.return_value = MagicMock(text="a")
    topic_paper_repo.upsert_association.return_value = (MagicMock(), False)

    ind = IndPaper(
        title="P", abstract="a", authors=[], year=2020, source="arxiv", external_id="1"
    )
    provider = ArxivClient([ind])

    service = _build_service(repos, mock_voyage, settings, [provider])
    response = await service.search(
        DiscoverySearchRequest(query="contextual retrieval", limit=5)
    )

    assert response.cache_miss_reason == "stale_topic"
    assert response.external_search_performed is True


@pytest.mark.asyncio
async def test_insufficient_results_triggers_fallback(repos, mock_voyage) -> None:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    settings = _settings(search_cache_min_results=5)
    topic = _topic()

    topic_repo.get_by_normalized_query.return_value = topic
    chunk_repo.search_global.return_value = [(_paper(), 0.1), (_paper(), 0.15)]
    topic_paper_repo.list_papers_for_topic.return_value = []
    topic_repo.mark_external_refresh.return_value = topic
    execution_repo.record.return_value = _execution(search_topic_id=topic.id)
    paper_repo.upsert_from_ind_paper.return_value = (_paper(), True)
    chunk_repo.get_for_paper.return_value = None
    chunk_repo.ensure_chunk_for_paper.return_value = (MagicMock(), True)
    topic_paper_repo.upsert_association.return_value = (MagicMock(), True)

    ind = IndPaper(
        title="P", abstract="a", authors=[], year=2020, source="arxiv", external_id="1"
    )
    provider = ArxivClient([ind])

    service = _build_service(repos, mock_voyage, settings, [provider])
    response = await service.search(
        DiscoverySearchRequest(query="contextual retrieval", limit=5)
    )

    assert response.cache_miss_reason == "insufficient_results"


@pytest.mark.asyncio
async def test_provider_failure_does_not_abort_others(repos, mock_voyage) -> None:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    settings = _settings()
    topic = _topic(last_external_refresh_at=None)

    topic_repo.get_by_normalized_query.return_value = None
    topic_repo.find_similar.return_value = []
    topic_repo.get_or_create_by_normalized_query.return_value = (topic, True)
    chunk_repo.search_global.return_value = []
    topic_paper_repo.list_papers_for_topic.return_value = []
    topic_repo.mark_external_refresh.return_value = topic
    execution_repo.record.return_value = _execution(search_topic_id=topic.id)

    good = IndPaper(
        title="Good",
        abstract="a",
        authors=[],
        year=2020,
        source="arxiv",
        external_id="g1",
    )
    paper_repo.upsert_from_ind_paper.return_value = (_paper(title="Good"), True)
    chunk_repo.get_for_paper.return_value = None
    chunk_repo.ensure_chunk_for_paper.return_value = (MagicMock(), True)
    topic_paper_repo.upsert_association.return_value = (MagicMock(), True)

    failing = OpenAlexClient(RuntimeError("timeout"))
    succeeding = ArxivClient([good])

    service = _build_service(repos, mock_voyage, settings, [failing, succeeding])
    response = await service.search(
        DiscoverySearchRequest(query="brand new obscure topic xyz", limit=5)
    )

    assert response.external_search_performed is True
    assert "arxiv" in response.providers_succeeded
    assert any(f.provider == "openalex" for f in response.providers_failed)
    assert len(response.results) >= 1


@pytest.mark.asyncio
async def test_repeated_searches_create_separate_executions(repos, mock_voyage) -> None:
    paper_repo, chunk_repo, topic_repo, execution_repo, topic_paper_repo = repos
    settings = _settings(search_cache_min_results=1)
    topic = _topic()
    paper = _paper()

    topic_repo.get_by_normalized_query.return_value = topic
    chunk_repo.search_global.return_value = [(paper, 0.1)]
    topic_paper_repo.list_papers_for_topic.return_value = []
    execution_repo.record.side_effect = [
        _execution(id=uuid4(), search_topic_id=topic.id),
        _execution(id=uuid4(), search_topic_id=topic.id),
    ]

    service = _build_service(repos, mock_voyage, settings, [])
    r1 = await service.search(
        DiscoverySearchRequest(
            query="contextual retrieval", limit=1, force_refresh=True
        )
    )
    r2 = await service.search(
        DiscoverySearchRequest(
            query="contextual retrieval", limit=1, force_refresh=True
        )
    )

    assert r1.search_execution_id != r2.search_execution_id
    assert execution_repo.record.await_count == 2
    assert topic_repo.get_or_create_by_normalized_query.await_count == 0


class TestCacheEvaluationHelpers:
    def test_force_refresh_reason(self) -> None:
        service = DiscoverySearchService(
            paper_repo=AsyncMock(),
            chunk_repo=AsyncMock(),
            search_topic_repo=AsyncMock(),
            search_execution_repo=AsyncMock(),
            search_topic_paper_repo=AsyncMock(),
            voyage_client=AsyncMock(),
            settings=_settings(),
            provider_clients=[],
        )
        hit, reason = service._evaluate_cache(
            topic=_topic(),
            topic_match_type="exact",
            candidates=[
                _Candidate(paper=_paper(), similarity_score=0.9, origins={"database"})
            ],
            limit=5,
            force_refresh=True,
        )
        assert hit is False
        assert reason == "force_refresh"

    def test_ranking_is_deterministic(self) -> None:
        p1 = _paper(title="Alpha")
        p2 = _paper(title="Beta")
        candidates = [
            _Candidate(
                paper=p2, similarity_score=0.8, provider_rank=2, origins={"external"}
            ),
            _Candidate(
                paper=p1, similarity_score=0.8, provider_rank=1, origins={"external"}
            ),
        ]
        ranked = DiscoverySearchService._rank_candidates(candidates)
        assert ranked[0].paper.title == "Alpha"
