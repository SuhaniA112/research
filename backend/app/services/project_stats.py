"""Project statistics computed server-side from saved papers (pure, no I/O)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from app.schemas.stats import (
    BreakdownItem,
    ProjectStatsResponse,
    RecencyBar,
    RecencyStats,
    TopicCount,
)
from app.services.source_validity import compute_source_validity

PROVIDER_LABELS = {
    "arxiv": "arXiv",
    "openalex": "OpenAlex",
    "semantic_scholar": "Semantic Scholar",
    "dblp": "DBLP",
}
TOP_TOPICS = 8


def provider_label(source: str | None) -> str:
    raw = (source or "").strip()
    return PROVIDER_LABELS.get(raw.lower(), raw) if raw else "Unknown"


def build_breakdown(papers: list) -> list[BreakdownItem]:
    """Top two providers by count plus Other, as rounded percentages."""
    if not papers:
        return []
    counts = Counter(provider_label(p.source) for p in papers)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    groups = ranked[:2]
    other = sum(n for _, n in ranked[2:])
    if other:
        groups.append(("Other", other))
    groups.sort(key=lambda kv: (-kv[1], kv[0]))
    total = len(papers)
    return [BreakdownItem(name=n, count=c, percent=round(100 * c / total)) for n, c in groups]


def build_recency(papers: list, present_year: int) -> RecencyStats | None:
    """Papers per publication year, from the earliest saved year to now."""
    years = sorted(p.year for p in papers if p.year and 1900 <= p.year <= 2100)
    if not years:
        return None
    end = max(years[-1], present_year)
    start = years[0]
    counts = Counter(y for y in years if start <= y <= end)
    return RecencyStats(
        bars=[RecencyBar(year=y, count=counts.get(y, 0)) for y in range(start, end + 1)],
        earliest_year=years[0],
        total=len(years),
        start_year=start,
        present_year=present_year,
    )


def build_topics(papers: list) -> list[TopicCount]:
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    for p in papers:
        seen: set[str] = set()
        for t in (t.strip() for t in (p.topics or []) if t and t.strip()):
            key = t.casefold()
            if key in seen:
                continue
            seen.add(key)
            display.setdefault(key, t)
            counts[key] += 1
    return [
        TopicCount(topic=display[k], count=n)
        for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_TOPICS]
    ]


def compute_project_stats(papers: Iterable, present_year: int) -> ProjectStatsResponse:
    papers = list(papers)
    return ProjectStatsResponse(
        total_sources=len(papers),
        breakdown=build_breakdown(papers),
        recency=build_recency(papers, present_year),
        validity=compute_source_validity(papers),
        topics=build_topics(papers),
    )
