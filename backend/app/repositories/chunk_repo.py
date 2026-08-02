from uuid import UUID

from sqlalchemy import select
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

    async def search_by_project(
        self,
        project_id: UUID,
        query_embedding: list[float],
        *,
        max_distance: float,
        top_k: int,
    ) -> list[tuple[Chunk, float]]:
        """Retrieval: vector similarity search over Chunks, scoped to a single Project via
        the ProjectPaper join. Never queries across Projects. Postgres applies the distance
        threshold in the WHERE clause rather than filtering in the app.
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
