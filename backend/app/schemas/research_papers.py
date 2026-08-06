from pydantic import BaseModel, Field, field_validator

from app.core.text import clean_paper_text


class IndPaper(BaseModel):
    title: str
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    url: str | None = None
    pdf_url: str | None = None
    source: str
    external_id: str | None = None
    topics: list[str] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        cleaned = clean_paper_text(value)
        return cleaned or "Untitled"

    @field_validator("abstract", mode="before")
    @classmethod
    def clean_abstract(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        return clean_paper_text(value)


class SearchResponse(BaseModel):
    interests: list[str]
    total_results: int
    papers: list[IndPaper]
