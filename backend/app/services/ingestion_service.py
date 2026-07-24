from uuid import UUID

from fastapi import HTTPException, status

from app.models.paper import Paper
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

        existing_paper = await self.paper_repo.get_by_source_and_external_id(
            paper_in.source, paper_in.external_id
        )

        if existing_paper is not None:
            paper = existing_paper
        else:
            paper = await self.paper_repo.create(
                Paper(
                    source=paper_in.source,
                    external_id=paper_in.external_id,
                    title=paper_in.title,
                    abstract=paper_in.abstract,
                    authors=paper_in.authors,
                    year=paper_in.year,
                    url=paper_in.url,
                    pdf_url=paper_in.pdf_url,
                    topics=paper_in.topics,
                )
            )
            # Indexable Text: abstract when available, falling back to title so a paper
            # is never unembeddable just because its Source Provider has no abstract
            # (e.g. DBLP always returns abstract=None).
            indexable_text = paper_in.abstract if paper_in.abstract else paper_in.title
            [embedding] = await self.voyage_client.embed(
                [indexable_text], input_type="document"
            )
            await self.chunk_repo.create_for_paper(paper.id, indexable_text, embedding)

        _, created = await self.project_paper_repo.create_if_absent(project_id, paper.id)

        return SavePaperResponse(
            paper=PaperResponse.model_validate(paper),
            already_saved=not created,
        )

    async def unsave_paper_from_project(self, project_id: UUID, paper_id: UUID) -> bool:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        return await self.project_paper_repo.delete_if_present(project_id, paper_id)
