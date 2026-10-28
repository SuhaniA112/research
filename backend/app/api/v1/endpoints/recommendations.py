from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserDep, ProjectRepoDep, RecommendationServiceDep
from app.schemas.recommendation import (
    DigestResponse,
    RecommendedPaper,
    ScoresRequest,
    ScoresResponse,
)

router = APIRouter()


@router.get("/digest", response_model=DigestResponse)
async def get_digest(
    service: RecommendationServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(default=5, ge=1, le=20),
    offset: int = Query(default=0, ge=0),
    refresh: bool = False,
) -> DigestResponse:
    """Personalised hub papers, paged."""
    return await service.digest(current_user, limit=limit, offset=offset, refresh=refresh)


@router.get("/papers/{paper_id}/related", response_model=list[RecommendedPaper])
async def get_related_papers(
    paper_id: UUID,
    service: RecommendationServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(default=5, ge=1, le=20),
) -> list[RecommendedPaper]:
    return await service.related(paper_id, limit=limit)


@router.get("/projects/{project_id}/suggestions", response_model=list[RecommendedPaper])
async def get_project_suggestions(
    project_id: UUID,
    service: RecommendationServiceDep,
    project_repo: ProjectRepoDep,
    current_user: CurrentUserDep,
    limit: int = Query(default=10, ge=1, le=30),
) -> list[RecommendedPaper]:
    """Stored papers that fit the project; no live provider search."""
    project = await project_repo.get_for_user(project_id, current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await service.project_suggestions(project, limit=limit)


@router.post("/projects/{project_id}/scores", response_model=ScoresResponse)
async def score_papers_for_project(
    project_id: UUID,
    payload: ScoresRequest,
    service: RecommendationServiceDep,
    project_repo: ProjectRepoDep,
    current_user: CurrentUserDep,
) -> ScoresResponse:
    """Relevance to the project, similarity to its saved papers, and an optional query match."""
    project = await project_repo.get_for_user(project_id, current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    scores = await service.project_scores(project, payload.paper_ids, payload.query)
    return ScoresResponse(scores=scores)
