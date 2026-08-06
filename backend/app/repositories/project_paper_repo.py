from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper
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

    async def list_papers_for_project(self, project_id: UUID) -> list[Paper]:
        stmt = (
            select(Paper)
            .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
            .where(ProjectPaper.project_id == project_id)
            .order_by(ProjectPaper.saved_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_papers_by_project(
        self, project_ids: list[UUID] | None = None
    ) -> dict[UUID, int]:
        stmt = select(ProjectPaper.project_id, func.count()).group_by(
            ProjectPaper.project_id
        )
        if project_ids is not None:
            if not project_ids:
                return {}
            stmt = stmt.where(ProjectPaper.project_id.in_(project_ids))
        result = await self.session.execute(stmt)
        return {project_id: int(count) for project_id, count in result.all()}

    async def count_distinct_papers(self) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(ProjectPaper.paper_id)))
        )
        return int(result.scalar_one())

    async def topics_by_project(
        self, project_ids: list[UUID] | None = None
    ) -> dict[UUID, list[str]]:
        stmt = (
            select(ProjectPaper.project_id, Paper.topics)
            .join(Paper, Paper.id == ProjectPaper.paper_id)
            .where(Paper.topics.is_not(None))
        )
        if project_ids is not None:
            if not project_ids:
                return {}
            stmt = stmt.where(ProjectPaper.project_id.in_(project_ids))
        result = await self.session.execute(stmt)

        topics_map: dict[UUID, list[str]] = {}
        for project_id, topics in result.all():
            bucket = topics_map.setdefault(project_id, [])
            for topic in topics or []:
                if topic and topic not in bucket:
                    bucket.append(topic)
        return topics_map
