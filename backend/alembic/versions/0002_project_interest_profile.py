"""Add project interest profile columns (topics, keywords, reading_level).

Revision ID: 0002_project_interest_profile
Revises: 0001_shared_search
Create Date: 2026-08-05

Persists the Create Project form fields that were previously dropped on the
wire, matching the live DB columns used by the frontend.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_project_interest_profile"
down_revision: Union[str, Sequence[str], None] = "0001_shared_search"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    cols = _column_names("projects")
    if "topics" not in cols:
        op.add_column(
            "projects",
            sa.Column(
                "topics",
                postgresql.ARRAY(sa.String()),
                nullable=False,
                server_default="{}",
            ),
        )
    if "keywords" not in cols:
        op.add_column(
            "projects",
            sa.Column(
                "keywords",
                postgresql.ARRAY(sa.String()),
                nullable=False,
                server_default="{}",
            ),
        )
    if "reading_level" not in cols:
        op.add_column(
            "projects",
            sa.Column(
                "reading_level",
                sa.String(length=32),
                nullable=False,
                server_default="graduate",
            ),
        )


def downgrade() -> None:
    cols = _column_names("projects")
    if "reading_level" in cols:
        op.drop_column("projects", "reading_level")
    if "keywords" in cols:
        op.drop_column("projects", "keywords")
    if "topics" in cols:
        op.drop_column("projects", "topics")
