"""Query normalization for discovery search.

Preserves technical punctuation and meaning. Does not stem, rewrite, or use an LLM.
"""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_query(raw_query: str) -> str:
    """Trim and collapse internal whitespace; reject empty/whitespace-only input.

    Raises:
        ValueError: when the query is empty after normalization.
    """
    if raw_query is None:
        raise ValueError("Query must not be empty")

    normalized = _WHITESPACE_RE.sub(" ", raw_query.strip())
    if not normalized:
        raise ValueError("Query must not be empty or whitespace-only")
    return normalized
