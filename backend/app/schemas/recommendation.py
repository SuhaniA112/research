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
    method: Literal["embedding", "lexical", "none"] = "none"
    generated_at: datetime


class SimilarityRequest(BaseModel):
    paper_ids: list[UUID] = Field(max_length=100)


class SimilarityResponse(BaseModel):
    scores: dict[str, int | None] = Field(default_factory=dict)
