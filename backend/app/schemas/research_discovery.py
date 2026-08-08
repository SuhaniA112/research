from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.paper import PaperResponse

# Keep in sync with Settings.search_max_* defaults; service also clamps via settings.
_MAX_QUERY_LENGTH = 500
_MAX_LIMIT = 50


class DiscoverySearchRequest(BaseModel):
    """Database-first discovery request.

    ``query`` may be empty when ``project_id`` is set — the backend builds the
    effective intent from the project's topics/keywords. Empty query with no
    usable project/profile context is rejected by the service.
    """

    query: str = Field(default="", max_length=_MAX_QUERY_LENGTH)
    project_id: UUID | None = None
    limit: int | None = Field(default=None, ge=1, le=_MAX_LIMIT)
    force_refresh: bool = False

    @model_validator(mode="after")
    def validate_query_or_project(self) -> "DiscoverySearchRequest":
        # Allow whitespace/empty when project context can supply intent.
        if self.project_id is not None:
            return self
        if not (self.query or "").strip():
            # Keep a clear empty-state path; service may still try profile fallback.
            return self
        return self


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
