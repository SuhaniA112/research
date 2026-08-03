from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.chunk import EMBEDDING_DIMENSION


class SearchTopic(Base, TimestampMixin):
    """Global semantic research topic shared across users.

    Not a user's private search-history record. Exact normalized queries and
    sufficiently similar embeddings reuse an existing topic rather than creating
    duplicates. Does not store user identity or Project data.
    """

    __tablename__ = "search_topics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    canonical_query: Mapped[str] = mapped_column(Text, nullable=False)
    # Exact-match key for topic reuse. Unique so concurrent inserts for the same
    # normalized query collide safely at the database level.
    normalized_query: Mapped[str] = mapped_column(String(1024), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=False
    )
    last_external_refresh_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    external_refresh_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_result_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    topic_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    __table_args__ = (
        UniqueConstraint("normalized_query", name="uq_search_topics_normalized_query"),
    )

    search_executions: Mapped[list["SearchExecution"]] = relationship(
        back_populates="search_topic"
    )
    topic_papers: Mapped[list["SearchTopicPaper"]] = relationship(
        back_populates="search_topic", cascade="all, delete-orphan"
    )
