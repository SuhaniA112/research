"""Abstract-based fallback summaries and the OpenRouter cooldown."""

import httpx
import pytest

from app.services.summarization import paper_summarizer as ps
from app.services.summarization.extractive import extractive_summary, split_sentences

ABSTRACT = (
    "Medical image segmentation has advanced with deep learning. "
    "Existing models are discriminative and ignore the data distribution. "
    "We propose HiDiff, a hybrid diffusion framework for segmentation. "
    "HiDiff outperforms state-of-the-art methods on four datasets. "
    "It improves Dice by 3.2% on small objects. "
    "Code is available online for everyone to use."
)


def test_levels_grow_with_reading_level() -> None:
    s = extractive_summary(ABSTRACT)
    assert s["general"].count(".") == 2
    assert len(s["general"]) < len(s["graduate"]) < len(s["expert"])


def test_findings_pick_result_sentences() -> None:
    findings = extractive_summary(ABSTRACT)["key_findings"]
    texts = [f["text"] for f in findings]
    assert any("outperforms" in t for t in texts) and any("3.2%" in t for t in texts)
    assert all(f["section"] == "Abstract" for f in findings) and len(findings) <= 3


def test_empty_or_tiny_abstracts() -> None:
    assert extractive_summary(None) is None
    assert extractive_summary("Too short.") is None
    assert split_sentences("One sentence that is long enough here.  ") == [
        "One sentence that is long enough here."
    ]


class _Client:
    api_key = "k"

    def __init__(self, status: int) -> None:
        self.status, self.calls = status, 0

    async def chat_completion(self, messages):
        self.calls += 1
        req = httpx.Request("POST", "https://x")
        raise httpx.HTTPStatusError("x", request=req, response=httpx.Response(self.status, request=req))


@pytest.mark.asyncio
async def test_rate_limit_opens_cooldown(monkeypatch) -> None:
    monkeypatch.setattr(ps, "_cooldown_until", 0.0)
    client = _Client(429)
    s = ps.PaperSummarizer(client)
    assert await s.summarize(title="t", source_text="b") is None
    assert not ps.PaperSummarizer.available()
    assert await s.summarize(title="t", source_text="b") is None
    assert client.calls == 1  # second call skipped during cooldown
    monkeypatch.setattr(ps, "_cooldown_until", 0.0)
    assert ps.PaperSummarizer.available()


def _paper(**over):
    import uuid
    from datetime import datetime, timezone
    from types import SimpleNamespace

    base = dict(
        id=uuid.uuid4(), source="arxiv", external_id="1", title="T", abstract=ABSTRACT,
        authors=[], year=2024, url=None, pdf_url=None, topics=[], source_categories=[],
        citation_count=None, venue=None, is_open_access=None, is_peer_reviewed=None,
        summary_general=None, summary_graduate=None, summary_expert=None, key_findings=[],
        created_at=datetime.now(timezone.utc),
    )
    return SimpleNamespace(**{**base, **over})


def test_response_falls_back_to_abstract_then_prefers_ai() -> None:
    from app.services.ingestion_service import with_summary_fallback

    fallback = with_summary_fallback(_paper())
    assert fallback.summary_source == "extractive" and fallback.summary_general
    assert fallback.key_findings
    ai = with_summary_fallback(_paper(summary_general="g", summary_graduate="g", summary_expert="e"))
    assert ai.summary_source == "ai" and ai.summary_general == "g"
    assert with_summary_fallback(_paper(abstract=None)).summary_source is None
