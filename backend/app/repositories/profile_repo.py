from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Profile)

    async def ensure_for_user(self, user_id: str) -> Profile:
        existing = await self.get_by_id(user_id)
        if existing is not None:
            return existing
        return await self.create(
            Profile(
                id=user_id,
                occupation="",
                institution="",
                research_areas=[],
                keywords=[],
                reading_level="graduate",
                weekly_digest=True,
                source_notifications=False,
            )
        )
