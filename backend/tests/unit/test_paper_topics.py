"""Regression tests for paper topic architecture."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.research_papers import IndPaper
from app.services.indexing.paper_indexer import PaperIndexer
from app.services.query_normalization import normalize_topic_list
from app.services.research_sources.arxiv import ArxivClient
from app.services.research_sources.dblp import DblpClient
from app.services.research_sources.openalex import OpenAlexClient
from app.services.research_sources.semanticscholar import SemanticScholarClient
from app.services.taxonomy.arxiv_categories import (
    is_arxiv_category_code,
    map_arxiv_categories_to_topics,
)
from app.services.taxonomy.paper_topics import (
    build_paper_topics,
    sanitize_persisted_topic_fields,
)


class TestArxivCategoryMapping:
    def test_single_category(self) -> None:
        assert map_arxiv_categories_to_topics(["cs.CV"]) == [
            "Computer Science",
            "Computer Vision",
        ]

    def test_multiple_categories_dedupe_machine_learning(self) -> None:
        assert map_arxiv_categories_to_topics(["cs.CV", "cs.LG", "stat.ML"]) == [
            "Computer Science",
            "Statistics",
            "Computer Vision",
            "Machine Learning",
        ]

    def test_fake_news_style_categories(self) -> None:
        topics = map_arxiv_categories_to_topics(
            ["cs.CL", "cs.IR", "cs.LG", "stat.ML"]
        )
        assert topics == [
            "Computer Science",
            "Statistics",
            "Natural Language Processing",
            "Information Retrieval",
            "Machine Learning",
        ]
        assert topics.count("Machine Learning") == 1

    def test_unknown_category_does_not_crash_or_fabricate(self) -> None:
        assert map_arxiv_categories_to_topics(["cs.SOMETHING_UNKNOWN"]) == []
        assert is_arxiv_category_code("cs.SOMETHING_UNKNOWN")
        topics, categories = sanitize_persisted_topic_fields(
            ["cs.SOMETHING_UNKNOWN"],
            [],
        )
        assert categories == ["cs.SOMETHING_UNKNOWN"]
        assert topics == []
        assert "cs.SOMETHING_UNKNOWN" not in topics


class TestBuildPaperTopics:
    def test_arxiv_query_isolation(self) -> None:
        topics = build_paper_topics(
            source_categories=["cs.CV"],
            provider_topics=["computer vision medical imaging"],
        )
        assert "Computer Science" in topics
        assert "Computer Vision" in topics
        assert "computer vision medical imaging" not in topics
        assert "cs.CV" not in topics

    def test_does_not_use_search_query_as_topic(self) -> None:
        topics = build_paper_topics(
            source_categories=["cs.CL", "cs.IR", "cs.LG", "stat.ML"],
            provider_topics=[
                "machine learning and detection of medical conditions"
            ],
        )
        assert "machine learning and detection of medical conditions" not in [
            t.casefold() for t in topics
        ]
        for expected in [
            "Computer Science",
            "Natural Language Processing",
            "Information Retrieval",
            "Machine Learning",
            "Statistics",
        ]:
            assert expected in topics


class TestSanitizePersistedTopics:
    def test_stale_data_cleanup(self) -> None:
        topics, categories = sanitize_persisted_topic_fields(
            ["cs.CV", "computer vision medical imaging"],
            [],
        )
        assert categories == ["cs.CV"]
        assert topics == ["Computer Science", "Computer Vision"]
        assert "computer vision medical imaging" not in topics

    def test_fake_news_contamination_cleanup(self) -> None:
        topics, categories = sanitize_persisted_topic_fields(
            [
                "cs.CL",
                "cs.IR",
                "cs.LG",
                "stat.ML",
                "machine learning and detection of medical conditions",
            ],
            [],
        )
        assert categories == ["cs.CL", "cs.IR", "cs.LG", "stat.ML"]
        assert "machine learning and detection of medical conditions" not in [
            t.casefold() for t in topics
        ]
        assert "Computer Science" in topics
        assert "Natural Language Processing" in topics
        assert "Information Retrieval" in topics
        assert "Machine Learning" in topics
        assert "Statistics" in topics

    def test_preserves_provider_native_labels(self) -> None:
        topics, categories = sanitize_persisted_topic_fields(
            ["Computer Science", "Active Learning"],
            ["cs.LG"],
        )
        assert categories == ["cs.LG"]
        assert "Computer Science" in topics
        assert "Machine Learning" in topics
        assert "Active Learning" in topics


class TestNormalizeDoesNotSplitAnd:
    def test_vision_and_language_models_stays_one_topic(self) -> None:
        assert normalize_topic_list(["vision and language models"]) == [
            "vision and language models"
        ]


class TestArxivClientTopics:
    @pytest.mark.asyncio
    async def test_query_not_copied_into_topics(self) -> None:
        feed = MagicMock()
        entry = MagicMock()
        entry.title = "Active Learning for Medical Image Segmentation"
        entry.summary = "An abstract."
        entry.authors = []
        entry.links = []
        entry.published = "2024-01-01"
        entry.link = "https://arxiv.org/abs/2401.00001"
        entry.id = "http://arxiv.org/abs/2401.00001"
        tag = MagicMock()
        tag.term = "cs.CV"
        entry.tags = [tag]
        feed.entries = [entry]

        response = MagicMock()
        response.text = "<feed/>"
        response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = response

        with (
            patch(
                "app.services.research_sources.arxiv.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "app.services.research_sources.arxiv.feedparser.parse",
                return_value=feed,
            ),
        ):
            results = await ArxivClient().search(
                "computer vision medical imaging", max_results=1
            )

        assert len(results) == 1
        paper = results[0]
        assert paper.source_categories == ["cs.CV"]
        assert "Computer Science" in paper.topics
        assert "Computer Vision" in paper.topics
        assert "computer vision medical imaging" not in paper.topics
        assert "cs.CV" not in paper.topics


class TestDblpClientTopics:
    @pytest.mark.asyncio
    async def test_query_not_used_as_topic(self) -> None:
        payload = {
            "result": {
                "hits": {
                    "hit": [
                        {
                            "@id": "123",
                            "info": {
                                "title": "Some Paper",
                                "year": "2020",
                                "url": "https://dblp.org/rec/123",
                                "authors": {"author": {"text": "Ada"}},
                            },
                        }
                    ]
                }
            }
        }
        response = MagicMock()
        response.json.return_value = payload
        response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = response

        with patch(
            "app.services.research_sources.dblp.httpx.AsyncClient",
            return_value=mock_client,
        ):
            results = await DblpClient().search(
                "machine learning and detection of medical conditions",
                max_results=1,
            )

        assert len(results) == 1
        assert results[0].topics == []
        assert results[0].source_categories == []


class TestOpenAlexClientTopics:
    @pytest.mark.asyncio
    async def test_preserves_provider_topics_not_query(self) -> None:
        payload = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "title": "A Paper",
                    "authorships": [],
                    "publication_year": 2024,
                    "open_access": {},
                    "abstract_inverted_index": None,
                    "topics": [{"display_name": "Computer Vision"}],
                }
            ]
        }
        response = MagicMock()
        response.json.return_value = payload
        response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = response

        with patch(
            "app.services.research_sources.openalex.httpx.AsyncClient",
            return_value=mock_client,
        ):
            results = await OpenAlexClient().search(
                "artificial intelligence in healthcare", max_results=1
            )

        assert results[0].topics == ["Computer Vision"]
        assert "artificial intelligence in healthcare" not in results[0].topics
        assert results[0].source_categories == []


class TestSemanticScholarClientTopics:
    @pytest.mark.asyncio
    async def test_preserves_fields_of_study_not_query(self) -> None:
        payload = {
            "data": [
                {
                    "paperId": "abc",
                    "title": "A Paper",
                    "abstract": "Abs",
                    "authors": [],
                    "year": 2024,
                    "url": "https://example.com",
                    "openAccessPdf": {},
                    "fieldsOfStudy": ["Computer Science", "Medicine"],
                }
            ]
        }
        response = MagicMock()
        response.json.return_value = payload
        response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = response

        with patch(
            "app.services.research_sources.semanticscholar.httpx.AsyncClient",
            return_value=mock_client,
        ):
            results = await SemanticScholarClient().search(
                "computer vision medical imaging", max_results=1
            )

        assert results[0].topics == ["Computer Science", "Medicine"]
        assert "computer vision medical imaging" not in results[0].topics


class TestPaperIndexerTopics:
    @pytest.mark.asyncio
    async def test_embedding_text_excludes_contaminated_query(self) -> None:
        indexer = PaperIndexer()
        paper = IndPaper(
            title="Fake News Detection Benchmark",
            abstract="We study fake news detection.",
            authors=["A"],
            year=2024,
            url="https://example.com",
            source="arxiv",
            external_id="2401.00002",
            topics=[
                "cs.CL",
                "machine learning and detection of medical conditions",
            ],
            source_categories=["cs.CL", "cs.LG"],
        )

        chunks = await indexer.prepare_chunks("paper-1", paper)
        assert chunks
        text = chunks[0].embedding_text
        assert "machine learning and detection of medical conditions" not in text
        assert "Topics:" in text
        assert "Computer Science" in text
        assert "Natural Language Processing" in text or "Machine Learning" in text
        # Raw codes should not be the Topics: line content when mapped.
        assert "Topics: cs.CL" not in text
