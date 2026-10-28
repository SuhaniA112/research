from pydantic import BaseModel, Field


class SourceValidityMetric(BaseModel):
    key: str
    label: str
    # None when no saved paper has this field reported by its provider.
    percent: int | None = None
    # Papers meeting the criterion / papers with the field reported.
    count: int = 0
    known: int = 0


class BreakdownItem(BaseModel):
    name: str
    count: int
    percent: int


class RecencyBar(BaseModel):
    year: int
    count: int


class RecencyStats(BaseModel):
    bars: list[RecencyBar]
    earliest_year: int
    total: int
    start_year: int
    present_year: int


class TopicCount(BaseModel):
    topic: str
    count: int


class SourceValidityResponse(BaseModel):
    # Mean of the available metric percentages, 0–100; None with no data.
    score: int | None = None
    status: str
    total_sources: int = 0
    metrics: list[SourceValidityMetric] = Field(default_factory=list)


class ProjectStatsResponse(BaseModel):
    total_sources: int = 0
    breakdown: list[BreakdownItem] = Field(default_factory=list)
    recency: RecencyStats | None = None
    validity: SourceValidityResponse
    topics: list[TopicCount] = Field(default_factory=list)
