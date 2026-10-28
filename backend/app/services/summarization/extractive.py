"""No-LLM fallback: leveled summaries and key findings pulled from the abstract.

Used when OpenRouter is unavailable (no key, rate-limited, errors) so cards still
show readable summaries. Results are labelled ``extractive`` and never persisted,
so an AI summary replaces them once the model is reachable again.
"""

from __future__ import annotations

import re

_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(])")
# Phrases that usually introduce a result or contribution.
_FINDING_CUES = re.compile(
    r"\b(we (show|find|demonstrate|propose|introduce|present)|results?|outperform\w*|"
    r"achiev\w*|improv\w*|state-of-the-art|significant\w*|reduc\w*|increas\w*)\b|\d+(\.\d+)?\s?%",
    re.IGNORECASE,
)
MAX_FINDINGS = 3


def split_sentences(text: str) -> list[str]:
    cleaned = " ".join((text or "").split())
    return [s.strip() for s in _SENTENCE.split(cleaned) if len(s.strip()) > 20]


def extractive_summary(abstract: str | None) -> dict | None:
    """General = first 2 sentences, graduate = first 3, expert = up to 5; None if no abstract."""
    sentences = split_sentences(abstract or "")
    if not sentences:
        return None
    findings = [s for s in sentences[1:] if _FINDING_CUES.search(s)][:MAX_FINDINGS]
    return {
        "general": " ".join(sentences[:2]),
        "graduate": " ".join(sentences[:3]),
        "expert": " ".join(sentences[:5]),
        "key_findings": [{"text": s, "section": "Abstract"} for s in findings],
    }
