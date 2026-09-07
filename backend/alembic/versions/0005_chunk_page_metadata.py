"""Add page/chunk metadata columns on chunks.

Revision ID: 0005_chunk_page_metadata
Revises: 0004_app_profile
Create Date: 2026-08-08

Persists indexer metadata (page_number, content_type, indexer_version).
Existing rows remain valid with NULL values.

Idempotent: skips columns that already exist (e.g. when baseline was bootstrapped
via SQLAlchemy create_all with the current model).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_chunk_page_metadata"
down_revision: Union[str, Sequence[str], None] = "0004_app_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("chunks")}

    if "page_number" not in existing:
        op.add_column(
            "chunks",
            sa.Column("page_number", sa.Integer(), nullable=True),
        )
    if "content_type" not in existing:
        op.add_column(
            "chunks",
            sa.Column("content_type", sa.String(length=32), nullable=True),
        )
    if "indexer_version" not in existing:
        op.add_column(
            "chunks",
            sa.Column("indexer_version", sa.String(length=32), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("chunks")}
    if "indexer_version" in existing:
        op.drop_column("chunks", "indexer_version")
    if "content_type" in existing:
        op.drop_column("chunks", "content_type")
    if "page_number" in existing:
        op.drop_column("chunks", "page_number")
