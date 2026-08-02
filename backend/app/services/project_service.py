from uuid import UUID

from fastapi import HTTPException, status

from app.models.project import Project
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse


class ProjectService:
    def __init__(self, project_repo: ProjectRepository) -> None:
        self.project_repo = project_repo

    async def get_project(self, project_id: UUID) -> ProjectResponse:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        return ProjectResponse.model_validate(project)

    async def list_projects(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[ProjectResponse]:
        projects = await self.project_repo.list_all(skip=skip, limit=limit)
        return [ProjectResponse.model_validate(project) for project in projects]

    async def create_project(self, payload: ProjectCreate) -> ProjectResponse:
        project = Project(name=payload.name, description=payload.description)
        created = await self.project_repo.create(project)
        return ProjectResponse.model_validate(created)
