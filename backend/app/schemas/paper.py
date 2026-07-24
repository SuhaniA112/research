from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.research_papers import IndPaper


class PaperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    external_id: str
    title: str
    abstract: str | None
    authors: list[str]
    year: int | None
    url: str | None
    pdf_url: str | None
    topics: list[str]
    created_at: datetime


class SavePaperRequest(BaseModel):
    paper: IndPaper


class SavePaperResponse(BaseModel):
    paper: PaperResponse
    already_saved: bool
