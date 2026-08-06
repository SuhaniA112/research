from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import SINGLETON_PROFILE_ID, Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Profile)

    async def get_singleton(self) -> Profile | None:
        return await self.get_by_id(SINGLETON_PROFILE_ID)

    async def ensure_singleton(self) -> Profile:
        existing = await self.get_singleton()
        if existing is not None:
            return existing
        return await self.create(
            Profile(
                id=SINGLETON_PROFILE_ID,
                name="Alex",
                full_name="Alex Chen",
                email="alex@example.com",
                occupation="Graduate Student",
                institution="Cornell University",
                research_areas=["AI/ML", "HCI", "Assistive Tech"],
                keywords=["LLM", "GenAI"],
                reading_level="graduate",
                weekly_digest=True,
                source_notifications=False,
            )
        )
