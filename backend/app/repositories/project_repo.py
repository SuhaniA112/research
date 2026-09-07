from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def get_for_user(self, project_id: UUID, user_id: UUID) -> Project | None:
        """Return the project only when it belongs to ``user_id``."""
        stmt = select(Project).where(
            Project.id == project_id,
            Project.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: UUID, *, skip: int = 0, limit: int = 100
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

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[Project]:
        """Unscoped listing — prefer ``list_for_user`` for API access."""
        stmt = (
            select(Project)
            .order_by(Project.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_user(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.user_id == user_id)
        )
        return int(result.scalar_one())

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

    async def count_updated_since_for_user(
        self, user_id: UUID, since: datetime
    ) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.user_id == user_id, Project.updated_at >= since)
        )
        return int(result.scalar_one())
