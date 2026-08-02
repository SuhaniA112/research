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
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/paper_searcher"
    )
    database_echo: bool = False

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = False

    voyage_api_key: str = Field(default="")
    voyage_embedding_model: str = Field(default="voyage-3.5")
    # Must match the Vector(dim) literal on Chunk.embedding (app/models/chunk.py). Changing
    # the embedding model's output width requires migrating that column, not just this value.
    voyage_embedding_dimension: int = Field(default=1024)

    openrouter_api_key: str = Field(default="")
    # Hardcoded default, not user-selectable — see CONTEXT.md's Output/generation decision.
    openrouter_model: str = Field(default="openai/gpt-4o-mini")

    # Max cosine distance (0 = identical, 2 = opposite) for a Chunk to be included in
    # Retrieval results; not a 0-1 similarity score.
    retrieval_max_distance: float = Field(default=0.4)
    retrieval_top_k: int = Field(default=5)

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
