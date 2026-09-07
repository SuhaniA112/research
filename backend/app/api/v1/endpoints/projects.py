from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import (
    AskServiceDep,
    CurrentUserDep,
    IngestionServiceDep,
    ProjectServiceDep,
)
from app.schemas.ask import AskRequest, AskResponse
from app.schemas.paper import PaperResponse, SavePaperRequest, SavePaperResponse
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, current_user: CurrentUserDep, service: ProjectServiceDep
) -> ProjectResponse:
    return await service.create_project(current_user, payload)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: CurrentUserDep,
    service: ProjectServiceDep,
    skip: int = 0,
    limit: int = 100,
) -> list[ProjectResponse]:
    return await service.list_projects(current_user, skip=skip, limit=limit)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID, current_user: CurrentUserDep, service: ProjectServiceDep
) -> ProjectResponse:
    return await service.get_project(project_id, current_user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID, current_user: CurrentUserDep, service: ProjectServiceDep
) -> Response:
    await service.delete_project(project_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/papers", response_model=list[PaperResponse])
async def list_project_papers(
    project_id: UUID,
    current_user: CurrentUserDep,
    service: IngestionServiceDep,
) -> list[PaperResponse]:
    return await service.list_papers_for_project(project_id, current_user)


@router.post(
    "/{project_id}/papers",
    response_model=SavePaperResponse,
    status_code=status.HTTP_200_OK,
)
async def save_paper(
    project_id: UUID,
    payload: SavePaperRequest,
    current_user: CurrentUserDep,
    service: IngestionServiceDep,
) -> SavePaperResponse:
    return await service.save_paper_to_project(project_id, payload.paper, current_user)


@router.delete(
    "/{project_id}/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def unsave_paper(
    project_id: UUID,
    paper_id: UUID,
    current_user: CurrentUserDep,
    service: IngestionServiceDep,
) -> Response:
    await service.unsave_paper_from_project(project_id, paper_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/ask", response_model=AskResponse)
async def ask(
    project_id: UUID,
    payload: AskRequest,
    current_user: CurrentUserDep,
    service: AskServiceDep,
) -> AskResponse:
    return await service.ask(project_id, payload.question, current_user)
