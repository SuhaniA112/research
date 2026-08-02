"""Create baseline application schema (users, projects, papers, chunks, project_papers).

Revision ID: 0000_baseline_schema
Revises:
Create Date: 2026-08-01

This is the root migration. It creates every table that existed before the
shared-search feature so `alembic upgrade head` works on an empty database.

Idempotent: if a table already exists (e.g. from an older create_all bootstrap),
it is left untouched so local/dev databases with data are not destroyed.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# Matches app.models.chunk.EMBEDDING_DIMENSION.
EMBEDDING_DIMENSION = 1024

revision: str = "0000_baseline_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector: Inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # Preferred path: extension created by infrastructure with a privileged role.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column(
                "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
            ),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        # Matches SQLAlchemy unique=True, index=True on User.email.
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not _table_exists("projects"):
        op.create_table(
            "projects",
            sa.Column(
                "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
            ),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="SET NULL",
            ),
        )

    if not _table_exists("papers"):
        op.create_table(
            "papers",
            sa.Column(
                "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
            ),
            sa.Column("source", sa.String(length=50), nullable=False),
            sa.Column("external_id", sa.String(length=512), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("abstract", sa.Text(), nullable=True),
            sa.Column(
                "authors",
                postgresql.ARRAY(sa.String()),
                nullable=False,
            ),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("pdf_url", sa.Text(), nullable=True),
            sa.Column(
                "topics",
                postgresql.ARRAY(sa.String()),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "source",
                "external_id",
                name="uq_papers_source_external_id",
            ),
        )

    if not _table_exists("chunks"):
        op.create_table(
            "chunks",
            sa.Column(
                "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
            ),
            sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["paper_id"],
                ["papers.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "paper_id",
                "chunk_index",
                name="uq_chunks_paper_id_chunk_index",
            ),
        )
        op.create_index("ix_chunks_paper_id", "chunks", ["paper_id"], unique=False)

    if not _table_exists("project_papers"):
        op.create_table(
            "project_papers",
            sa.Column(
                "project_id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "paper_id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "saved_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["project_id"],
                ["projects.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["paper_id"],
                ["papers.id"],
                ondelete="CASCADE",
            ),
        )


def downgrade() -> None:
    if _table_exists("project_papers"):
        op.drop_table("project_papers")
    if _table_exists("chunks"):
        op.drop_index("ix_chunks_paper_id", table_name="chunks")
        op.drop_table("chunks")
    if _table_exists("papers"):
        op.drop_table("papers")
    if _table_exists("projects"):
        op.drop_table("projects")
    if _table_exists("users"):
        op.drop_index("ix_users_email", table_name="users")
        op.drop_table("users")
