from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.paper import Paper
from app.repositories.base import BaseRepository
from app.schemas.research_papers import IndPaper


class PaperRepository(BaseRepository[Paper]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Paper)

    async def get_by_source_and_external_id(
        self, source: str, external_id: str
    ) -> Paper | None:
        stmt = select(Paper).where(
            Paper.source == source, Paper.external_id == external_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_chunks(self, paper_id: UUID) -> Paper | None:
        stmt = (
            select(Paper)
            .where(Paper.id == paper_id)
            .options(selectinload(Paper.chunks))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _better_metadata_updates(
        existing: Paper, incoming: IndPaper
    ) -> dict[str, object]:
        """Return field updates where incoming nonempty values improve stored ones.

        Never overwrites a good stored value with empty/None.
        """
        updates: dict[str, object] = {}

        if incoming.title and (
            not existing.title or len(incoming.title) > len(existing.title)
        ):
            updates["title"] = incoming.title

        if incoming.abstract and (
            existing.abstract is None or len(incoming.abstract) > len(existing.abstract)
        ):
            updates["abstract"] = incoming.abstract

        if incoming.authors and (
            not existing.authors or len(incoming.authors) > len(existing.authors)
        ):
            updates["authors"] = list(incoming.authors)

        if incoming.year is not None and existing.year is None:
            updates["year"] = incoming.year

        if incoming.url and not existing.url:
            updates["url"] = incoming.url

        if incoming.pdf_url and not existing.pdf_url:
            updates["pdf_url"] = incoming.pdf_url

        if incoming.topics and (
            not existing.topics or len(incoming.topics) > len(existing.topics)
        ):
            updates["topics"] = list(incoming.topics)

        return updates

    async def upsert_from_ind_paper(self, paper_in: IndPaper) -> tuple[Paper, bool]:
        """Insert or reuse a global Paper by (source, external_id).

        Uses INSERT ... ON CONFLICT DO NOTHING so concurrent discoveries of the
        same canonical paper do not fail the request. Returns (paper, created).
        """
        if not paper_in.external_id:
            raise ValueError("Paper is missing a stable external_id")

        existing = await self.get_by_source_and_external_id(
            paper_in.source, paper_in.external_id
        )
        if existing is not None:
            updates = self._better_metadata_updates(existing, paper_in)
            for key, value in updates.items():
                setattr(existing, key, value)
            if updates:
                await self.session.flush()
            return existing, False

        new_id = uuid4()
        stmt = (
            insert(Paper)
            .values(
                id=new_id,
                source=paper_in.source,
                external_id=paper_in.external_id,
                title=paper_in.title,
                abstract=paper_in.abstract,
                authors=list(paper_in.authors or []),
                year=paper_in.year,
                url=paper_in.url,
                pdf_url=paper_in.pdf_url,
                topics=list(paper_in.topics or []),
            )
            .on_conflict_do_nothing(constraint="uq_papers_source_external_id")
            .returning(Paper.id)
        )
        result = await self.session.execute(stmt)
        inserted_id = result.scalar_one_or_none()

        if inserted_id is not None:
            paper = await self.get_by_id(inserted_id)
            assert paper is not None
            return paper, True

        # Concurrent insert won the race — reuse the existing row.
        # Under READ COMMITTED each statement gets a fresh snapshot, so the
        # peer's committed row is visible here after ON CONFLICT waited it out.
        paper = await self.get_by_source_and_external_id(
            paper_in.source, paper_in.external_id
        )
        if paper is None:
            raise RuntimeError(
                "Paper upsert race unresolved for "
                f"{paper_in.source}/{paper_in.external_id}"
            )
        updates = self._better_metadata_updates(paper, paper_in)
        for key, value in updates.items():
            setattr(paper, key, value)
        if updates:
            await self.session.flush()
        return paper, False
