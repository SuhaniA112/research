from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserDep, ProjectRepoDep, RecommendationServiceDep
from app.schemas.recommendation import (
    DigestResponse,
    RecommendedPaper,
    SimilarityRequest,
    SimilarityResponse,
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


@router.post("/projects/{project_id}/similarity", response_model=SimilarityResponse)
async def get_similarity_to_saved(
    project_id: UUID,
    payload: SimilarityRequest,
    service: RecommendationServiceDep,
    project_repo: ProjectRepoDep,
    current_user: CurrentUserDep,
) -> SimilarityResponse:
    """How close each paper is to the project's saved papers."""
    if await project_repo.get_for_user(project_id, current_user.id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    scores = await service.similarity_to_saved(project_id, payload.paper_ids)
    return SimilarityResponse(scores=scores)
