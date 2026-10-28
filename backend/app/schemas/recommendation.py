from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.paper import PaperResponse


class RecommendedPaper(BaseModel):
    paper: PaperResponse
    # 0-100 cosine match to the user's interests / the query paper.
    relevance: int | None = None
    # 0-100 cosine match to the user's saved papers.
    similarity: int | None = None
    matched_interest: str | None = None


class DigestResponse(BaseModel):
    interests: list[str] = Field(default_factory=list)
    items: list[RecommendedPaper] = Field(default_factory=list)
    total: int = 0
    offset: int = 0
    has_more: bool = False
    # True when the database has few matches; the client may run a live search.
    sparse: bool = False
    method: Literal["embedding", "lexical", "recent", "none"] = "none"
    generated_at: datetime


class ScoresRequest(BaseModel):
    paper_ids: list[UUID] = Field(max_length=100)
    # Optional search text; adds a search_match score and weights the ranking.
    query: str | None = Field(default=None, max_length=500)


class PaperScore(BaseModel):
    relevance: int | None = None  # 0-100 match to the project
    similarity: int | None = None  # 0-100 match to the project's saved papers
    search_match: int | None = None  # 0-100 match to the query, when given
    score: float | None = None  # weighted 0-1 ranking score (features.py)
    features: dict[str, float | None] | None = None  # inputs to `score`, for transparency


class ScoresResponse(BaseModel):
    scores: dict[str, PaperScore] = Field(default_factory=dict)
