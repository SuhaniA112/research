"""Per-user profiles.

Revision ID: 0010_per_user_profiles
Revises: 0009_paper_validity_metadata
Create Date: 2026-10-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_per_user_profiles"
down_revision: Union[str, Sequence[str], None] = "0009_paper_validity_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if "user_id" not in _columns("profiles"):
        op.add_column(
            "profiles",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_profiles_user_id_users",
            "profiles",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_unique_constraint("uq_profiles_user_id", "profiles", ["user_id"])


def downgrade() -> None:
    if "user_id" in _columns("profiles"):
        op.drop_constraint("uq_profiles_user_id", "profiles", type_="unique")
        op.drop_constraint("fk_profiles_user_id_users", "profiles", type_="foreignkey")
        op.drop_column("profiles", "user_id")
