from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SearchTopicPaper(Base):
    """Join between a global SearchTopic and a global Paper.

    The same Paper may belong to many topics; the same topic may contain many
    papers. Repeated discovery updates last_seen_at rather than inserting
    duplicates. semantic_relevance_score is cosine similarity in [0, 1]
    (derived as 1 - pgvector cosine_distance).
    """

    __tablename__ = "search_topic_papers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    search_topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Cosine similarity = 1 - cosine_distance. Higher is more relevant.
    semantic_relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    discovery_source: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "search_topic_id",
            "paper_id",
            name="uq_search_topic_papers_topic_paper",
        ),
    )

    search_topic: Mapped["SearchTopic"] = relationship(back_populates="topic_papers")
    paper: Mapped["Paper"] = relationship(back_populates="topic_papers")
