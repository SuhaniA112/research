from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.paper import Paper
from app.repositories.base import BaseRepository
from app.schemas.research_papers import IndPaper
from app.services.query_normalization import merge_topic_lists
from app.services.taxonomy.paper_topics import (
    normalize_source_categories,
    sanitize_persisted_topic_fields,
)


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

    async def get_many(self, paper_ids: list[UUID]) -> dict[UUID, Paper]:
        if not paper_ids:
            return {}
        result = await self.session.execute(select(Paper).where(Paper.id.in_(paper_ids)))
        return {paper.id: paper for paper in result.scalars().all()}

    async def find_by_topic_overlap(
        self, topics: list[str], *, exclude: set[UUID], limit: int
    ) -> list[tuple[Paper, int]]:
        """Papers sharing topics with ``topics`` (case-insensitive), most overlap first."""
        wanted = {t.casefold() for t in topics if t}
        if not wanted:
            return []
        stmt = select(Paper).where(Paper.topics.op("&&")(pg_array(list(topics)))).limit(limit * 4)
        result = await self.session.execute(stmt)
        scored = []
        for paper in result.scalars().all():
            if paper.id in exclude:
                continue
            overlap = sum(1 for t in paper.topics or [] if t.casefold() in wanted)
            if overlap:
                scored.append((paper, overlap))
        scored.sort(key=lambda item: (-item[1], item[0].title.lower()))
        return scored[:limit]

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

        updates.update(PaperRepository._validity_updates(existing, incoming))

        merged_categories = normalize_source_categories(
            list(existing.source_categories or [])
            + list(incoming.source_categories or [])
        )
        # Merge then sanitize so legacy query contaminants / raw codes are removed
        # even when a later provider refresh supplies fewer topics.
        clean_topics, clean_categories = sanitize_persisted_topic_fields(
            merge_topic_lists(existing.topics, incoming.topics),
            merged_categories,
        )

        if clean_categories != list(existing.source_categories or []):
            updates["source_categories"] = clean_categories
        if clean_topics != list(existing.topics or []):
            updates["topics"] = clean_topics

        return updates

    @staticmethod
    def _validity_updates(existing: Paper, incoming: IndPaper) -> dict[str, object]:
        """Merge source-validity metadata without discarding known values.

        Citation counts only grow, so keep the larger. A paper that any provider
        reports as peer-reviewed / open access stays that way (preprints get
        published; a closed copy elsewhere does not revoke an open one).
        """
        updates: dict[str, object] = {}

        if incoming.citation_count is not None and (
            existing.citation_count is None
            or incoming.citation_count > existing.citation_count
        ):
            updates["citation_count"] = incoming.citation_count

        if incoming.venue and (not existing.venue or existing.venue == "arXiv"):
            if incoming.venue != existing.venue:
                updates["venue"] = incoming.venue

        for field in ("is_open_access", "is_peer_reviewed"):
            new_value = getattr(incoming, field)
            old_value = getattr(existing, field)
            if new_value is None or new_value == old_value:
                continue
            if old_value is None or new_value is True:
                updates[field] = new_value

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

        topics, source_categories = sanitize_persisted_topic_fields(
            paper_in.topics,
            paper_in.source_categories,
        )

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
                topics=topics,
                source_categories=source_categories,
                citation_count=paper_in.citation_count,
                venue=paper_in.venue,
                is_open_access=paper_in.is_open_access,
                is_peer_reviewed=paper_in.is_peer_reviewed,
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
