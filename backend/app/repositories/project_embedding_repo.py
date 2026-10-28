from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_embedding import ProjectEmbedding


class ProjectEmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, project_id: UUID) -> ProjectEmbedding | None:
        return await self.session.get(ProjectEmbedding, project_id)

    async def upsert(self, project_id: UUID, text: str, embedding: list[float]) -> None:
        stmt = insert(ProjectEmbedding).values(project_id=project_id, text=text, embedding=embedding)
        stmt = stmt.on_conflict_do_update(
            index_elements=["project_id"],
            set_={"text": stmt.excluded.text, "embedding": stmt.excluded.embedding},
        )
        await self.session.execute(stmt)
