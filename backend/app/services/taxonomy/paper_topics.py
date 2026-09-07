"""Separate search intent, source taxonomy, and user-facing paper topics."""

from __future__ import annotations

from app.services.query_normalization import merge_topic_lists, normalize_topic_list
from app.services.taxonomy.arxiv_categories import (
    is_arxiv_category_code,
    map_arxiv_categories_to_topics,
    normalize_arxiv_category,
)

# Historical discovery queries that were incorrectly copied into Paper.topics.
# Match case-insensitively; never treat these as paper-owned topics.
KNOWN_QUERY_CONTAMINANTS: frozenset[str] = frozenset(
    {
        "computer vision medical imaging",
        "machine learning and detection of medical conditions",
        "artificial intelligence in healthcare",
    }
)


def is_known_query_contaminant(value: str) -> bool:
    text = (value or "").strip().casefold()
    return bool(text) and text in KNOWN_QUERY_CONTAMINANTS


def normalize_source_categories(categories: list[str] | None) -> list[str]:
    """Normalize and dedupe raw provider taxonomy codes (preserve codes, not labels)."""
    if not categories:
        return []

    result: list[str] = []
    seen: set[str] = set()
    for item in categories:
        if item is None:
            continue
        if not isinstance(item, str):
            item = str(item)
        raw = item.strip()
        if not raw:
            continue
        code = normalize_arxiv_category(raw) if is_arxiv_category_code(raw) else raw
        key = code.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(code)
    return result


def build_paper_topics(
    *,
    source_categories: list[str] | None = None,
    provider_topics: list[str] | None = None,
) -> list[str]:
    """Build user-facing topics from taxonomy mappings + provider-native labels.

    Ordering:
      1. broad mapped domains / taxonomy topics
      2. provider-native semantic topics (OpenAlex, S2, etc.)

    Does not accept search queries. Filters raw category codes and known
    query contaminants out of ``provider_topics``.
    """
    categories = normalize_source_categories(source_categories)
    mapped = map_arxiv_categories_to_topics(categories)

    native: list[str] = []
    for topic in normalize_topic_list(provider_topics):
        if is_arxiv_category_code(topic):
            continue
        if is_known_query_contaminant(topic):
            continue
        native.append(topic)

    return merge_topic_lists(mapped, native)


def sanitize_persisted_topic_fields(
    topics: list[str] | None,
    source_categories: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Clean a persisted Paper row's topics / source_categories.

    - Moves arXiv-like codes from topics into source_categories
    - Drops known search-query contaminants
    - Rebuilds display topics from categories + remaining provider labels

    Returns ``(clean_topics, clean_source_categories)``.
    """
    existing_topics = list(topics or [])
    existing_categories = list(source_categories or [])

    extracted_categories: list[str] = []
    remaining_provider_topics: list[str] = []

    for item in existing_topics:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        if is_known_query_contaminant(text):
            continue
        if is_arxiv_category_code(text):
            extracted_categories.append(text)
            continue
        remaining_provider_topics.append(text)

    clean_categories = normalize_source_categories(
        [*existing_categories, *extracted_categories]
    )
    clean_topics = build_paper_topics(
        source_categories=clean_categories,
        provider_topics=remaining_provider_topics,
    )
    return clean_topics, clean_categories
