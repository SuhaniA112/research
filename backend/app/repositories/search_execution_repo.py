from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search_execution import SearchExecution
from app.repositories.base import BaseRepository


class SearchExecutionRepository(BaseRepository[SearchExecution]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SearchExecution)

    async def record(
        self,
        *,
        search_topic_id: UUID,
        raw_query: str,
        normalized_query: str,
        cache_hit: bool,
        cache_miss_reason: str | None,
        external_search_performed: bool,
        force_refresh: bool,
        requested_limit: int,
        results_returned: int,
        user_id: UUID | None = None,
        anonymous_session_id: str | None = None,
    ) -> SearchExecution:
        """Persist a per-request search history row (cache hits included)."""
        execution = SearchExecution(
            search_topic_id=search_topic_id,
            raw_query=raw_query,
            normalized_query=normalized_query,
            cache_hit=cache_hit,
            cache_miss_reason=cache_miss_reason,
            external_search_performed=external_search_performed,
            force_refresh=force_refresh,
            requested_limit=requested_limit,
            results_returned=results_returned,
            user_id=user_id,
            anonymous_session_id=anonymous_session_id,
        )
        return await self.create(execution)
