from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
from app.repositories.base import BaseRepository


class PaperRepository(BaseRepository[Paper]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Paper)

    async def get_by_source_and_external_id(
        self, source: str, external_id: str
    ) -> Paper | None:
        stmt = select(Paper).where(
            Paper.source == source, Paper.external_id == external_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
