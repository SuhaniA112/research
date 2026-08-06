"""Add singleton app profile table (pre-auth preferences).

Revision ID: 0004_app_profile
Revises: 0003_paper_summaries
Create Date: 2026-08-06

Stores shared profile fields used by Profile/Onboarding/Hub until
real user auth exists. Stats remain computed, not stored.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_app_profile"
down_revision: Union[str, Sequence[str], None] = "0003_paper_summaries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SINGLETON_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "profiles" not in inspector.get_table_names():
        op.create_table(
            "profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("occupation", sa.String(length=255), nullable=False),
            sa.Column("institution", sa.String(length=255), nullable=False),
            sa.Column(
                "research_areas",
                postgresql.ARRAY(sa.String()),
                nullable=False,
                server_default=sa.text("'{}'::varchar[]"),
            ),
            sa.Column(
                "keywords",
                postgresql.ARRAY(sa.String()),
                nullable=False,
                server_default=sa.text("'{}'::varchar[]"),
            ),
            sa.Column(
                "reading_level",
                sa.String(length=32),
                nullable=False,
                server_default="graduate",
            ),
            sa.Column(
                "weekly_digest",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "source_notifications",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
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
        )

    op.execute(
        sa.text(
            f"""
            INSERT INTO profiles (
              id, name, full_name, email, occupation, institution,
              research_areas, keywords, reading_level,
              weekly_digest, source_notifications
            ) VALUES (
              '{_SINGLETON_ID}'::uuid, 'Alex', 'Alex Chen', 'alex@example.com',
              'Graduate Student', 'Cornell University',
              ARRAY['AI/ML','HCI','Assistive Tech']::varchar[],
              ARRAY['LLM','GenAI']::varchar[],
              'graduate', true, false
            )
            ON CONFLICT (id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "profiles" in inspector.get_table_names():
        op.drop_table("profiles")
