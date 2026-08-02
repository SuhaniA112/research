import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PaperSearcher API"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/paper_searcher"
    )
    database_echo: bool = False

    # Connection pool — keep conservative for hosted Postgres with low limits.
    database_pool_size: int = Field(default=5)
    database_max_overflow: int = Field(default=10)
    database_pool_timeout: int = Field(default=30)
    database_pool_recycle: int = Field(default=1800)
    database_pool_pre_ping: bool = Field(default=True)

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = False

    voyage_api_key: str = Field(default="")
    voyage_embedding_model: str = Field(default="voyage-3.5")
    # Must match Vector(dim) on Chunk.embedding (app/models/chunk.py). Changing
    # the embedding model output width requires migrating that column, not just
    # this value.
    voyage_embedding_dimension: int = Field(default=1024)

    openrouter_api_key: str = Field(default="")
    # Hardcoded default, not user-selectable — see CONTEXT.md Output decision.
    openrouter_model: str = Field(default="openai/gpt-4o-mini")

    # Max cosine distance (0 = identical, 2 = opposite) for a Chunk to be included in
    # Retrieval results; not a 0-1 similarity score.
    retrieval_max_distance: float = Field(default=0.4)
    retrieval_top_k: int = Field(default=5)

    # --- Database-first discovery cache -----------------------------------------
    # Similarity = 1 - pgvector cosine_distance. Values are in [0, 1] for typical
    # normalized Voyage embeddings (1 = identical, 0 = orthogonal).
    # A paper passes the cache relevance gate when similarity >= this threshold.
    search_cache_paper_similarity_threshold: float = Field(default=0.60)
    # A SearchTopic is considered a semantic match when similarity >= this threshold.
    search_cache_topic_similarity_threshold: float = Field(default=0.85)
    # Minimum number of papers (above the paper similarity threshold) required for
    # a cache hit without calling external providers.
    search_cache_min_results: int = Field(default=5)
    # Topics whose last_external_refresh_at is older than this many days are stale.
    search_cache_max_age_days: int = Field(default=14)
    search_default_limit: int = Field(default=20)
    search_max_limit: int = Field(default=50)
    # Over-fetch factor before per-paper aggregation / final limit trimming.
    search_candidate_multiplier: int = Field(default=3)
    # Max length of a raw/normalized discovery query.
    search_max_query_length: int = Field(default=500)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value

        stripped = value.strip()
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            if not isinstance(parsed, list):
                raise ValueError("CORS_ORIGINS JSON value must be an array")
            return [str(origin).strip() for origin in parsed if str(origin).strip()]

        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def paper_max_distance(self) -> float:
        """Convert configured paper similarity threshold to pgvector cosine distance."""
        return 1.0 - self.search_cache_paper_similarity_threshold

    @property
    def topic_max_distance(self) -> float:
        """Convert configured topic similarity threshold to pgvector cosine distance."""
        return 1.0 - self.search_cache_topic_similarity_threshold


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
