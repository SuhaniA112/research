import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Embedding dimension is a DDL-time literal tied to
# settings.voyage_embedding_model's output width. Swapping to a model with a
# different output dimension requires an Alembic migration of this column
# (and SearchTopic.embedding), not just a config edit.
EMBEDDING_DIMENSION = 1024


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Position within the paper's Indexable Text. Always 0 in v1 (one chunk per paper);
    # exists so multi-chunk splitting later doesn't require a schema rewrite.
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSION), nullable=False
    )
    # Populated from PaperIndexer PreparedChunk.metadata when available.
    # Abstract/title-derived chunks leave page_number null (never fabricated).
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    indexer_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "paper_id", "chunk_index", name="uq_chunks_paper_id_chunk_index"
        ),
        # HNSW ANN index matching cosine distance (<=> / vector_cosine_ops).
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    paper: Mapped["Paper"] = relationship(back_populates="chunks")
