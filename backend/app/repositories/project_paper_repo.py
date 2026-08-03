from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_paper import ProjectPaper


class ProjectPaperRepository:
    """Not a BaseRepository[ModelT] subclass: ProjectPaper has a composite primary key,
    which BaseRepository.get_by_id(entity_id: UUID) isn't shaped for.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, project_id: UUID, paper_id: UUID) -> ProjectPaper | None:
        return await self.session.get(ProjectPaper, (project_id, paper_id))

    async def create_if_absent(
        self, project_id: UUID, paper_id: UUID
    ) -> tuple[ProjectPaper, bool]:
        existing = await self.get(project_id, paper_id)
        if existing is not None:
            return existing, False

        stmt = (
            insert(ProjectPaper)
            .values(project_id=project_id, paper_id=paper_id)
            .on_conflict_do_nothing()
            .returning(ProjectPaper.project_id, ProjectPaper.paper_id)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is not None:
            created = await self.get(project_id, paper_id)
            assert created is not None
            return created, True

        existing = await self.get(project_id, paper_id)
        if existing is None:
            raise RuntimeError(
                f"ProjectPaper upsert race unresolved for "
                f"project={project_id} paper={paper_id}"
            )
        return existing, False

    async def delete_if_present(self, project_id: UUID, paper_id: UUID) -> bool:
        existing = await self.get(project_id, paper_id)
        if existing is None:
            return False

        await self.session.delete(existing)
        await self.session.flush()
        return True
