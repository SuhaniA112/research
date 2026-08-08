"""Query and topic normalization for discovery, projects, profiles, and papers.

SearchTopic / cache matching uses the full normalized query string (one intent).
Paper/project/profile topic arrays use split+deduped topic lists.

Does not stem, rewrite, LLM-normalize, or split on the word "and".
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
# Collapse spaces around harmless list delimiters without removing the delimiter.
_DELIMITER_SPACE_RE = re.compile(r"\s*([,;|])\s*")
_TOPIC_SPLIT_RE = re.compile(r"[,;\n|]+")


def normalize_query(raw_query: str) -> str:
    """Normalize a search/cache query string.

    - strips leading/trailing whitespace
    - collapses repeated whitespace
    - applies Unicode NFKC
    - casefolds for stable matching
    - normalizes harmless delimiter spacing (e.g. ``a , b`` → ``a, b``)
    - preserves scientifically meaningful punctuation/characters

    Raises:
        ValueError: when the query is empty after normalization.
    """
    if raw_query is None:
        raise ValueError("Query must not be empty")

    text = unicodedata.normalize("NFKC", raw_query)
    text = _WHITESPACE_RE.sub(" ", text.strip())
    text = _DELIMITER_SPACE_RE.sub(r"\1 ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    # Trailing delimiter spacing can leave a trailing space before strip; also
    # avoid a dangling space after a trailing delimiter: "a, b," → "a, b,"
    text = text.casefold()
    if not text:
        raise ValueError("Query must not be empty or whitespace-only")
    return text


def normalize_topic_list(topics: list[str] | None) -> list[str]:
    """Split, clean, and case-insensitively dedupe topic/keyword strings.

    Splits each entry on comma, semicolon, newline, or pipe. Does **not** split
    on the word ``and``. Preserves a readable first-occurrence form (casing and
    scientifically meaningful punctuation).
    """
    if not topics:
        return []

    result: list[str] = []
    seen: set[str] = set()

    for item in topics:
        if item is None:
            continue
        if not isinstance(item, str):
            item = str(item)

        for part in _TOPIC_SPLIT_RE.split(item):
            readable = _readable_topic(part)
            if not readable:
                continue
            key = readable.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(readable)

    return result


def merge_topic_lists(*topic_lists: list[str] | None) -> list[str]:
    """Merge multiple topic lists, then normalize and dedupe."""
    combined: list[str] = []
    for topics in topic_lists:
        if topics:
            combined.extend(topics)
    return normalize_topic_list(combined)


def build_intent_query_from_topics(
    topics: list[str] | None,
    keywords: list[str] | None = None,
) -> str | None:
    """Build a human-readable discovery intent from topics/keywords, or None."""
    combined = merge_topic_lists(topics, keywords)
    if not combined:
        return None
    return ", ".join(combined)


def _readable_topic(raw: str) -> str:
    text = unicodedata.normalize("NFKC", raw)
    text = _WHITESPACE_RE.sub(" ", text.strip())
    return text
