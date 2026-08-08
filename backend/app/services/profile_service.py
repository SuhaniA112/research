from datetime import datetime, timezone

from app.models.profile import Profile
from app.repositories.profile_repo import ProfileRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.query_normalization import normalize_topic_list


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

    async def get_me(self) -> ProfileResponse:
        profile = await self.profile_repo.ensure_singleton()
        return await self._to_response(profile)

    async def update_me(self, payload: ProfileUpdate) -> ProfileResponse:
        profile = await self.profile_repo.ensure_singleton()
        update_data = payload.model_dump(exclude_unset=True)
        if "research_areas" in update_data and update_data["research_areas"] is not None:
            update_data["research_areas"] = normalize_topic_list(
                list(update_data["research_areas"])
            )
        if "keywords" in update_data and update_data["keywords"] is not None:
            update_data["keywords"] = normalize_topic_list(
                list(update_data["keywords"])
            )
        for field, value in update_data.items():
            setattr(profile, field, value)
        updated = await self.profile_repo.update(profile)
        return await self._to_response(updated)

    async def _to_response(self, profile: Profile) -> ProfileResponse:
        projects_count = await self.project_repo.count_all()
        sources_saved = await self.project_paper_repo.count_distinct_papers()
        active = await self.project_repo.count_updated_since(_month_start_utc())
        return ProfileResponse(
            name=profile.name,
            full_name=profile.full_name,
            email=profile.email,
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
