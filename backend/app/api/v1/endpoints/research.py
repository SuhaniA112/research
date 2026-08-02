from fastapi import APIRouter

from app.api.deps import DiscoverySearchServiceDep, ResearchServiceDep
from app.schemas.research_discovery import (
    DiscoverySearchRequest,
    DiscoverySearchResponse,
)
from app.schemas.research_papers import SearchResponse

router = APIRouter()


@router.get("/papers", response_model=SearchResponse)
async def get_research_papers(
    service: ResearchServiceDep,
) -> SearchResponse:
    """Legacy interest-based discovery that always queries external providers."""
    return await service.get_research_for_user()


@router.post("/search", response_model=DiscoverySearchResponse)
async def search_research_papers(
    body: DiscoverySearchRequest,
    service: DiscoverySearchServiceDep,
) -> DiscoverySearchResponse:
    """Database-first discovery with external-provider fallback.

    Authorization: when authentication exists, pass the authenticated user_id into
    the service so SearchExecution rows are owned correctly. Listing another user's
    SearchExecution records must remain forbidden.
    """
    return await service.search(body)
