"""Unit tests for PaperSummarizer JSON parsing."""

from unittest.mock import AsyncMock

import pytest

from app.services.summarization.paper_summarizer import PaperSummarizer


@pytest.fixture
def summarizer() -> PaperSummarizer:
    client = AsyncMock()
    client.api_key = "test-key"
    return PaperSummarizer(client)


def test_parse_valid_json(summarizer: PaperSummarizer) -> None:
    result = summarizer._parse(
        """
        {
          "general": "Easy summary.",
          "graduate": "Grad summary.",
          "expert": "Expert summary.",
          "key_findings": [
            {"text": "Finding A", "section": "Results"},
            {"text": "Finding B"}
          ]
        }
        """
    )
    assert result is not None
    assert result.general == "Easy summary."
    assert result.graduate == "Grad summary."
    assert result.expert == "Expert summary."
    assert result.key_findings == [
        {"text": "Finding A", "section": "Results"},
        {"text": "Finding B", "section": "Paper"},
    ]


def test_parse_wrapped_in_markdown(summarizer: PaperSummarizer) -> None:
    result = summarizer._parse(
        'Here you go:\n```json\n{"general":"a","graduate":"b","expert":"c","key_findings":[]}\n```'
    )
    assert result is not None
    assert result.general == "a"


def test_parse_missing_level_returns_none(summarizer: PaperSummarizer) -> None:
    assert summarizer._parse('{"general":"a","graduate":"b"}') is None


@pytest.mark.asyncio
async def test_summarize_skips_without_api_key() -> None:
    client = AsyncMock()
    client.api_key = ""
    summarizer = PaperSummarizer(client)
    assert await summarizer.summarize(title="T", source_text="Body") is None
    client.chat_completion.assert_not_called()
