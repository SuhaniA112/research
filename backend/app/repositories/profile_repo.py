from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import SINGLETON_PROFILE_ID, Profile
from app.models.user import User
from app.repositories.base import BaseRepository


def _first_name(full_name: str) -> str:
    return (full_name or "").strip().split(" ")[0] or "Researcher"


class ProfileRepository(BaseRepository[Profile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Profile)

    async def get_singleton(self) -> Profile | None:
        """Legacy shared profile (pre per-user); kept for older callers."""
        return await self.get_by_id(SINGLETON_PROFILE_ID)

    async def ensure_singleton(self) -> Profile:
        """Legacy shared profile (pre per-user); kept for older callers."""
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

    async def get_for_user(self, user_id: UUID) -> Profile | None:
        result = await self.session.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def ensure_for_user(self, user: User) -> Profile:
        """Return the user's profile, creating it from their account on first use.

        Concurrent first requests (e.g. /users/me and /digest) both land here, so the
        insert ignores a duplicate instead of failing.
        """
        existing = await self.get_for_user(user.id)
        if existing is not None:
            return existing
        await self.session.execute(
            insert(Profile)
            .values(
                id=uuid4(),
                user_id=user.id,
                name=_first_name(user.full_name),
                full_name=user.full_name or "Researcher",
                email=user.email or "",
                occupation="",
                institution="",
                research_areas=[],
                keywords=[],
                reading_level="graduate",
                weekly_digest=True,
                source_notifications=False,
            )
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        profile = await self.get_for_user(user.id)
        assert profile is not None
        return profile
