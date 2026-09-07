"""Add papers.source_categories and clean contaminated topics.

Revision ID: 0008_paper_source_categories
Revises: 0007_projects_user_id_index
Create Date: 2026-09-07

Separates raw provider taxonomy codes from user-facing paper topics, and
removes known search-query contaminants that were previously copied into
``papers.topics``.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_paper_source_categories"
down_revision: Union[str, Sequence[str], None] = "0007_projects_user_id_index"
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
    if "source_categories" not in cols:
        op.add_column(
            "papers",
            sa.Column(
                "source_categories",
                postgresql.ARRAY(sa.String()),
                nullable=False,
                server_default="{}",
            ),
        )

    # Data backfill: move arXiv codes out of topics, drop known query strings,
    # and rebuild human-readable topics from the taxonomy map.
    from app.services.taxonomy.paper_topics import sanitize_persisted_topic_fields

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, topics, source_categories FROM papers")
    ).fetchall()

    update_stmt = sa.text(
        "UPDATE papers SET topics = :topics, source_categories = :categories "
        "WHERE id = :id"
    )

    for row in rows:
        paper_id, topics, source_categories = row[0], row[1], row[2]
        clean_topics, clean_categories = sanitize_persisted_topic_fields(
            list(topics or []),
            list(source_categories or []),
        )
        if clean_topics == list(topics or []) and clean_categories == list(
            source_categories or []
        ):
            continue
        bind.execute(
            update_stmt,
            {
                "id": paper_id,
                "topics": clean_topics,
                "categories": clean_categories,
            },
        )


def downgrade() -> None:
    cols = _column_names("papers")
    if "source_categories" in cols:
        # Best-effort: fold source categories back into topics for older code,
        # without re-introducing known query contaminants (those stay gone).
        bind = op.get_bind()
        rows = bind.execute(
            sa.text("SELECT id, topics, source_categories FROM papers")
        ).fetchall()
        update_stmt = sa.text("UPDATE papers SET topics = :topics WHERE id = :id")
        for row in rows:
            paper_id, topics, source_categories = row[0], row[1], row[2]
            merged: list[str] = []
            seen: set[str] = set()
            for item in list(topics or []) + list(source_categories or []):
                if not item:
                    continue
                key = str(item).casefold()
                if key in seen:
                    continue
                seen.add(key)
                merged.append(str(item))
            if merged != list(topics or []):
                bind.execute(update_stmt, {"id": paper_id, "topics": merged})

        op.drop_column("papers", "source_categories")
