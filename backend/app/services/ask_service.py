import logging
import re
from uuid import UUID

from fastapi import HTTPException, status

from app.models.chunk import Chunk
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.ask import AskResponse, Citation
from app.services.embeddings.voyage_client import VoyageEmbeddingClient
from app.services.generation.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

_CITATIONS_PATTERN = re.compile(r"CITATIONS:\s*\[(.*?)\]", re.IGNORECASE | re.DOTALL)
_UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


class AskService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        chunk_repo: ChunkRepository,
        voyage_client: VoyageEmbeddingClient,
        openrouter_client: OpenRouterClient,
        *,
        max_distance: float,
        top_k: int,
        ann_overfetch: int = 50,
    ) -> None:
        self.project_repo = project_repo
        self.chunk_repo = chunk_repo
        self.voyage_client = voyage_client
        self.openrouter_client = openrouter_client
        self.max_distance = max_distance
        self.top_k = top_k
        self.ann_overfetch = ann_overfetch

    async def ask(
        self,
        project_id: UUID,
        question: str,
        *,
        user_id: UUID,
        debug: bool = False,
    ) -> AskResponse | tuple[AskResponse, list[UUID]]:
        project = await self.project_repo.get_for_user(project_id, user_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        [query_embedding] = await self.voyage_client.embed(
            [question], input_type="query"
        )
        results = await self.chunk_repo.search_by_project(
            project_id,
            query_embedding,
            max_distance=self.max_distance,
            top_k=self.top_k,
            candidate_multiplier=self.ann_overfetch,
        )

        retrieved_chunk_ids = [chunk.id for chunk, _ in results]

        if not results:
            response = AskResponse(
                status="no_relevant_sources", answer=None, citations=[]
            )
            return (response, retrieved_chunk_ids) if debug else response

        messages = self._build_prompt(question, results)
        raw_answer = await self.openrouter_client.chat_completion(messages)
        answer_text, cited_chunk_ids = self._parse_citations(raw_answer)
        citations = self._resolve_citations(cited_chunk_ids, results)

        response = AskResponse(
            status="answered", answer=answer_text, citations=citations
        )
        return (response, retrieved_chunk_ids) if debug else response

    def _build_prompt(
        self, question: str, results: list[tuple[Chunk, float]]
    ) -> list[dict[str, str]]:
        numbered_sources = "\n\n".join(
            f"[{i}] chunk_id={chunk.id}\nTitle: {chunk.paper.title}\nText: {chunk.text}"
            for i, (chunk, _distance) in enumerate(results, start=1)
        )
        system = (
            "You answer questions using only the numbered sources provided. "
            "Do not use outside knowledge. If the sources don't answer the "
            "question, say so. "
            "After your answer, on its own line, list the chunk_id of every "
            "source you actually used in this exact format: "
            "CITATIONS: [<chunk_id>, <chunk_id>, ...]"
        )
        user = f"Sources:\n\n{numbered_sources}\n\nQuestion: {question}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _parse_citations(self, raw_answer: str) -> tuple[str, list[UUID]]:
        match = _CITATIONS_PATTERN.search(raw_answer)
        if match is None:
            logger.warning("OpenRouter response had no parseable CITATIONS block")
            return raw_answer.strip(), []

        answer_text = raw_answer[: match.start()].strip()
        cited_ids = []
        for raw_id in _UUID_PATTERN.findall(match.group(1)):
            try:
                cited_ids.append(UUID(raw_id))
            except ValueError:
                continue

        if not cited_ids:
            logger.warning(
                "OpenRouter response had an empty/unparseable CITATIONS block"
            )

        return answer_text, cited_ids

    def _resolve_citations(
        self, cited_chunk_ids: list[UUID], results: list[tuple[Chunk, float]]
    ) -> list[Citation]:
        by_id = {chunk.id: (chunk, distance) for chunk, distance in results}
        citations = []

        for chunk_id in cited_chunk_ids:
            found = by_id.get(chunk_id)
            if found is None:
                # Model cited a chunk_id outside the retrieved set — ignore.
                continue
            chunk, distance = found
            citations.append(
                Citation(
                    paper_id=chunk.paper_id,
                    chunk_id=chunk.id,
                    title=chunk.paper.title,
                    url=chunk.paper.url,
                    page_number=chunk.page_number,
                    distance=distance,
                )
            )

        return citations
