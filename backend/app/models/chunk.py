import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Embedding dimension is a DDL-time literal tied to settings.voyage_embedding_model's output
# width. Swapping to a model with a different output dimension requires migrating this column
# (manual ALTER TABLE or drop/recreate — there is no Alembic in this repo), not just a config edit.
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
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)

    __table_args__ = (
        UniqueConstraint("paper_id", "chunk_index", name="uq_chunks_paper_id_chunk_index"),
    )

    paper: Mapped["Paper"] = relationship(back_populates="chunks")

    # Deferred: add an ANN index once Chunk row count grows past ~10k or query latency
    # becomes noticeable. v1's expected volume (manual, save-triggered ingestion, single
    # implicit workspace) doesn't justify the index build/maintenance cost yet. Locking in
    # vector_cosine_ops now keeps a future index consistent with the distance operator
    # already used in ChunkRepository.search_by_project.
    #
    # __table_args__ += (
    #     Index(
    #         "ix_chunks_embedding_hnsw", "embedding",
    #         postgresql_using="hnsw",
    #         postgresql_with={"m": 16, "ef_construction": 64},
    #         postgresql_ops={"embedding": "vector_cosine_ops"},
    #     ),
    # )
