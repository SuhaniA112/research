import pytest

from app.core.database import assert_safe_test_database_url
from app.services.query_normalization import normalize_query


class TestNormalizeQuery:
    def test_trims_and_collapses_whitespace(self) -> None:
        assert normalize_query("  contextual   retrieval  ") == "contextual retrieval"

    def test_preserves_punctuation(self) -> None:
        assert (
            normalize_query("BERT-style (encoder) models")
            == "BERT-style (encoder) models"
        )

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalize_query("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="whitespace"):
            normalize_query("   \t  ")


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
