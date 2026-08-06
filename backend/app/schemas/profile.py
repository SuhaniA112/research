from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReadingLevel = Literal["casual", "graduate", "expert"]


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    occupation: str | None = Field(default=None, max_length=255)
    institution: str | None = Field(default=None, max_length=255)
    research_areas: list[str] | None = None
    keywords: list[str] | None = None
    reading_level: ReadingLevel | None = None
    weekly_digest: bool | None = None
    source_notifications: bool | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    full_name: str
    email: str
    occupation: str
    institution: str
    member_since: str
    research_areas: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    reading_level: ReadingLevel = "graduate"
    sources_saved: int = 0
    projects_count: int = 0
    active_projects_this_month: int = 0
    notes_written: int = 0
    last_note_days_ago: int = 0
    weekly_digest: bool = True
    source_notifications: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
