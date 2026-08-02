from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import AskServiceDep, IngestionServiceDep, ProjectServiceDep
from app.schemas.ask import AskRequest, AskResponse
from app.schemas.paper import SavePaperRequest, SavePaperResponse
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, service: ProjectServiceDep) -> ProjectResponse:
    return await service.create_project(payload)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    service: ProjectServiceDep,
    skip: int = 0,
    limit: int = 100,
) -> list[ProjectResponse]:
    return await service.list_projects(skip=skip, limit=limit)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, service: ProjectServiceDep) -> ProjectResponse:
    return await service.get_project(project_id)


@router.post("/{project_id}/papers", response_model=SavePaperResponse, status_code=status.HTTP_200_OK)
async def save_paper(
    project_id: UUID,
    payload: SavePaperRequest,
    service: IngestionServiceDep,
) -> SavePaperResponse:
    return await service.save_paper_to_project(project_id, payload.paper)


@router.delete("/{project_id}/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_paper(
    project_id: UUID,
    paper_id: UUID,
    service: IngestionServiceDep,
) -> Response:
    await service.unsave_paper_from_project(project_id, paper_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/ask", response_model=AskResponse)
async def ask(project_id: UUID, payload: AskRequest, service: AskServiceDep) -> AskResponse:
    return await service.ask(project_id, payload.question)
