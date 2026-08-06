from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.text import clean_paper_text
from app.schemas.research_papers import IndPaper


class KeyFinding(BaseModel):
    text: str
    section: str = ""

    @field_validator("text", "section", mode="before")
    @classmethod
    def clean_finding_fields(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return clean_paper_text(value) or ""


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
    summary_general: str | None = None
    summary_graduate: str | None = None
    summary_expert: str | None = None
    key_findings: list[KeyFinding] = Field(default_factory=list)
    created_at: datetime

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return clean_paper_text(value) or "Untitled"

    @field_validator(
        "abstract",
        "summary_general",
        "summary_graduate",
        "summary_expert",
        mode="before",
    )
    @classmethod
    def clean_optional_text(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        return clean_paper_text(value)

    @field_validator("key_findings", mode="before")
    @classmethod
    def coerce_key_findings(cls, value: object) -> object:
        return value if value is not None else []


class SavePaperRequest(BaseModel):
    paper: IndPaper


class SavePaperResponse(BaseModel):
    paper: PaperResponse
    already_saved: bool
