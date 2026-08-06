import uuid

from sqlalchemy import ARRAY, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Paper(Base, TimestampMixin):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Global, deduped across Projects by (source, external_id) — a Paper is a fact,
    # not something owned by whichever Project first saved it.
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    topics: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    summary_general: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_graduate: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_expert: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_findings: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_papers_source_external_id"),
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
    project_papers: Mapped[list["ProjectPaper"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
    topic_papers: Mapped[list["SearchTopicPaper"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
