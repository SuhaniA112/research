from collections.abc import AsyncIterator
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUserDep, DiscoverySearchServiceDep, ResearchServiceDep
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
    current_user: CurrentUserDep,
) -> DiscoverySearchResponse:
    """Database-first discovery with external-provider fallback.

    Requires temporary ``X-User-ID`` so project-scoped empty searches and
    SearchExecution ownership stay user-bound. Listing another user's
    SearchExecution records must remain forbidden.
    """
    return await service.search(body, user_id=current_user.id)


@router.post("/search/stream")
async def search_research_papers_stream(
    body: DiscoverySearchRequest,
    service: DiscoverySearchServiceDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    """SSE stream of ranked discovery snapshots as providers complete.

    Events:
    - ``event: results`` — partial or final ``DiscoverySearchResponse`` JSON
    - ``event: error`` — ``{"detail": "..."}`` on unexpected failure
    """

    async def event_gen() -> AsyncIterator[str]:
        try:
            async for snapshot in service.search_stream(
                body, user_id=current_user.id
            ):
                payload = snapshot.model_dump(mode="json")
                yield f"event: results\ndata: {json.dumps(payload)}\n\n"
        except Exception as exc:
            yield (
                "event: error\ndata: "
                f"{json.dumps({'detail': str(exc)[:300]})}\n\n"
            )

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
