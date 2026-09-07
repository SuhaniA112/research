"""Migrate identity to Clerk: drop local users table, key profiles/projects/
search_executions by Clerk user id instead of a local UUID FK.

Revision ID: 0005_clerk_auth
Revises: 0004_app_profile
Create Date: 2026-09-07

No local user data predates real auth (see PROJECT-STATUS.md), so existing
rows in profiles/projects/search_executions are treated as disposable rather
than converted.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_clerk_auth"
down_revision: Union[str, Sequence[str], None] = "0004_app_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cascades to drop the projects.user_id / search_executions.user_id FK
    # constraints without needing their (unnamed, DB-assigned) constraint names.
    op.execute("DROP TABLE IF EXISTS users CASCADE")

    op.execute("TRUNCATE TABLE search_executions")
    op.alter_column(
        "search_executions",
        "user_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        type_=sa.String(length=64),
        nullable=False,
        postgresql_using="user_id::text",
    )

    # CASCADE also truncates project_papers, which FKs to projects.
    op.execute("TRUNCATE TABLE projects CASCADE")
    op.alter_column(
        "projects",
        "user_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        type_=sa.String(length=64),
        nullable=False,
        postgresql_using="user_id::text",
    )

    op.execute("TRUNCATE TABLE profiles")
    op.drop_column("profiles", "name")
    op.drop_column("profiles", "full_name")
    op.drop_column("profiles", "email")
    op.alter_column(
        "profiles",
        "id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        type_=sa.String(length=64),
        postgresql_using="id::text",
    )


def downgrade() -> None:
    op.alter_column(
        "profiles",
        "id",
        existing_type=sa.String(length=64),
        type_=sa.dialects.postgresql.UUID(as_uuid=True),
        postgresql_using="id::uuid",
    )
    op.add_column(
        "profiles",
        sa.Column("email", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "profiles",
        sa.Column(
            "full_name", sa.String(length=255), nullable=False, server_default=""
        ),
    )
    op.add_column(
        "profiles",
        sa.Column("name", sa.String(length=100), nullable=False, server_default=""),
    )

    op.execute("TRUNCATE TABLE projects CASCADE")
    op.alter_column(
        "projects",
        "user_id",
        existing_type=sa.String(length=64),
        type_=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
        postgresql_using="user_id::uuid",
    )

    op.execute("TRUNCATE TABLE search_executions")
    op.alter_column(
        "search_executions",
        "user_id",
        existing_type=sa.String(length=64),
        type_=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
        postgresql_using="user_id::uuid",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
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
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_foreign_key(
        "projects_user_id_fkey",
        "projects",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "search_executions_user_id_fkey",
        "search_executions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
