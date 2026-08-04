from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.models.project import Project
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse


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
        topics = await self.project_paper_repo.topics_by_project(ids)
        return [
            ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                created_at=project.created_at,
                updated_at=project.updated_at,
                source_count=counts.get(project.id, 0),
                topics=topics.get(project.id, []),
            )
            for project in projects
        ]

    async def get_project(self, project_id: UUID) -> ProjectResponse:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        return await self._to_response(project)

    async def list_projects(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[ProjectResponse]:
        projects = await self.project_repo.list_all(skip=skip, limit=limit)
        return await self._to_responses(projects)

    async def create_project(self, payload: ProjectCreate) -> ProjectResponse:
        project = Project(name=payload.name, description=payload.description)
        created = await self.project_repo.create(project)
        return await self._to_response(created)

    async def delete_project(self, project_id: UUID) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        await self.project_repo.delete(project)

    async def touch_project(self, project_id: UUID) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            return
        project.updated_at = datetime.now(timezone.utc)
        await self.project_repo.update(project)
