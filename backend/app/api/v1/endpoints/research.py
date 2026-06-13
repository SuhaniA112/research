from fastapi import APIRouter

from app.api.deps import ResearchServiceDep
from app.schemas.research_papers import SearchResponse

router = APIRouter()


@router.get("/papers", response_model=SearchResponse)
async def get_research_papers(
    service: ResearchServiceDep,
) -> SearchResponse:
    return await service.get_research_for_user()