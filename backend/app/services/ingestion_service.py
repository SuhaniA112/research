import logging
from datetime import datetime, timezone
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
from app.services.indexing.paper_indexer import PaperIndexer
from app.services.summarization.paper_summarizer import PaperSummarizer

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        paper_repo: PaperRepository,
        chunk_repo: ChunkRepository,
        project_paper_repo: ProjectPaperRepository,
        project_repo: ProjectRepository,
        voyage_client: VoyageEmbeddingClient,
        paper_indexer: PaperIndexer,
        paper_summarizer: PaperSummarizer,
    ) -> None:
        self.paper_repo = paper_repo
        self.chunk_repo = chunk_repo
        self.project_paper_repo = project_paper_repo
        self.project_repo = project_repo
        self.voyage_client = voyage_client
        self.paper_indexer = paper_indexer
        self.paper_summarizer = paper_summarizer

    async def save_paper_to_project(
        self, project_id: UUID, paper_in: IndPaper, user_id: UUID
    ) -> SavePaperResponse:
        project = await self.project_repo.get_for_user(project_id, user_id)
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

        # Always link to the project first so save succeeds even when Voyage/indexing
        # fails (common with bad keys / network). Multi-project saves depend on this.
        _, link_created = await self.project_paper_repo.create_if_absent(
            project_id, paper.id
        )
        if link_created:
            project.updated_at = datetime.now(timezone.utc)
            await self.project_repo.update(project)

        should_index = paper_created
        if not should_index:
            existing_chunk = await self.chunk_repo.get_for_paper(paper.id)
            should_index = existing_chunk is None

        if should_index and self.voyage_client.api_key:
            try:
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
            except Exception as exc:  # noqa: BLE001 — never fail save on indexing
                logger.warning(
                    "Indexing failed for paper %s during save; link kept: %s",
                    paper.id,
                    exc,
                )

        return SavePaperResponse(
            paper=PaperResponse.model_validate(paper),
            already_saved=not link_created,
        )

    async def upsert_and_summarize(self, paper_in: IndPaper) -> PaperResponse:
        """Persist a paper (no project link) and generate leveled summaries."""
        if paper_in.external_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paper is missing a stable external_id",
            )
        paper, _ = await self.paper_repo.upsert_from_ind_paper(paper_in)
        paper = await self.ensure_summaries(paper)
        return PaperResponse.model_validate(paper)

    async def get_paper_with_summaries(self, paper_id: UUID) -> PaperResponse:
        paper = await self.paper_repo.get_by_id(paper_id)
        if paper is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper {paper_id} not found",
            )
        paper = await self.ensure_summaries(paper)
        return PaperResponse.model_validate(paper)

    async def ensure_summaries(self, paper: Paper) -> Paper:
        """Generate and persist leveled summaries when missing. Soft-fails."""
        has_all = bool(
            paper.summary_general and paper.summary_graduate and paper.summary_expert
        )
        if has_all:
            return paper

        chunks = await self.chunk_repo.list_for_paper(paper.id)
        source_text = "\n\n".join(chunk.text for chunk in chunks if chunk.text)
        if not source_text.strip():
            source_text = (paper.abstract or paper.title or "").strip()
        if not source_text:
            return paper

        try:
            result = await self.paper_summarizer.summarize(
                title=paper.title,
                source_text=source_text,
            )
        except Exception as exc:  # noqa: BLE001 — never fail save/get on summary
            logger.warning("ensure_summaries raised for paper %s: %s", paper.id, exc)
            return paper

        if result is None:
            return paper

        paper.summary_general = result.general
        paper.summary_graduate = result.graduate
        paper.summary_expert = result.expert
        paper.key_findings = result.key_findings
        await self.paper_repo.update(paper)
        return paper

    async def list_papers_for_project(
        self, project_id: UUID, user_id: UUID
    ) -> list[PaperResponse]:
        project = await self.project_repo.get_for_user(project_id, user_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        papers = await self.project_paper_repo.list_papers_for_project(project_id)
        return [PaperResponse.model_validate(paper) for paper in papers]

    async def unsave_paper_from_project(
        self, project_id: UUID, paper_id: UUID, user_id: UUID
    ) -> bool:
        project = await self.project_repo.get_for_user(project_id, user_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )
        deleted = await self.project_paper_repo.delete_if_present(project_id, paper_id)
        if deleted:
            project.updated_at = datetime.now(timezone.utc)
            await self.project_repo.update(project)
        return deleted
