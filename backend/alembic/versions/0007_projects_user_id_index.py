"""Index projects.user_id for user-scoped project lookups.

Revision ID: 0007_projects_user_id_index
Revises: 0006_chunks_embedding_hnsw
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_projects_user_id_index"
down_revision: Union[str, Sequence[str], None] = "0006_chunks_embedding_hnsw"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes("projects")}
    if "ix_projects_user_id" not in existing:
        op.create_index("ix_projects_user_id", "projects", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes("projects")}
    if "ix_projects_user_id" in existing:
        op.drop_index("ix_projects_user_id", table_name="projects")
