from pydantic import BaseModel, Field


class SourceValidityMetric(BaseModel):
    key: str
    label: str
    # None when no saved paper has this field reported by its provider.
    percent: int | None = None
    # Papers meeting the criterion / papers with the field reported.
    count: int = 0
    known: int = 0


class SourceValidityResponse(BaseModel):
    # Mean of the available metric percentages, 0–100; None with no data.
    score: int | None = None
    status: str
    total_sources: int = 0
    metrics: list[SourceValidityMetric] = Field(default_factory=list)
