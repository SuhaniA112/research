"""Text helpers for paper metadata cleanup."""

from __future__ import annotations

import html
import re

_WHITESPACE = re.compile(r"\s+")


def clean_paper_text(value: str | None) -> str | None:
    """Decode HTML entities and normalize whitespace in provider text.

    Providers (esp. Semantic Scholar / OpenAlex) often return titles like:
    ``&quot;Hey Siri, How Am I Doing?&quot;: Legal Challenges...``
    """
    if value is None:
        return None
    text = html.unescape(value).replace("\xa0", " ")
    text = _WHITESPACE.sub(" ", text).strip()
    return text or None
