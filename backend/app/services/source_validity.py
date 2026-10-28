"""Source Validity percentages over a project's saved papers.

Each metric counts only papers whose provider reported the field; no data -> None.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol

from app.schemas.stats import SourceValidityMetric, SourceValidityResponse

# A paper cited at least this many times counts as "cross-cited".
CROSS_CITED_MIN_CITATIONS = 1


class _PaperLike(Protocol):
    authors: list[str] | None
    citation_count: int | None
    is_open_access: bool | None
    is_peer_reviewed: bool | None


def _metric(
    key: str,
    label: str,
    papers: list[Any],
    known: Callable[[Any], bool],
    passes: Callable[[Any], bool],
) -> SourceValidityMetric:
    known_papers = [p for p in papers if known(p)]
    count = sum(1 for p in known_papers if passes(p))
    percent = (
        round(100 * count / len(known_papers)) if known_papers else None
    )
    return SourceValidityMetric(
        key=key,
        label=label,
        percent=percent,
        count=count,
        known=len(known_papers),
    )


def status_label(score: int | None, total: int) -> str:
    if total == 0:
        return "NO SOURCES YET"
    if score is None:
        return "NOT ENOUGH DATA"
    if score >= 75:
        return "HIGHLY CONNECTED"
    if score >= 50:
        return "WELL SUPPORTED"
    if score >= 25:
        return "MIXED SUPPORT"
    return "NEEDS STRONGER SOURCES"


def compute_source_validity(papers: Iterable[_PaperLike]) -> SourceValidityResponse:
    papers = list(papers)
    metrics = [
        _metric(
            "cross_cited",
            "Cross-cited",
            papers,
            known=lambda p: p.citation_count is not None,
            passes=lambda p: p.citation_count >= CROSS_CITED_MIN_CITATIONS,
        ),
        _metric(
            "peer_reviewed",
            "Peer-reviewed",
            papers,
            known=lambda p: p.is_peer_reviewed is not None,
            passes=lambda p: p.is_peer_reviewed is True,
        ),
        _metric(
            "open_access",
            "Open access",
            papers,
            known=lambda p: p.is_open_access is not None,
            passes=lambda p: p.is_open_access is True,
        ),
        _metric(
            "multi_author",
            "Multi-author",
            papers,
            known=lambda p: bool(p.authors),
            passes=lambda p: len(p.authors) >= 2,
        ),
    ]

    available = [m.percent for m in metrics if m.percent is not None]
    score = round(sum(available) / len(available)) if available else None

    return SourceValidityResponse(
        score=score,
        status=status_label(score, len(papers)),
        total_sources=len(papers),
        metrics=metrics,
    )
