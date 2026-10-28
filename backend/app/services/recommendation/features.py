"""Weighted relevance model: embedding similarity plus engineered signals.

Each feature is in [0, 1] or None (unknown). The composite is a weighted mean over
the known features, so a paper with no citation data isn't penalised for it.
Weights come from weights.json (written by eval/tune_weights.py) or the defaults.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Mapping
from pathlib import Path

FEATURES = ("search", "semantic", "saved", "recency", "citations", "topic")

# search: match to the typed query; semantic: match to the project/interests;
# saved: closeness to saved papers; the rest are metadata signals.
DEFAULT_WEIGHTS: dict[str, float] = {
    "search": 0.45,
    "semantic": 0.30,
    "saved": 0.10,
    "recency": 0.05,
    "citations": 0.05,
    "topic": 0.05,
}

WEIGHTS_PATH = Path(__file__).with_name("weights.json")
RECENCY_HALF_LIFE_YEARS = 5.0
CITATION_CAP = 1000
_TOKEN = re.compile(r"[a-z0-9]+")
_STOPWORDS = {"and", "for", "the", "with", "from", "into", "using", "based", "via", "of"}


def similarity_feature(cosine: float | None) -> float | None:
    if cosine is None or math.isnan(cosine):
        return None
    return max(0.0, min(1.0, float(cosine)))


def recency_feature(year: int | None, now_year: int) -> float | None:
    """1.0 this year, halves every RECENCY_HALF_LIFE_YEARS."""
    if not year:
        return None
    age = max(0, now_year - int(year))
    return 0.5 ** (age / RECENCY_HALF_LIFE_YEARS)


def citation_feature(count: int | None) -> float | None:
    """Log-scaled citation count; CITATION_CAP or more -> 1.0."""
    if count is None:
        return None
    return min(1.0, math.log1p(max(0, count)) / math.log1p(CITATION_CAP))


def tokens(texts: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for text in texts:
        out |= {t for t in _TOKEN.findall((text or "").lower()) if len(t) > 2 and t not in _STOPWORDS}
    return out


def topic_feature(paper_topics: Iterable[str], context: set[str]) -> float | None:
    """Share of context words that appear in the paper's topics."""
    if not context:
        return None
    paper = tokens(paper_topics)
    if not paper:
        return None
    return min(1.0, len(paper & context) / len(context))


def composite(features: Mapping[str, float | None], weights: Mapping[str, float]) -> float | None:
    """Weighted mean of the known features (weights renormalised)."""
    num = den = 0.0
    for name, value in features.items():
        w = weights.get(name, 0.0)
        if value is None or w <= 0:
            continue
        num += w * value
        den += w
    return round(num / den, 4) if den > 0 else None


def load_weights(path: Path = WEIGHTS_PATH) -> dict[str, float]:
    """Defaults overridden by a tuned weights file, if present and valid."""
    weights = dict(DEFAULT_WEIGHTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        tuned = data.get("weights", {})
        weights.update({k: float(v) for k, v in tuned.items() if k in FEATURES and float(v) >= 0})
    except (OSError, ValueError, AttributeError):
        pass
    return weights


def save_weights(weights: Mapping[str, float], meta: Mapping, path: Path = WEIGHTS_PATH) -> None:
    payload = {"weights": {k: round(float(weights.get(k, 0.0)), 4) for k in FEATURES}, **meta}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
