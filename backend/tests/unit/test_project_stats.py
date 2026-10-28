"""Server-side project statistics."""

from types import SimpleNamespace

from app.services.project_stats import (
    build_breakdown,
    build_recency,
    build_topics,
    compute_project_stats,
)


def _p(source="arxiv", year=2024, topics=(), authors=("A",)):
    return SimpleNamespace(
        source=source, year=year, topics=list(topics), authors=list(authors),
        citation_count=None, is_open_access=None, is_peer_reviewed=None,
    )


def test_breakdown_groups_top_two_plus_other() -> None:
    papers = [_p("arxiv")] * 3 + [_p("openalex")] * 2 + [_p("dblp"), _p("semantic_scholar")]
    items = build_breakdown(papers)
    assert [(i.name, i.count, i.percent) for i in items] == [
        ("arXiv", 3, 43),
        ("OpenAlex", 2, 29),
        ("Other", 2, 29),
    ]
    assert build_breakdown([]) == []


def test_recency_window_and_zero_years() -> None:
    stats = build_recency([_p(year=2020), _p(year=2024), _p(year=None)], present_year=2026)
    assert stats.start_year == 2020 and stats.present_year == 2026
    assert [b.count for b in stats.bars] == [1, 0, 0, 0, 1, 0, 0]
    assert stats.total == 2
    old = build_recency([_p(year=2001), _p(year=2025)], present_year=2026)
    assert old.start_year == 2001 and len(old.bars) == 26
    assert build_recency([_p(year=None)], 2026) is None


def test_topics_counted_once_per_paper_case_insensitive() -> None:
    papers = [_p(topics=["NLP", "nlp", "Vision"]), _p(topics=["nlp"])]
    assert [(t.topic, t.count) for t in build_topics(papers)] == [("NLP", 2), ("Vision", 1)]


def test_compute_project_stats_bundles_everything() -> None:
    stats = compute_project_stats([_p(authors=("A", "B"))], 2026)
    assert stats.total_sources == 1
    assert stats.validity.total_sources == 1
    assert stats.breakdown[0].percent == 100
