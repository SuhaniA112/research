import logging
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_embedding import ProjectEmbedding


logger = logging.getLogger(__name__)


class ProjectEmbeddingRepository:
    """Savepoints keep a missing table (migration not run) from failing the request."""
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, project_id: UUID) -> ProjectEmbedding | None:
        try:
            async with self.session.begin_nested():
                return await self.session.get(ProjectEmbedding, project_id)
        except ProgrammingError:
            logger.warning("project_embeddings table missing; run `alembic upgrade head`")
            return None

    async def upsert(self, project_id: UUID, text: str, embedding: list[float]) -> None:
        stmt = insert(ProjectEmbedding).values(project_id=project_id, text=text, embedding=embedding)
        stmt = stmt.on_conflict_do_update(
            index_elements=["project_id"],
            set_={"text": stmt.excluded.text, "embedding": stmt.excluded.embedding},
        )
        try:
            async with self.session.begin_nested():
                await self.session.execute(stmt)
        except ProgrammingError:
            logger.warning("project_embeddings table missing; run `alembic upgrade head`")
