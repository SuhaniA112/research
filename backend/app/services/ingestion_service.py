from uuid import UUID

from fastapi import HTTPException, status

from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.paper import PaperResponse, SavePaperResponse
from app.schemas.research_papers import IndPaper
from app.services.embeddings.voyage_client import VoyageEmbeddingClient


class IngestionService:
    def __init__(
        self,
        paper_repo: PaperRepository,
        chunk_repo: ChunkRepository,
        project_paper_repo: ProjectPaperRepository,
        project_repo: ProjectRepository,
        voyage_client: VoyageEmbeddingClient,
    ) -> None:
        self.paper_repo = paper_repo
        self.chunk_repo = chunk_repo
        self.project_paper_repo = project_paper_repo
        self.project_repo = project_repo
        self.voyage_client = voyage_client

    async def save_paper_to_project(
        self, project_id: UUID, paper_in: IndPaper
    ) -> SavePaperResponse:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        if paper_in.external_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paper is missing a stable external_id and cannot be saved",
            )

        paper, created = await self.paper_repo.upsert_from_ind_paper(paper_in)

        if created:
            # Indexable Text: abstract when available, falling back to title so a paper
            # is never unembeddable just because its Source Provider has no abstract
            # (e.g. DBLP always returns abstract=None).
            indexable_text = paper_in.abstract if paper_in.abstract else paper_in.title
            [embedding] = await self.voyage_client.embed(
                [indexable_text], input_type="document"
            )
            await self.chunk_repo.ensure_chunk_for_paper(
                paper.id, indexable_text, embedding
            )
        else:
            # Reuse existing paper — only embed if it somehow lacks a chunk.
            existing_chunk = await self.chunk_repo.get_for_paper(paper.id)
            if existing_chunk is None:
                indexable_text = paper.abstract if paper.abstract else paper.title
                [embedding] = await self.voyage_client.embed(
                    [indexable_text], input_type="document"
                )
                await self.chunk_repo.ensure_chunk_for_paper(
                    paper.id, indexable_text, embedding
                )

        _, link_created = await self.project_paper_repo.create_if_absent(
            project_id, paper.id
        )

        return SavePaperResponse(
            paper=PaperResponse.model_validate(paper),
            already_saved=not link_created,
        )

    async def unsave_paper_from_project(self, project_id: UUID, paper_id: UUID) -> bool:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        return await self.project_paper_repo.delete_if_present(project_id, paper_id)
