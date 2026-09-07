"""Create HNSW ANN index on chunks.embedding (cosine).

Revision ID: 0006_chunks_embedding_hnsw
Revises: 0005_chunk_page_metadata
Create Date: 2026-08-08

Does not alter embedding dimension or recreate the column.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0006_chunks_embedding_hnsw"
down_revision: Union[str, Sequence[str], None] = "0005_chunk_page_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw
        ON chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
