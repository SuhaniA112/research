from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chunk import Chunk
from app.models.paper import Paper
from app.models.project_paper import ProjectPaper
from app.repositories.base import BaseRepository
from app.schemas.indexing import PreparedChunk

# Over-fetch nearest chunks before paper dedupe so HNSW ANN + LIMIT stays useful.
DEFAULT_ANN_CANDIDATE_MULTIPLIER = 10
# Project RAG may need extra candidates when filtering after a global ANN probe.
DEFAULT_PROJECT_ANN_OVERFETCH = 50


def _metadata_fields(chunk: PreparedChunk) -> dict[str, object]:
    meta = chunk.metadata or {}
    page_number = meta.get("page_number")
    content_type = meta.get("content_type")
    indexer_version = meta.get("indexer_version")
    return {
        "page_number": page_number if isinstance(page_number, int) else None,
        "content_type": str(content_type) if content_type else None,
        "indexer_version": str(indexer_version) if indexer_version else None,
    }


class ChunkRepository(BaseRepository[Chunk]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Chunk)

    async def create_many_for_paper(
        self,
        paper_id: UUID,
        chunks: list[PreparedChunk],
        embeddings: list[list[float]],
    ) -> list[Chunk]:
        if not chunks:
            return []

        rows = [
            Chunk(
                paper_id=paper_id,
                chunk_index=chunk.chunk_index,
                text=chunk.chunk_text,
                embedding=embedding,
                **_metadata_fields(chunk),
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def get_for_paper(
        self, paper_id: UUID, *, chunk_index: int = 0
    ) -> Chunk | None:
        stmt = select(Chunk).where(
            Chunk.paper_id == paper_id, Chunk.chunk_index == chunk_index
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_paper(self, paper_id: UUID) -> list[Chunk]:
        stmt = (
            select(Chunk)
            .where(Chunk.paper_id == paper_id)
            .order_by(Chunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def ensure_chunk_for_paper(
        self,
        paper_id: UUID,
        text: str,
        embedding: list[float],
        *,
        chunk_index: int = 0,
        page_number: int | None = None,
        content_type: str | None = None,
        indexer_version: str | None = None,
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
            existing.page_number = page_number
            existing.content_type = content_type
            existing.indexer_version = indexer_version
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
                page_number=page_number,
                content_type=content_type,
                indexer_version=indexer_version,
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
            existing.page_number = page_number
            existing.content_type = content_type
            existing.indexer_version = indexer_version
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
        candidate_multiplier: int = DEFAULT_PROJECT_ANN_OVERFETCH,
    ) -> list[tuple[Chunk, float]]:
        """ANN-friendly project-scoped retrieval.

        1. Over-fetch nearest chunks among papers saved in the project
           (``ORDER BY embedding <=> query LIMIT``) so HNSW can be used.
        2. Apply the distance threshold in Python.
        3. Return at most ``top_k`` hits — never chunks outside the project.
        """
        distance = Chunk.embedding.cosine_distance(query_embedding)
        candidate_limit = max(top_k * candidate_multiplier, top_k)
        stmt = (
            select(Chunk, distance.label("distance"))
            .join(Paper, Chunk.paper_id == Paper.id)
            .join(ProjectPaper, ProjectPaper.paper_id == Paper.id)
            .where(ProjectPaper.project_id == project_id)
            .order_by(distance)
            .limit(candidate_limit)
            .options(selectinload(Chunk.paper))
        )
        result = await self.session.execute(stmt)
        filtered: list[tuple[Chunk, float]] = []
        for chunk, dist in result.all():
            if float(dist) <= max_distance:
                filtered.append((chunk, float(dist)))
            if len(filtered) >= top_k:
                break
        return filtered

    async def search_global(
        self,
        query_embedding: list[float],
        *,
        max_distance: float,
        limit: int,
        candidate_multiplier: int = DEFAULT_ANN_CANDIDATE_MULTIPLIER,
    ) -> list[tuple[Paper, float]]:
        """Global paper-vector search via ANN candidate retrieval then paper dedupe.

        Shape is intentionally ANN-friendly:
        ``ORDER BY embedding <=> query LIMIT candidate_limit`` first, then
        threshold filter, then best-distance-per-paper aggregation.
        """
        distance = Chunk.embedding.cosine_distance(query_embedding)
        candidate_limit = max(limit * candidate_multiplier, limit)
        stmt = (
            select(Chunk, distance.label("distance"))
            .order_by(distance)
            .limit(candidate_limit)
            .options(selectinload(Chunk.paper))
        )
        result = await self.session.execute(stmt)

        best_by_paper: dict[UUID, tuple[Paper, float]] = {}
        for chunk, dist in result.all():
            dist_f = float(dist)
            if dist_f > max_distance:
                continue
            paper = chunk.paper
            current = best_by_paper.get(paper.id)
            if current is None or dist_f < current[1]:
                best_by_paper[paper.id] = (paper, dist_f)

        ranked = sorted(best_by_paper.values(), key=lambda item: (item[1], item[0].title.lower()))
        return ranked[:limit]

    async def hnsw_index_exists(self) -> bool:
        """Return True when the chunks HNSW index is present (for tests)."""
        result = await self.session.execute(
            text(
                "SELECT 1 FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND indexname = 'ix_chunks_embedding_hnsw'"
            )
        )
        return result.scalar_one_or_none() is not None
