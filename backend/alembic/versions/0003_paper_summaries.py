"""Add leveled summaries and key findings on papers.

Revision ID: 0003_paper_summaries
Revises: 0002_project_interest_profile
Create Date: 2026-08-06

Stores OpenRouter-generated General/Graduate/Expert summaries plus
structured key findings for source cards and the source detail page.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_paper_summaries"
down_revision: Union[str, Sequence[str], None] = "0002_project_interest_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    cols = _column_names("papers")
    if "summary_general" not in cols:
        op.add_column("papers", sa.Column("summary_general", sa.Text(), nullable=True))
    if "summary_graduate" not in cols:
        op.add_column("papers", sa.Column("summary_graduate", sa.Text(), nullable=True))
    if "summary_expert" not in cols:
        op.add_column("papers", sa.Column("summary_expert", sa.Text(), nullable=True))
    if "key_findings" not in cols:
        op.add_column(
            "papers",
            sa.Column(
                "key_findings",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )


def downgrade() -> None:
    cols = _column_names("papers")
    if "key_findings" in cols:
        op.drop_column("papers", "key_findings")
    if "summary_expert" in cols:
        op.drop_column("papers", "summary_expert")
    if "summary_graduate" in cols:
        op.drop_column("papers", "summary_graduate")
    if "summary_general" in cols:
        op.drop_column("papers", "summary_general")
