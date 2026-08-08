import pytest

from app.core.database import assert_safe_test_database_url
from app.services.query_normalization import (
    build_intent_query_from_topics,
    merge_topic_lists,
    normalize_query,
    normalize_topic_list,
)


class TestNormalizeQuery:
    def test_trims_and_collapses_whitespace(self) -> None:
        assert normalize_query("  contextual   retrieval  ") == "contextual retrieval"

    def test_preserves_technical_punctuation(self) -> None:
        assert (
            normalize_query("BERT-style (encoder) models")
            == "bert-style (encoder) models"
        )

    def test_casefolds(self) -> None:
        assert normalize_query("Machine Learning") == "machine learning"
        assert normalize_query("GRAPH Neural Nets") == "graph neural nets"

    def test_unicode_nfkc(self) -> None:
        # Fullwidth letters normalize under NFKC then casefold.
        assert normalize_query("ＭＬ") == "ml"

    def test_normalizes_delimiter_spacing(self) -> None:
        assert normalize_query("ml ,  imaging") == "ml, imaging"
        assert normalize_query("a;b|c") == "a; b| c"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalize_query("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="whitespace"):
            normalize_query("   \t  ")


class TestNormalizeTopicList:
    def test_comma_splitting(self) -> None:
        assert normalize_topic_list(
            ["Machine Learning, Medical Imaging, Cancer Detection"]
        ) == ["Machine Learning", "Medical Imaging", "Cancer Detection"]

    def test_semicolon_splitting(self) -> None:
        assert normalize_topic_list(["A; B; C"]) == ["A", "B", "C"]

    def test_newline_splitting(self) -> None:
        assert normalize_topic_list(["A\nB\nC"]) == ["A", "B", "C"]

    def test_pipe_splitting(self) -> None:
        assert normalize_topic_list(["A|B|C"]) == ["A", "B", "C"]

    def test_whitespace_and_repeated_delimiters(self) -> None:
        assert normalize_topic_list(["  A  ,,  ; B ||  "]) == ["A", "B"]

    def test_duplicate_topics_case_insensitive(self) -> None:
        assert normalize_topic_list(
            [
                "Machine Learning, medical imaging",
                "Cancer Detection",
                "machine learning",
            ]
        ) == ["Machine Learning", "medical imaging", "Cancer Detection"]

    def test_preserves_and_phrases(self) -> None:
        assert normalize_topic_list(["research and development"]) == [
            "research and development"
        ]
        assert normalize_topic_list(["R&D, research and development"]) == [
            "R&D",
            "research and development",
        ]

    def test_already_separated_arrays(self) -> None:
        assert normalize_topic_list(
            ["Machine Learning", "Medical Imaging", "Cancer Detection"]
        ) == ["Machine Learning", "Medical Imaging", "Cancer Detection"]

    def test_empty_values(self) -> None:
        assert normalize_topic_list([]) == []
        assert normalize_topic_list(None) == []
        assert normalize_topic_list(["", "  ", ",,", "A"]) == ["A"]

    def test_merge_topic_lists(self) -> None:
        assert merge_topic_lists(
            ["Machine Learning"],
            ["machine learning, NLP"],
            None,
            [],
        ) == ["Machine Learning", "NLP"]

    def test_build_intent_query_from_topics(self) -> None:
        assert (
            build_intent_query_from_topics(
                ["Machine Learning, Imaging"],
                ["cancer"],
            )
            == "Machine Learning, Imaging, cancer"
        )
        assert build_intent_query_from_topics([], []) is None
        assert build_intent_query_from_topics(None, None) is None


class TestTestDatabaseGuard:
    def test_allows_test_database_name(self) -> None:
        assert_safe_test_database_url(
            "postgresql+asyncpg://postgres:postgres@localhost:5432/paper_searcher_test"
        )

    def test_rejects_production_database_name(self) -> None:
        with pytest.raises(RuntimeError, match="containing 'test'"):
            assert_safe_test_database_url(
                "postgresql+asyncpg://postgres:postgres@localhost:5432/paper_searcher"
            )

    def test_rejects_hosted_production_looking_url(self) -> None:
        with pytest.raises(RuntimeError, match="containing 'test'"):
            assert_safe_test_database_url(
                "postgresql+asyncpg://user:pass@db.example.com:5432/paper_searcher_prod"
            )
