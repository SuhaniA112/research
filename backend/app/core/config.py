from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
