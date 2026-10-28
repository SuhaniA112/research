"""ProfileService: per-user profile and user-scoped stats."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileUpdate
from app.services.profile_service import ProfileService

JAN = datetime(2024, 1, 15, tzinfo=timezone.utc)


def _user() -> User:
    return User(
        id=uuid4(),
        email="sam@example.com",
        full_name="Sam Lee",
        hashed_password="x",
        is_active=True,
        created_at=JAN,
        updated_at=JAN,
    )


def _profile(user: User, **overrides: object) -> Profile:
    base = dict(
        id=uuid4(),
        user_id=user.id,
        name="Sam",
        full_name="Sam Lee",
        email="sam@example.com",
        occupation="Student",
        institution="Cornell",
        research_areas=["HCI"],
        keywords=["LLM"],
        reading_level="graduate",
        weekly_digest=True,
        source_notifications=False,
        created_at=JAN,
        updated_at=JAN,
    )
    base.update(overrides)
    return Profile(**base)  # type: ignore[arg-type]


def _repos(profile: Profile, *, projects=3, active=1, saved=7):
    profile_repo = AsyncMock()
    profile_repo.ensure_for_user.return_value = profile
    profile_repo.update.side_effect = lambda p: p
    project_repo = AsyncMock()
    project_repo.count_for_user.return_value = projects
    project_repo.count_updated_since_for_user.return_value = active
    project_paper_repo = AsyncMock()
    project_paper_repo.count_distinct_papers_for_user.return_value = saved
    return profile_repo, project_repo, project_paper_repo


@pytest.mark.asyncio
async def test_get_me_is_scoped_to_the_user() -> None:
    user = _user()
    profile_repo, project_repo, project_paper_repo = _repos(_profile(user))
    service = ProfileService(profile_repo, project_repo, project_paper_repo)

    result = await service.get_me(user)

    profile_repo.ensure_for_user.assert_awaited_once_with(user)
    project_repo.count_for_user.assert_awaited_once_with(user.id)
    project_paper_repo.count_distinct_papers_for_user.assert_awaited_once_with(user.id)
    assert result.name == "Sam"
    assert result.member_since == "Jan 2024"
    assert (result.projects_count, result.sources_saved, result.active_projects_this_month) == (3, 7, 1)


@pytest.mark.asyncio
async def test_update_me_persists_patch() -> None:
    user = _user()
    profile = _profile(user)
    profile_repo, project_repo, project_paper_repo = _repos(profile)
    service = ProfileService(profile_repo, project_repo, project_paper_repo)

    result = await service.update_me(
        user, ProfileUpdate(reading_level="casual", research_areas=["AI/ML"])
    )

    assert profile.reading_level == "casual"
    assert profile.research_areas == ["AI/ML"]
    assert result.reading_level == "casual"
    profile_repo.update.assert_awaited_once()
