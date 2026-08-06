import uuid

from sqlalchemy import ARRAY, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# Shared app profile until real auth lands. One row, always the same id.
SINGLETON_PROFILE_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


class Profile(Base, TimestampMixin):
    """Singleton preferences/identity row (no auth yet)."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=SINGLETON_PROFILE_ID,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="Researcher")
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Researcher"
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    occupation: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    institution: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    research_areas: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    reading_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="graduate"
    )
    weekly_digest: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    source_notifications: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
