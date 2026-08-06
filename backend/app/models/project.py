import uuid

from sqlalchemy import ARRAY, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Forward-compat only; no auth exists yet so this is never enforced today.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    reading_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="graduate"
    )

    project_papers: Mapped[list["ProjectPaper"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
