from uuid import UUID

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

        row = ProjectPaper(project_id=project_id, paper_id=paper_id)
        self.session.add(row)
        await self.session.flush()
        return row, True

    async def delete_if_present(self, project_id: UUID, paper_id: UUID) -> bool:
        existing = await self.get(project_id, paper_id)
        if existing is None:
            return False

        await self.session.delete(existing)
        await self.session.flush()
        return True
