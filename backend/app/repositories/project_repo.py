from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def list_all(
        self, user_id: str, *, skip: int = 0, limit: int = 100
    ) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_owned_by_id(self, project_id: UUID, user_id: str) -> Project | None:
        project = await self.get_by_id(project_id)
        if project is None or project.user_id != user_id:
            return None
        return project

    async def count_all(self, user_id: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Project).where(Project.user_id == user_id)
        )
        return int(result.scalar_one())

    async def count_updated_since(self, user_id: str, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.user_id == user_id, Project.updated_at >= since)
        )
        return int(result.scalar_one())
