from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.paper import PaperResponse

# Keep in sync with Settings.search_max_* defaults; service also clamps via settings.
_MAX_QUERY_LENGTH = 500
_MAX_LIMIT = 50


class DiscoverySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=_MAX_QUERY_LENGTH)
    limit: int | None = Field(default=None, ge=1, le=_MAX_LIMIT)
    force_refresh: bool = False

    @field_validator("query")
    @classmethod
    def reject_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Query must not be empty or whitespace-only")
        return value


class ProviderFailure(BaseModel):
    provider: str
    failure_type: str
    detail: str | None = None


class DiscoverySearchResultItem(BaseModel):
    paper: PaperResponse
    similarity_score: float | None = None
    result_origin: Literal["database", "external", "database_and_external"]


class DiscoverySearchResponse(BaseModel):
    query: str
    normalized_query: str
    search_execution_id: UUID
    matched_topic_id: UUID
    topic_match_type: Literal["exact", "semantic", "new"]
    cache_hit: bool
    cache_miss_reason: (
        Literal[
            "no_matching_topic",
            "no_relevant_papers",
            "insufficient_results",
            "low_similarity",
            "stale_topic",
            "force_refresh",
            "incomplete_metadata",
        ]
        | None
    ) = None
    external_search_performed: bool
    providers_attempted: list[str] = Field(default_factory=list)
    providers_succeeded: list[str] = Field(default_factory=list)
    providers_failed: list[ProviderFailure] = Field(default_factory=list)
    results: list[DiscoverySearchResultItem] = Field(default_factory=list)
    searched_at: datetime | None = None
