"""Add source-validity metadata to papers.

Revision ID: 0009_paper_validity_metadata
Revises: 0008_paper_source_categories
Create Date: 2026-10-28

Adds nullable provider metadata used by the project Source Validity card:
citation count, venue, open-access and peer-reviewed flags. NULL means the
provider did not report the value; existing rows fill in on the next provider
refresh (discovery upsert) rather than via a backfill here.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_paper_validity_metadata"
down_revision: Union[str, Sequence[str], None] = "0008_paper_source_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_COLUMNS: list[tuple[str, sa.types.TypeEngine]] = [
    ("citation_count", sa.Integer()),
    ("venue", sa.Text()),
    ("is_open_access", sa.Boolean()),
    ("is_peer_reviewed", sa.Boolean()),
]


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    cols = _column_names("papers")
    for name, type_ in _NEW_COLUMNS:
        if name not in cols:
            op.add_column("papers", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    cols = _column_names("papers")
    for name, _ in reversed(_NEW_COLUMNS):
        if name in cols:
            op.drop_column("papers", name)
