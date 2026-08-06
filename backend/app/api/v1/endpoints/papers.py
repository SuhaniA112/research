from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import PaperRepoDep
from app.schemas.paper import PaperResponse

router = APIRouter()


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: UUID, paper_repo: PaperRepoDep) -> PaperResponse:
    paper = await paper_repo.get_by_id(paper_id)
    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper {paper_id} not found",
        )
    return PaperResponse.model_validate(paper)
