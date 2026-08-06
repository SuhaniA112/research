from uuid import UUID

from fastapi import APIRouter

from app.api.deps import IngestionServiceDep
from app.schemas.paper import PaperResponse, SavePaperRequest

router = APIRouter()


@router.post("/summarize", response_model=PaperResponse)
async def summarize_paper(
    payload: SavePaperRequest,
    service: IngestionServiceDep,
) -> PaperResponse:
    """Upsert a paper and generate leveled summaries (no project save required)."""
    return await service.upsert_and_summarize(payload.paper)


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: UUID, service: IngestionServiceDep
) -> PaperResponse:
    return await service.get_paper_with_summaries(paper_id)
