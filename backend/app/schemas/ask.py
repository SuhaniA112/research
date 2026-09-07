from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class Citation(BaseModel):
    paper_id: UUID
    chunk_id: UUID
    title: str
    url: str | None
    page_number: int | None = None
    distance: float


class AskResponse(BaseModel):
    status: Literal["answered", "no_relevant_sources"]
    answer: str | None
    citations: list[Citation]
