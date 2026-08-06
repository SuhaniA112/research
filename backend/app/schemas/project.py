from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ReadingLevel = Literal["casual", "graduate", "expert"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    topics: list[str] = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    reading_level: ReadingLevel = "graduate"


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    source_count: int = 0
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    reading_level: ReadingLevel = "graduate"
