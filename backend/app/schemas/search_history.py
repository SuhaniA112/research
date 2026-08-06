from pydantic import BaseModel, Field


class SearchHistoryRecordRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=64)
    query: str = Field(min_length=1, max_length=500)


class SearchHistoryDeleteRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=500)
    project_id: str | None = Field(default=None, max_length=64)


class SearchHistoryClearRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)


class SearchHistoryResponse(BaseModel):
    recent_searches: list[str]
    recent_project_searches: dict[str, list[str]]
