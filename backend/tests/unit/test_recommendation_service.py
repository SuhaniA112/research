"""RecommendationService with mocked repositories."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.recommendation import service as svc
from app.services.recommendation.service import RecommendationService, collect_interests

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _paper(title: str, topics=()):
    return SimpleNamespace(
        id=uuid4(), source="arxiv", external_id=title, title=title, abstract=None,
        authors=[], year=2024, url=None, pdf_url=None, topics=list(topics),
        source_categories=[], created_at=NOW,
    )


@pytest.fixture(autouse=True)
def _clear():
    svc.clear_caches()
    yield
    svc.clear_caches()


def _service(papers, vectors, *, saved=(), interests=("vision", "nlp"), api_key="k"):
    by_id = {p.id: p for p in papers}
    profile_repo = AsyncMock()
    profile_repo.ensure_for_user.return_value = SimpleNamespace(
        research_areas=list(interests), keywords=[]
    )
    project_repo = AsyncMock()
    project_repo.list_for_user.return_value = []
    pp_repo = AsyncMock()
    pp_repo.list_papers_for_user.return_value = list(saved)
    pp_repo.list_papers_for_project.return_value = list(saved)
    chunk_repo = AsyncMock()
    chunk_repo.search_global.side_effect = lambda q, **kw: [(p, 0.2) for p in papers]
    chunk_repo.get_for_papers.side_effect = lambda ids, **kw: {
        i: SimpleNamespace(embedding=vectors[i]) for i in ids if i in vectors
    }
    paper_repo = AsyncMock()
    paper_repo.get_many.side_effect = lambda ids: {i: by_id[i] for i in ids if i in by_id}
    paper_repo.find_by_topic_overlap.return_value = [(papers[0], 1)]
    paper_repo.list_recent.side_effect = lambda exclude, limit: [
        p for p in papers if p.id not in exclude
    ][:limit]
    voyage = AsyncMock()
    voyage.api_key = api_key
    voyage.model = "m"
    voyage.embed.side_effect = lambda texts, **kw: [
        [1.0, 0.0, 0.0] if t == "vision" else [0.0, 1.0, 0.0] for t in texts
    ]
    service = RecommendationService(profile_repo, project_repo, pp_repo, chunk_repo, paper_repo, voyage)
    return service, voyage, chunk_repo


def test_collect_interests_dedupes_case_insensitively() -> None:
    projects = [SimpleNamespace(topics=["Vision", "Robotics"], keywords=["nlp"])]
    assert collect_interests(["vision"], ["NLP"], projects) == ["vision", "NLP", "Robotics"]


@pytest.mark.asyncio
async def test_digest_ranks_excludes_saved_and_pages() -> None:
    a, b, c, saved = _paper("a"), _paper("b"), _paper("c"), _paper("saved")
    vectors = {a.id: [1, 0, 0], b.id: [0, 1, 0], c.id: [0.7, 0.7, 0], saved.id: [1, 0, 0]}
    service, voyage, _ = _service([a, b, c, saved], vectors, saved=[saved])
    user = SimpleNamespace(id=uuid4())

    first = await service.digest(user, limit=2)
    ids = [item.paper.id for item in first.items]
    assert saved.id not in ids
    assert first.method == "embedding"
    assert first.total == 3 and first.has_more
    assert first.items[0].relevance == 100
    assert first.items[0].similarity is not None

    second = await service.digest(user, limit=2, offset=2)
    assert len(second.items) == 1 and not second.has_more
    assert voyage.embed.await_count == 1  # cached between pages


@pytest.mark.asyncio
async def test_digest_falls_back_to_topics_without_key() -> None:
    a = _paper("a", topics=["vision"])
    service, voyage, _ = _service([a], {}, api_key="")
    result = await service.digest(SimpleNamespace(id=uuid4()))
    assert result.method == "lexical"
    assert result.items[0].matched_interest == "vision"
    voyage.embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_digest_without_interests_shows_recent_papers() -> None:
    a, saved = _paper("a"), _paper("saved")
    service, voyage, _ = _service([a, saved], {}, saved=[saved], interests=())
    result = await service.digest(SimpleNamespace(id=uuid4()))
    assert result.method == "recent"
    assert [i.paper.id for i in result.items] == [a.id]
    assert result.sparse is False  # nothing to search for without interests
    voyage.embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_digest_cold_start_ranks_by_saved_papers() -> None:
    near, far, saved = _paper("near"), _paper("far"), _paper("saved")
    vectors = {near.id: [1, 0, 0], far.id: [0, 1, 0], saved.id: [1, 0, 0]}
    service, voyage, _ = _service([near, far, saved], vectors, saved=[saved], interests=())
    result = await service.digest(SimpleNamespace(id=uuid4()))
    assert result.method == "embedding"
    assert [i.paper.id for i in result.items][0] == near.id
    assert result.items[0].relevance == 100 and result.items[0].similarity == 100
    assert result.items[0].matched_interest is None
    voyage.embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_related_skips_the_paper_itself() -> None:
    a, b = _paper("a"), _paper("b")
    service, _, _ = _service([a, b], {a.id: [1, 0, 0], b.id: [0.9, 0.1, 0]})
    related = await service.related(a.id, limit=3)
    assert [r.paper.id for r in related] == [b.id]
    assert related[0].relevance == 80


@pytest.mark.asyncio
async def test_similarity_to_saved_ignores_self_match() -> None:
    a, s = _paper("a"), _paper("s")
    service, _, _ = _service([a, s], {a.id: [1, 0, 0], s.id: [1, 0, 0]}, saved=[s])
    scores = await service.similarity_to_saved(uuid4(), [a.id, s.id])
    assert scores[str(a.id)] == 100
    assert scores[str(s.id)] is None
