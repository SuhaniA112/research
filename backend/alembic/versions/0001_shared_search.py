"""Add shared search topic tables for database-first discovery.

Revision ID: 0001_shared_search
Revises: 0000_baseline_schema
Create Date: 2026-08-01

Adds SearchTopic, SearchExecution, and SearchTopicPaper on top of the baseline
schema. Requires 0000_baseline_schema (users, papers, …) and pgvector.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# Matches app.models.chunk.EMBEDDING_DIMENSION / settings.voyage_embedding_dimension.
EMBEDDING_DIMENSION = 1024

revision: str = "0001_shared_search"
down_revision: Union[str, Sequence[str], None] = "0000_baseline_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_topics",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("canonical_query", sa.Text(), nullable=False),
        sa.Column("normalized_query", sa.String(length=1024), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
        sa.Column(
            "last_external_refresh_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "external_refresh_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "last_result_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            "normalized_query", name="uq_search_topics_normalized_query"
        ),
    )
    op.create_index(
        "ix_search_topics_last_external_refresh_at",
        "search_topics",
        ["last_external_refresh_at"],
        unique=False,
    )

    op.create_table(
        "search_executions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_query", sa.Text(), nullable=False),
        sa.Column("normalized_query", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cache_hit", sa.Boolean(), nullable=False),
        sa.Column("cache_miss_reason", sa.String(length=64), nullable=True),
        sa.Column("external_search_performed", sa.Boolean(), nullable=False),
        sa.Column("force_refresh", sa.Boolean(), nullable=False),
        sa.Column("requested_limit", sa.Integer(), nullable=False),
        sa.Column("results_returned", sa.Integer(), nullable=False),
        sa.Column("anonymous_session_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["search_topic_id"],
            ["search_topics.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_search_executions_user_id",
        "search_executions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_search_executions_search_topic_id",
        "search_executions",
        ["search_topic_id"],
        unique=False,
    )
    op.create_index(
        "ix_search_executions_created_at",
        "search_executions",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "search_topic_papers",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("search_topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paper_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semantic_relevance_score", sa.Float(), nullable=True),
        sa.Column("provider_rank", sa.Integer(), nullable=True),
        sa.Column(
            "first_discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("discovery_source", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["paper_id"],
            ["papers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["search_topic_id"],
            ["search_topics.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "search_topic_id",
            "paper_id",
            name="uq_search_topic_papers_topic_paper",
        ),
    )
    op.create_index(
        "ix_search_topic_papers_search_topic_id",
        "search_topic_papers",
        ["search_topic_id"],
        unique=False,
    )
    op.create_index(
        "ix_search_topic_papers_paper_id",
        "search_topic_papers",
        ["paper_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_search_topic_papers_paper_id", table_name="search_topic_papers")
    op.drop_index(
        "ix_search_topic_papers_search_topic_id", table_name="search_topic_papers"
    )
    op.drop_table("search_topic_papers")

    op.drop_index("ix_search_executions_created_at", table_name="search_executions")
    op.drop_index(
        "ix_search_executions_search_topic_id", table_name="search_executions"
    )
    op.drop_index("ix_search_executions_user_id", table_name="search_executions")
    op.drop_table("search_executions")

    op.drop_index(
        "ix_search_topics_last_external_refresh_at", table_name="search_topics"
    )
    op.drop_table("search_topics")
