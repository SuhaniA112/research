from pydantic import BaseModel, Field


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


class SearchResponse(BaseModel):
    interests: list[str]
    total_results: int
    papers: list[IndPaper]
