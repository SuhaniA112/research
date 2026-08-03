from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.search_topic import SearchTopic
from app.repositories.base import BaseRepository


class SearchTopicRepository(BaseRepository[SearchTopic]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SearchTopic)

    async def get_by_normalized_query(
        self, normalized_query: str
    ) -> SearchTopic | None:
        stmt = select(SearchTopic).where(
            SearchTopic.normalized_query == normalized_query
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_similar(
        self,
        query_embedding: list[float],
        *,
        max_distance: float,
        limit: int = 5,
    ) -> list[tuple[SearchTopic, float]]:
        distance = SearchTopic.embedding.cosine_distance(query_embedding)
        stmt = (
            select(SearchTopic, distance.label("distance"))
            .where(distance <= max_distance)
            .order_by(distance)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [(row[0], float(row[1])) for row in result.all()]

    async def get_or_create_by_normalized_query(
        self,
        *,
        canonical_query: str,
        normalized_query: str,
        embedding: list[float],
    ) -> tuple[SearchTopic, bool]:
        """Reuse exact normalized_query or insert a new global topic.

        Concurrent inserts for the same normalized_query resolve via
        ON CONFLICT DO NOTHING and a subsequent SELECT.
        """
        existing = await self.get_by_normalized_query(normalized_query)
        if existing is not None:
            return existing, False

        new_id = uuid4()
        stmt = (
            insert(SearchTopic)
            .values(
                id=new_id,
                canonical_query=canonical_query,
                normalized_query=normalized_query,
                embedding=embedding,
            )
            .on_conflict_do_nothing(constraint="uq_search_topics_normalized_query")
            .returning(SearchTopic.id)
        )
        result = await self.session.execute(stmt)
        inserted_id = result.scalar_one_or_none()
        if inserted_id is not None:
            topic = await self.get_by_id(inserted_id)
            assert topic is not None
            return topic, True

        topic = await self.get_by_normalized_query(normalized_query)
        if topic is None:
            raise RuntimeError(
                f"SearchTopic upsert race unresolved for {normalized_query!r}"
            )
        return topic, False

    async def mark_external_refresh(
        self, topic_id: UUID, *, result_count: int
    ) -> SearchTopic | None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(SearchTopic)
            .where(SearchTopic.id == topic_id)
            .values(
                last_external_refresh_at=now,
                external_refresh_count=SearchTopic.external_refresh_count + 1,
                last_result_count=result_count,
            )
            .returning(SearchTopic.id)
        )
        result = await self.session.execute(stmt)
        updated_id = result.scalar_one_or_none()
        if updated_id is None:
            return None
        return await self.get_by_id(updated_id)

    async def get_with_papers(self, topic_id: UUID) -> SearchTopic | None:
        stmt = (
            select(SearchTopic)
            .where(SearchTopic.id == topic_id)
            .options(selectinload(SearchTopic.topic_papers))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
