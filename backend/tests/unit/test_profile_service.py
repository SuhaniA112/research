"""Unit tests for ProfileService response mapping / updates."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.auth import CurrentUser
from app.models.profile import Profile
from app.schemas.profile import ProfileUpdate
from app.services.profile_service import ProfileService

_USER_ID = "user_test_profile"


def _profile(**overrides: object) -> Profile:
    base = dict(
        id=_USER_ID,
        occupation="Student",
        institution="Cornell",
        research_areas=["HCI"],
        keywords=["LLM"],
        reading_level="graduate",
        weekly_digest=True,
        source_notifications=False,
        created_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return Profile(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_get_me_computes_stats() -> None:
    current_user = CurrentUser(id=_USER_ID)
    profile_repo = AsyncMock()
    profile_repo.ensure_for_user.return_value = _profile()
    project_repo = AsyncMock()
    project_repo.count_all.return_value = 3
    project_repo.count_updated_since.return_value = 1
    project_paper_repo = AsyncMock()
    project_paper_repo.count_distinct_papers.return_value = 7

    service = ProfileService(profile_repo, project_repo, project_paper_repo)
    result = await service.get_me(current_user)

    # In AUTH_MODE=mock, display identity is a fixed sentinel (never stored locally).
    assert result.name == "Researcher"
    assert result.member_since == "Jan 2024"
    assert result.projects_count == 3
    assert result.sources_saved == 7
    assert result.active_projects_this_month == 1
    assert result.notes_written == 0


@pytest.mark.asyncio
async def test_update_me_persists_patch() -> None:
    current_user = CurrentUser(id=_USER_ID)
    profile = _profile()
    profile_repo = AsyncMock()
    profile_repo.ensure_for_user.return_value = profile
    profile_repo.update.side_effect = lambda p: p
    project_repo = AsyncMock()
    project_repo.count_all.return_value = 0
    project_repo.count_updated_since.return_value = 0
    project_paper_repo = AsyncMock()
    project_paper_repo.count_distinct_papers.return_value = 0

    service = ProfileService(profile_repo, project_repo, project_paper_repo)
    result = await service.update_me(
        current_user,
        ProfileUpdate(reading_level="casual", research_areas=["AI/ML"]),
    )

    assert profile.reading_level == "casual"
    assert profile.research_areas == ["AI/ML"]
    assert result.reading_level == "casual"
    profile_repo.update.assert_awaited_once()
