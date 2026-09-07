from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.models.project import Project
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services.query_normalization import normalize_topic_list


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        project_paper_repo: ProjectPaperRepository,
    ) -> None:
        self.project_repo = project_repo
        self.project_paper_repo = project_paper_repo

    async def _to_response(self, project: Project) -> ProjectResponse:
        return (await self._to_responses([project]))[0]

    async def _to_responses(self, projects: list[Project]) -> list[ProjectResponse]:
        if not projects:
            return []
        ids = [project.id for project in projects]
        counts = await self.project_paper_repo.count_papers_by_project(ids)
        paper_topics = await self.project_paper_repo.topics_by_project(ids)
        return [
            ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                created_at=project.created_at,
                updated_at=project.updated_at,
                source_count=counts.get(project.id, 0),
                # Prefer interest-profile topics; fall back to tags on saved papers.
                topics=project.topics or paper_topics.get(project.id, []),
                keywords=project.keywords or [],
                reading_level=project.reading_level  # validated on create
                if project.reading_level in ("casual", "graduate", "expert")
                else "graduate",
            )
            for project in projects
        ]

    async def get_project(self, project_id: UUID, user_id: UUID) -> ProjectResponse:
        project = await self.project_repo.get_for_user(project_id, user_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        return await self._to_response(project)

    async def get_project_entity(self, project_id: UUID, user_id: UUID) -> Project:
        """User-scoped project row lookup; 404 when missing or not owned."""
        project = await self.project_repo.get_for_user(project_id, user_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        return project

    async def list_projects(
        self, user_id: UUID, *, skip: int = 0, limit: int = 100
    ) -> list[ProjectResponse]:
        projects = await self.project_repo.list_for_user(
            user_id, skip=skip, limit=limit
        )
        return await self._to_responses(projects)

    async def create_project(
        self, payload: ProjectCreate, user_id: UUID
    ) -> ProjectResponse:
        project = Project(
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            topics=normalize_topic_list(list(payload.topics)),
            keywords=normalize_topic_list(list(payload.keywords)),
            reading_level=payload.reading_level,
        )
        if not project.topics:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Project must include at least one topic",
            )
        created = await self.project_repo.create(project)
        return await self._to_response(created)

    async def delete_project(self, project_id: UUID, user_id: UUID) -> None:
        project = await self.project_repo.get_for_user(project_id, user_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        await self.project_repo.delete(project)

    async def touch_project(self, project_id: UUID, user_id: UUID) -> None:
        project = await self.project_repo.get_for_user(project_id, user_id)
        if project is None:
            return
        project.updated_at = datetime.now(timezone.utc)
        await self.project_repo.update(project)
