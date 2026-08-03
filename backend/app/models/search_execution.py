from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SearchExecution(Base):
    """User-specific (or anonymous) record that a search was performed.

    Every search request creates a row, including cache hits. Raw query history
    stays private; this table must not be exposed globally. Authorization for
    listing a user's own executions is deferred until authentication exists.
    """

    __tablename__ = "search_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Nullable until authentication exists; structure ready for real user IDs.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    search_topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_query: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cache_miss_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_search_performed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    force_refresh: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requested_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    results_returned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    anonymous_session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    search_topic: Mapped["SearchTopic"] = relationship(
        back_populates="search_executions"
    )
