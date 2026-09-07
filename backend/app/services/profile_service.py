from datetime import datetime, timezone

from app.core.auth import CurrentUser, get_display_identity
from app.models.profile import Profile
from app.repositories.profile_repo import ProfileRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.profile import ProfileResponse, ProfileUpdate


def _format_member_since(created_at: datetime | None) -> str:
    if created_at is None:
        return ""
    return created_at.strftime("%b %Y")


class ProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        project_repo: ProjectRepository,
        project_paper_repo: ProjectPaperRepository,
    ) -> None:
        self.profile_repo = profile_repo
        self.project_repo = project_repo
        self.project_paper_repo = project_paper_repo

    async def get_me(self, current_user: CurrentUser) -> ProfileResponse:
        profile = await self.profile_repo.ensure_for_user(current_user.id)
        return await self._to_response(profile, current_user)

    async def update_me(
        self, current_user: CurrentUser, payload: ProfileUpdate
    ) -> ProfileResponse:
        profile = await self.profile_repo.ensure_for_user(current_user.id)
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        updated = await self.profile_repo.update(profile)
        return await self._to_response(updated, current_user)

    async def _to_response(
        self, profile: Profile, current_user: CurrentUser
    ) -> ProfileResponse:
        identity = await get_display_identity(current_user)
        projects_count = await self.project_repo.count_all(current_user.id)
        sources_saved = await self.project_paper_repo.count_distinct_papers(
            current_user.id
        )
        active = await self.project_repo.count_updated_since(
            current_user.id, _month_start_utc()
        )
        return ProfileResponse(
            name=identity.name,
            full_name=identity.full_name,
            email=identity.email,
            occupation=profile.occupation,
            institution=profile.institution,
            member_since=_format_member_since(profile.created_at),
            research_areas=list(profile.research_areas or []),
            keywords=list(profile.keywords or []),
            reading_level=profile.reading_level,  # type: ignore[arg-type]
            sources_saved=sources_saved,
            projects_count=projects_count,
            active_projects_this_month=active,
            # Notes stay client-side until a notes API exists.
            notes_written=0,
            last_note_days_ago=0,
            weekly_digest=profile.weekly_digest,
            source_notifications=profile.source_notifications,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )


def _month_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)
