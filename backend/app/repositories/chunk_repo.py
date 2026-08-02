from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chunk import Chunk
from app.models.paper import Paper
from app.models.project_paper import ProjectPaper
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Chunk)

    async def create_for_paper(
        self, paper_id: UUID, text: str, embedding: list[float]
    ) -> Chunk:
        chunk = Chunk(paper_id=paper_id, chunk_index=0, text=text, embedding=embedding)
        return await self.create(chunk)

    async def get_for_paper(
        self, paper_id: UUID, *, chunk_index: int = 0
    ) -> Chunk | None:
        stmt = select(Chunk).where(
            Chunk.paper_id == paper_id, Chunk.chunk_index == chunk_index
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def ensure_chunk_for_paper(
        self,
        paper_id: UUID,
        text: str,
        embedding: list[float],
        *,
        chunk_index: int = 0,
    ) -> tuple[Chunk, bool]:
        """Create chunk_index=0 if absent; skip when identical text already embedded.

        On unique-constraint races, reloads the existing row. Returns (chunk, created).
        If the stored text differs meaningfully from the new indexable text, updates
        text + embedding in place (deliberate re-embed strategy for content changes).
        """
        existing = await self.get_for_paper(paper_id, chunk_index=chunk_index)
        if existing is not None:
            if existing.text == text:
                return existing, False
            existing.text = text
            existing.embedding = embedding
            await self.session.flush()
            await self.session.refresh(existing)
            return existing, False

        new_id = uuid4()
        stmt = (
            insert(Chunk)
            .values(
                id=new_id,
                paper_id=paper_id,
                chunk_index=chunk_index,
                text=text,
                embedding=embedding,
            )
            .on_conflict_do_nothing(constraint="uq_chunks_paper_id_chunk_index")
            .returning(Chunk.id)
        )
        result = await self.session.execute(stmt)
        inserted_id = result.scalar_one_or_none()
        if inserted_id is not None:
            chunk = await self.get_by_id(inserted_id)
            assert chunk is not None
            return chunk, True

        existing = await self.get_for_paper(paper_id, chunk_index=chunk_index)
        if existing is None:
            raise RuntimeError(f"Chunk upsert race unresolved for paper {paper_id}")
        if existing.text != text:
            existing.text = text
            existing.embedding = embedding
            await self.session.flush()
            await self.session.refresh(existing)
        return existing, False

    async def search_by_project(
        self,
        project_id: UUID,
        query_embedding: list[float],
        *,
        max_distance: float,
        top_k: int,
    ) -> list[tuple[Chunk, float]]:
        """Retrieval: vector similarity search over Chunks, scoped to one Project
        via the ProjectPaper join. Never queries across Projects. Postgres applies
        the distance threshold in the WHERE clause rather than filtering in the app.
        """
        distance = Chunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(Chunk, distance.label("distance"))
            .join(Paper, Chunk.paper_id == Paper.id)
            .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
            .where(ProjectPaper.project_id == project_id)
            .where(distance <= max_distance)
            .order_by(distance)
            .limit(top_k)
            .options(selectinload(Chunk.paper))
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def search_global(
        self,
        query_embedding: list[float],
        *,
        max_distance: float,
        limit: int,
    ) -> list[tuple[Paper, float]]:
        """Global paper-vector search (not Project-scoped).

        Aggregates by Paper: when a paper has multiple chunks, keeps the best
        (lowest) cosine distance. Returns (Paper, distance) ordered by distance.
        """
        distance = Chunk.embedding.cosine_distance(query_embedding)
        fetch_limit = max(limit * 4, limit)
        stmt = (
            select(Chunk, distance.label("distance"))
            .where(distance <= max_distance)
            .order_by(distance)
            .limit(fetch_limit)
            .options(selectinload(Chunk.paper))
        )
        result = await self.session.execute(stmt)

        best_by_paper: dict[UUID, tuple[Paper, float]] = {}
        for chunk, dist in result.all():
            paper = chunk.paper
            current = best_by_paper.get(paper.id)
            if current is None or dist < current[1]:
                best_by_paper[paper.id] = (paper, float(dist))

        ranked = sorted(best_by_paper.values(), key=lambda item: item[1])
        return ranked[:limit]
