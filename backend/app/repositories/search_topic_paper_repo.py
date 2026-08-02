from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.paper import Paper
from app.models.search_topic_paper import SearchTopicPaper


class SearchTopicPaperRepository:
    """Join-table repository (not BaseRepository — specialized upsert API)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_papers_for_topic(
        self, search_topic_id: UUID, *, limit: int
    ) -> list[tuple[Paper, SearchTopicPaper]]:
        stmt = (
            select(Paper, SearchTopicPaper)
            .join(SearchTopicPaper, SearchTopicPaper.paper_id == Paper.id)
            .where(SearchTopicPaper.search_topic_id == search_topic_id)
            .order_by(
                SearchTopicPaper.semantic_relevance_score.desc().nullslast(),
                SearchTopicPaper.provider_rank.asc().nullslast(),
            )
            .limit(limit)
            .options(selectinload(Paper.chunks))
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def upsert_association(
        self,
        *,
        search_topic_id: UUID,
        paper_id: UUID,
        semantic_relevance_score: float | None = None,
        provider_rank: int | None = None,
        discovery_source: str | None = None,
    ) -> tuple[SearchTopicPaper, bool]:
        """Create or refresh a topic↔paper link without duplicating rows.

        Preserves first_discovered_at; updates last_seen_at and optional scores.
        """
        now = datetime.now(timezone.utc)
        stmt_existing = select(SearchTopicPaper).where(
            SearchTopicPaper.search_topic_id == search_topic_id,
            SearchTopicPaper.paper_id == paper_id,
        )
        result = await self.session.execute(stmt_existing)
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.last_seen_at = now
            if semantic_relevance_score is not None:
                if (
                    existing.semantic_relevance_score is None
                    or semantic_relevance_score > existing.semantic_relevance_score
                ):
                    existing.semantic_relevance_score = semantic_relevance_score
            if provider_rank is not None:
                if (
                    existing.provider_rank is None
                    or provider_rank < existing.provider_rank
                ):
                    existing.provider_rank = provider_rank
            if discovery_source and not existing.discovery_source:
                existing.discovery_source = discovery_source
            await self.session.flush()
            return existing, False

        new_id = uuid4()
        stmt = (
            insert(SearchTopicPaper)
            .values(
                id=new_id,
                search_topic_id=search_topic_id,
                paper_id=paper_id,
                semantic_relevance_score=semantic_relevance_score,
                provider_rank=provider_rank,
                discovery_source=discovery_source,
                first_discovered_at=now,
                last_seen_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_search_topic_papers_topic_paper")
            .returning(SearchTopicPaper.id)
        )
        insert_result = await self.session.execute(stmt)
        inserted_id = insert_result.scalar_one_or_none()
        if inserted_id is not None:
            row = await self.session.get(SearchTopicPaper, inserted_id)
            assert row is not None
            return row, True

        result = await self.session.execute(stmt_existing)
        existing = result.scalar_one_or_none()
        if existing is None:
            raise RuntimeError(
                f"SearchTopicPaper upsert race unresolved for "
                f"topic={search_topic_id} paper={paper_id}"
            )
        existing.last_seen_at = now
        await self.session.flush()
        return existing, False

    async def count_for_topic(self, search_topic_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(SearchTopicPaper)
            .where(SearchTopicPaper.search_topic_id == search_topic_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
