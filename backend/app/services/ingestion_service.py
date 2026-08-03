from uuid import UUID

from fastapi import HTTPException, status

from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.paper import PaperResponse, SavePaperResponse
from app.schemas.research_papers import IndPaper
from app.services.embeddings.voyage_client import VoyageEmbeddingClient
from app.services.indexing.paper_indexer import PaperIndexer


class IngestionService:
    def __init__(
        self,
        paper_repo: PaperRepository,
        chunk_repo: ChunkRepository,
        project_paper_repo: ProjectPaperRepository,
        project_repo: ProjectRepository,
        voyage_client: VoyageEmbeddingClient,
        paper_indexer: PaperIndexer,
    ) -> None:
        self.paper_repo = paper_repo
        self.chunk_repo = chunk_repo
        self.project_paper_repo = project_paper_repo
        self.project_repo = project_repo
        self.voyage_client = voyage_client
        self.paper_indexer = paper_indexer

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

        paper, paper_created = await self.paper_repo.upsert_from_ind_paper(paper_in)

        should_index = paper_created
        if not should_index:
            # Reuse existing paper — only embed if it somehow lacks a chunk.
            existing_chunk = await self.chunk_repo.get_for_paper(paper.id)
            should_index = existing_chunk is None

        if should_index:
            prepared_chunks = await self.paper_indexer.prepare_chunks(
                str(paper.id), paper_in
            )
            if prepared_chunks:
                embeddings = await self.voyage_client.embed(
                    [chunk.embedding_text for chunk in prepared_chunks],
                    input_type="document",
                )
                await self.chunk_repo.create_many_for_paper(
                    paper.id, prepared_chunks, embeddings
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
