from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[Project]:
        stmt = (
            select(Project)
            .order_by(Project.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Project))
        return int(result.scalar_one())

    async def count_updated_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.updated_at >= since)
        )
        return int(result.scalar_one())
