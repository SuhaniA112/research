"""Database-first research discovery with external-provider fallback.

Ranking (deterministic, no LLM):
1. Primary: semantic similarity (cosine similarity = 1 - pgvector cosine_distance).
2. Secondary: provider_rank ascending when similarity ties (external results).
3. Tertiary: title ascending for full determinism.

Result origins:
- database: paper found only via global cache / topic associations
- external: paper newly returned by providers this request
- database_and_external: paper already in DB and also returned by providers

Progressive mode (request.progressive=True):
- On cache miss with usable DB candidates, return those immediately
  (search_complete=False) without waiting for external providers.
- Client continues with force_refresh=True for enrichment.
- Default progressive=False preserves the historical single-shot contract.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.paper import Paper
from app.models.search_topic import SearchTopic
from app.models.search_topic_paper import SearchTopicPaper
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.search_execution_repo import SearchExecutionRepository
from app.repositories.search_topic_paper_repo import SearchTopicPaperRepository
from app.repositories.search_topic_repo import SearchTopicRepository
from app.schemas.paper import PaperResponse
from app.schemas.research_discovery import (
    DiscoverySearchRequest,
    DiscoverySearchResponse,
    DiscoverySearchResultItem,
    ProviderFailure,
)
from app.schemas.research_papers import IndPaper
from app.services.embeddings.voyage_client import VoyageEmbeddingClient
from app.services.query_normalization import (
    build_intent_query_from_topics,
    normalize_query,
)
from app.services.research_sources.arxiv import ArxivClient
from app.services.research_sources.base import ResearchSourceClient
from app.services.research_sources.dblp import DblpClient
from app.services.research_sources.openalex import OpenAlexClient
from app.services.research_sources.semanticscholar import SemanticScholarClient

logger = get_logger(__name__)

CacheMissReason = Literal[
    "no_matching_topic",
    "no_relevant_papers",
    "insufficient_results",
    "low_similarity",
    "stale_topic",
    "force_refresh",
    "incomplete_metadata",
]

TopicMatchType = Literal["exact", "semantic", "new"]
ResultOrigin = Literal["database", "external", "database_and_external"]


@dataclass
class _Candidate:
    paper: Paper
    similarity_score: float | None
    provider_rank: int | None = None
    origins: set[str] = field(default_factory=set)


@dataclass
class _ProviderRunStats:
    attempted: list[str] = field(default_factory=list)
    succeeded: list[str] = field(default_factory=list)
    failed: list[ProviderFailure] = field(default_factory=list)
    papers: list[tuple[IndPaper, int, str]] = field(default_factory=list)


@dataclass
class _IngestStats:
    papers_inserted: int = 0
    papers_reused: int = 0
    embeddings_generated: int = 0
    embeddings_reused: int = 0


@dataclass
class _ProviderBatch:
    label: str
    papers: list[tuple[IndPaper, int]] = field(default_factory=list)
    failure: ProviderFailure | None = None


class DiscoverySearchService:
    def __init__(
        self,
        *,
        paper_repo: PaperRepository,
        chunk_repo: ChunkRepository,
        search_topic_repo: SearchTopicRepository,
        search_execution_repo: SearchExecutionRepository,
        search_topic_paper_repo: SearchTopicPaperRepository,
        voyage_client: VoyageEmbeddingClient,
        settings: Settings,
        project_repo: ProjectRepository | None = None,
        profile_repo: ProfileRepository | None = None,
        provider_clients: list[ResearchSourceClient] | None = None,
    ) -> None:
        self.paper_repo = paper_repo
        self.chunk_repo = chunk_repo
        self.search_topic_repo = search_topic_repo
        self.search_execution_repo = search_execution_repo
        self.search_topic_paper_repo = search_topic_paper_repo
        self.project_repo = project_repo
        self.profile_repo = profile_repo
        self.voyage_client = voyage_client
        self.settings = settings
        self.clients = (
            provider_clients
            if provider_clients is not None
            else [
                ArxivClient(),
                OpenAlexClient(),
                SemanticScholarClient(),
                DblpClient(),
            ]
        )

    async def search(
        self,
        request: DiscoverySearchRequest,
        *,
        user_id: UUID | None = None,
        anonymous_session_id: str | None = None,
    ) -> DiscoverySearchResponse:
        started = time.perf_counter()
        t0 = started

        raw_query, normalized = await self._resolve_effective_query(
            request, user_id=user_id
        )
        limit = request.limit or self.settings.search_default_limit
        force_refresh = request.force_refresh
        progressive = request.progressive

        [query_embedding] = await self.voyage_client.embed(
            [normalized], input_type="query"
        )
        preprocess_ms = (time.perf_counter() - t0) * 1000

        t_topic = time.perf_counter()
        topic, topic_match_type = await self._resolve_topic(
            raw_query=raw_query,
            normalized_query=normalized,
            query_embedding=query_embedding,
        )
        topic_ms = (time.perf_counter() - t_topic) * 1000

        t_db = time.perf_counter()
        # Same AsyncSession cannot run concurrent awaits safely — keep sequential.
        paper_hits = await self.chunk_repo.search_global(
            query_embedding,
            max_distance=self.settings.paper_max_distance,
            limit=limit * self.settings.search_candidate_multiplier,
            candidate_multiplier=self.settings.search_ann_candidate_multiplier,
        )
        topic_assocs = await self.search_topic_paper_repo.list_papers_for_topic(
            topic.id, limit=limit * self.settings.search_candidate_multiplier
        )
        db_fetch_ms = (time.perf_counter() - t_db) * 1000

        candidates = self._merge_database_candidates(paper_hits, topic_assocs)
        cache_hit, miss_reason = self._evaluate_cache(
            topic=topic,
            topic_match_type=topic_match_type,
            candidates=candidates,
            limit=limit,
            force_refresh=force_refresh,
        )

        logger.info(
            "discovery_cache_decision search_topic_id=%s topic_match=%s "
            "cache_hit=%s miss_reason=%s cached_candidates=%s "
            "preprocess_ms=%.1f topic_ms=%.1f db_fetch_ms=%.1f progressive=%s",
            topic.id,
            topic_match_type,
            cache_hit,
            miss_reason,
            len(candidates),
            preprocess_ms,
            topic_ms,
            db_fetch_ms,
            progressive,
        )

        provider_stats = _ProviderRunStats()
        ingest_stats = _IngestStats()
        external_search_performed = False
        search_complete = True
        page1_process_ms = 0.0
        provider_fetch_ms = 0.0
        ingest_ms = 0.0
        time_to_first_results_ms: float | None = None

        if not cache_hit:
            # Progressive page-1: return ranked DB candidates immediately when we
            # already have something useful. External enrichment continues via a
            # follow-up force_refresh request from the client.
            if progressive and self._can_return_early(candidates, miss_reason):
                t_rank = time.perf_counter()
                ranked = self._rank_candidates(candidates)[:limit]
                results = self._to_result_items(ranked)
                page1_process_ms = (time.perf_counter() - t_rank) * 1000
                time_to_first_results_ms = (time.perf_counter() - started) * 1000
                search_complete = False

                execution = await self.search_execution_repo.record(
                    search_topic_id=topic.id,
                    raw_query=raw_query,
                    normalized_query=normalized,
                    cache_hit=False,
                    cache_miss_reason=miss_reason,
                    external_search_performed=False,
                    force_refresh=force_refresh,
                    requested_limit=limit,
                    results_returned=len(results),
                    user_id=user_id,
                    anonymous_session_id=anonymous_session_id,
                )

                logger.info(
                    "discovery_search_page1_early search_execution_id=%s "
                    "miss_reason=%s final_count=%s page1_process_ms=%.1f "
                    "time_to_first_results_ms=%.1f total_ms=%.1f",
                    execution.id,
                    miss_reason,
                    len(results),
                    page1_process_ms,
                    time_to_first_results_ms,
                    time_to_first_results_ms,
                )

                return DiscoverySearchResponse(
                    query=raw_query,
                    normalized_query=normalized,
                    search_execution_id=execution.id,
                    matched_topic_id=topic.id,
                    topic_match_type=topic_match_type,
                    cache_hit=False,
                    cache_miss_reason=miss_reason,
                    external_search_performed=False,
                    providers_attempted=[],
                    providers_succeeded=[],
                    providers_failed=[],
                    results=results,
                    search_complete=False,
                )

            # Release DB work before slow provider calls: flush so topic exists,
            # but do not hold a long transaction across HTTP.
            await self.paper_repo.session.flush()

            t_providers = time.perf_counter()
            provider_stats = await self._call_providers(normalized, limit=limit)
            provider_fetch_ms = (time.perf_counter() - t_providers) * 1000
            external_search_performed = True

            t_ingest = time.perf_counter()
            ingest_stats = await self._ingest_provider_papers(
                provider_stats=provider_stats,
                topic=topic,
                candidates=candidates,
                paper_hits=paper_hits,
                query_embedding=query_embedding,
            )
            ingest_ms = (time.perf_counter() - t_ingest) * 1000

            await self.search_topic_repo.mark_external_refresh(
                topic.id, result_count=len(provider_stats.papers)
            )

            # Refresh vector hits after new embeddings so ranking includes them.
            t_rerank = time.perf_counter()
            paper_hits = await self.chunk_repo.search_global(
                query_embedding,
                max_distance=self.settings.paper_max_distance,
                limit=limit * self.settings.search_candidate_multiplier,
                candidate_multiplier=self.settings.search_ann_candidate_multiplier,
            )
            sim_by_id = {p.id: 1.0 - dist for p, dist in paper_hits}
            for cand in candidates:
                if cand.paper.id in sim_by_id:
                    cand.similarity_score = sim_by_id[cand.paper.id]
                    cand.origins.add("database")
            page1_process_ms = (time.perf_counter() - t_rerank) * 1000

        ranked = self._rank_candidates(candidates)[:limit]
        results = self._to_result_items(ranked)
        time_to_first_results_ms = (time.perf_counter() - started) * 1000

        execution = await self.search_execution_repo.record(
            search_topic_id=topic.id,
            raw_query=raw_query,
            normalized_query=normalized,
            cache_hit=cache_hit,
            cache_miss_reason=None if cache_hit else miss_reason,
            external_search_performed=external_search_performed,
            force_refresh=force_refresh,
            requested_limit=limit,
            results_returned=len(results),
            user_id=user_id,
            anonymous_session_id=anonymous_session_id,
        )

        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "discovery_search_complete search_execution_id=%s cache_hit=%s "
            "external=%s search_complete=%s providers_attempted=%s "
            "providers_succeeded=%s providers_failed=%s cached_candidates=%s "
            "external_candidates=%s papers_inserted=%s papers_reused=%s "
            "embeddings_generated=%s embeddings_reused=%s final_count=%s "
            "preprocess_ms=%.1f topic_ms=%.1f db_fetch_ms=%.1f "
            "provider_fetch_ms=%.1f ingest_ms=%.1f page1_process_ms=%.1f "
            "time_to_first_results_ms=%.1f total_ms=%.1f",
            execution.id,
            cache_hit,
            external_search_performed,
            search_complete,
            provider_stats.attempted,
            provider_stats.succeeded,
            [f.provider for f in provider_stats.failed],
            len(candidates),
            len(provider_stats.papers),
            ingest_stats.papers_inserted,
            ingest_stats.papers_reused,
            ingest_stats.embeddings_generated,
            ingest_stats.embeddings_reused,
            len(results),
            preprocess_ms,
            topic_ms,
            db_fetch_ms,
            provider_fetch_ms,
            ingest_ms,
            page1_process_ms,
            time_to_first_results_ms,
            duration_ms,
        )

        return DiscoverySearchResponse(
            query=raw_query,
            normalized_query=normalized,
            search_execution_id=execution.id,
            matched_topic_id=topic.id,
            topic_match_type=topic_match_type,
            cache_hit=cache_hit,
            cache_miss_reason=None if cache_hit else miss_reason,
            external_search_performed=external_search_performed,
            providers_attempted=provider_stats.attempted,
            providers_succeeded=provider_stats.succeeded,
            providers_failed=provider_stats.failed,
            results=results,
            search_complete=search_complete,
        )

    async def search_stream(
        self,
        request: DiscoverySearchRequest,
        *,
        user_id: UUID | None = None,
        anonymous_session_id: str | None = None,
    ) -> AsyncIterator[DiscoverySearchResponse]:
        """Yield ranked snapshots as work completes (DB first, then each provider).

        Ranking rules match ``search``; only delivery is progressive. Cache hits
        yield a single complete response. Cache misses yield DB results (if any),
        then a snapshot after each provider finishes ingest+rank, then a final
        complete snapshot.
        """
        started = time.perf_counter()
        raw_query, normalized = await self._resolve_effective_query(
            request, user_id=user_id
        )
        limit = request.limit or self.settings.search_default_limit
        force_refresh = request.force_refresh

        t0 = time.perf_counter()
        [query_embedding] = await self.voyage_client.embed(
            [normalized], input_type="query"
        )
        preprocess_ms = (time.perf_counter() - t0) * 1000

        topic, topic_match_type = await self._resolve_topic(
            raw_query=raw_query,
            normalized_query=normalized,
            query_embedding=query_embedding,
        )

        paper_hits = await self.chunk_repo.search_global(
            query_embedding,
            max_distance=self.settings.paper_max_distance,
            limit=limit * self.settings.search_candidate_multiplier,
            candidate_multiplier=self.settings.search_ann_candidate_multiplier,
        )
        topic_assocs = await self.search_topic_paper_repo.list_papers_for_topic(
            topic.id, limit=limit * self.settings.search_candidate_multiplier
        )
        candidates = self._merge_database_candidates(paper_hits, topic_assocs)
        cache_hit, miss_reason = self._evaluate_cache(
            topic=topic,
            topic_match_type=topic_match_type,
            candidates=candidates,
            limit=limit,
            force_refresh=force_refresh,
        )

        logger.info(
            "discovery_stream_start cache_hit=%s miss_reason=%s candidates=%s "
            "preprocess_ms=%.1f",
            cache_hit,
            miss_reason,
            len(candidates),
            preprocess_ms,
        )

        def _snapshot(
            *,
            complete: bool,
            external: bool,
            provider_stats: _ProviderRunStats,
            execution_id: UUID | None = None,
        ) -> DiscoverySearchResponse:
            ranked = self._rank_candidates(candidates)[:limit]
            return DiscoverySearchResponse(
                query=raw_query,
                normalized_query=normalized,
                search_execution_id=execution_id or uuid4(),
                matched_topic_id=topic.id,
                topic_match_type=topic_match_type,
                cache_hit=cache_hit,
                cache_miss_reason=None if cache_hit else miss_reason,
                external_search_performed=external,
                providers_attempted=list(provider_stats.attempted),
                providers_succeeded=list(provider_stats.succeeded),
                providers_failed=list(provider_stats.failed),
                results=self._to_result_items(ranked),
                search_complete=complete,
            )

        if cache_hit:
            ranked = self._rank_candidates(candidates)[:limit]
            results = self._to_result_items(ranked)
            execution = await self.search_execution_repo.record(
                search_topic_id=topic.id,
                raw_query=raw_query,
                normalized_query=normalized,
                cache_hit=True,
                cache_miss_reason=None,
                external_search_performed=False,
                force_refresh=force_refresh,
                requested_limit=limit,
                results_returned=len(results),
                user_id=user_id,
                anonymous_session_id=anonymous_session_id,
            )
            logger.info(
                "discovery_stream_complete cache_hit=true "
                "time_to_first_results_ms=%.1f total_ms=%.1f count=%s",
                (time.perf_counter() - started) * 1000,
                (time.perf_counter() - started) * 1000,
                len(results),
            )
            yield DiscoverySearchResponse(
                query=raw_query,
                normalized_query=normalized,
                search_execution_id=execution.id,
                matched_topic_id=topic.id,
                topic_match_type=topic_match_type,
                cache_hit=True,
                cache_miss_reason=None,
                external_search_performed=False,
                results=results,
                search_complete=True,
            )
            return

        provider_stats = _ProviderRunStats()
        # Emit DB page-1 immediately when anything is available.
        if candidates:
            ttfr = (time.perf_counter() - started) * 1000
            logger.info(
                "discovery_stream_partial origin=database count=%s "
                "time_to_first_results_ms=%.1f",
                len(candidates),
                ttfr,
            )
            yield _snapshot(
                complete=False, external=False, provider_stats=provider_stats
            )

        await self.paper_repo.session.flush()

        ingest_total = _IngestStats()
        async for batch in self._iter_provider_batches(normalized, limit=limit):
            provider_stats.attempted.append(batch.label)
            if batch.failure is not None:
                provider_stats.failed.append(batch.failure)
                logger.info(
                    "discovery_stream_provider_failed provider=%s", batch.label
                )
                # Still emit so the client can see provider progress.
                yield _snapshot(
                    complete=False, external=True, provider_stats=provider_stats
                )
                continue

            provider_stats.succeeded.append(batch.label)
            batch_stats = _ProviderRunStats(
                papers=[(p, rank, batch.label) for p, rank in batch.papers]
            )
            stats = await self._ingest_provider_papers(
                provider_stats=batch_stats,
                topic=topic,
                candidates=candidates,
                paper_hits=paper_hits,
                query_embedding=query_embedding,
            )
            ingest_total.papers_inserted += stats.papers_inserted
            ingest_total.papers_reused += stats.papers_reused
            ingest_total.embeddings_generated += stats.embeddings_generated
            ingest_total.embeddings_reused += stats.embeddings_reused
            for paper, rank in batch.papers:
                provider_stats.papers.append((paper, rank, batch.label))

            logger.info(
                "discovery_stream_partial origin=provider provider=%s "
                "batch_papers=%s candidates=%s elapsed_ms=%.1f",
                batch.label,
                len(batch.papers),
                len(candidates),
                (time.perf_counter() - started) * 1000,
            )
            yield _snapshot(
                complete=False, external=True, provider_stats=provider_stats
            )

        await self.search_topic_repo.mark_external_refresh(
            topic.id, result_count=len(provider_stats.papers)
        )

        # Final ANN refresh so scores match non-stream search path.
        paper_hits = await self.chunk_repo.search_global(
            query_embedding,
            max_distance=self.settings.paper_max_distance,
            limit=limit * self.settings.search_candidate_multiplier,
            candidate_multiplier=self.settings.search_ann_candidate_multiplier,
        )
        sim_by_id = {p.id: 1.0 - dist for p, dist in paper_hits}
        for cand in candidates:
            if cand.paper.id in sim_by_id:
                cand.similarity_score = sim_by_id[cand.paper.id]
                cand.origins.add("database")

        ranked = self._rank_candidates(candidates)[:limit]
        results = self._to_result_items(ranked)
        execution = await self.search_execution_repo.record(
            search_topic_id=topic.id,
            raw_query=raw_query,
            normalized_query=normalized,
            cache_hit=False,
            cache_miss_reason=miss_reason,
            external_search_performed=True,
            force_refresh=force_refresh,
            requested_limit=limit,
            results_returned=len(results),
            user_id=user_id,
            anonymous_session_id=anonymous_session_id,
        )
        total_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "discovery_stream_complete cache_hit=false providers_succeeded=%s "
            "embeddings_generated=%s final_count=%s total_ms=%.1f",
            provider_stats.succeeded,
            ingest_total.embeddings_generated,
            len(results),
            total_ms,
        )
        yield DiscoverySearchResponse(
            query=raw_query,
            normalized_query=normalized,
            search_execution_id=execution.id,
            matched_topic_id=topic.id,
            topic_match_type=topic_match_type,
            cache_hit=False,
            cache_miss_reason=miss_reason,
            external_search_performed=True,
            providers_attempted=provider_stats.attempted,
            providers_succeeded=provider_stats.succeeded,
            providers_failed=provider_stats.failed,
            results=results,
            search_complete=True,
        )

    @staticmethod
    def _can_return_early(
        candidates: list[_Candidate],
        miss_reason: CacheMissReason | None,
    ) -> bool:
        """Whether progressive mode can show DB candidates before external I/O.

        Any non-empty candidate set is enough for page 1. Cold starts with an
        empty DB still wait for providers in one shot (miss_reason unused but
        kept for log/call-site clarity).
        """
        del miss_reason  # reserved for future gating by miss type
        return bool(candidates)

    @staticmethod
    def _to_result_items(
        ranked: list[_Candidate],
    ) -> list[DiscoverySearchResultItem]:
        return [
            DiscoverySearchResultItem(
                paper=PaperResponse.model_validate(c.paper),
                similarity_score=c.similarity_score,
                result_origin=DiscoverySearchService._origin_label(c.origins),
            )
            for c in ranked
        ]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = 0.0
        na = 0.0
        nb = 0.0
        for x, y in zip(a, b, strict=True):
            dot += x * y
            na += x * x
            nb += y * y
        if na <= 0.0 or nb <= 0.0:
            return 0.0
        return dot / (math.sqrt(na) * math.sqrt(nb))

    async def _ingest_provider_papers(
        self,
        *,
        provider_stats: _ProviderRunStats,
        topic: SearchTopic,
        candidates: list[_Candidate],
        paper_hits: list[tuple[Paper, float]],
        query_embedding: list[float],
    ) -> _IngestStats:
        """Upsert provider papers, batch-embed missing docs, associate to topic.

        Preserves prior per-paper semantics; only batches Voyage document embeds
        and chunk lookups that were previously one-at-a-time.
        """
        stats = _IngestStats()
        if not provider_stats.papers:
            return stats

        paper_vec_hits = {p.id: 1.0 - dist for p, dist in paper_hits}
        by_id: dict[UUID, _Candidate] = {c.paper.id: c for c in candidates}

        # Phase 1: upsert all papers (same session — sequential).
        upserted: list[tuple[Paper, IndPaper, int, str, bool]] = []
        for ind_paper, provider_rank, source_name in provider_stats.papers:
            try:
                paper, created = await self.paper_repo.upsert_from_ind_paper(ind_paper)
            except ValueError:
                continue
            if created:
                stats.papers_inserted += 1
            else:
                stats.papers_reused += 1
            upserted.append((paper, ind_paper, provider_rank, source_name, created))

        # Phase 2: one batched chunk lookup.
        existing_chunks = await self.chunk_repo.get_for_papers(
            [paper.id for paper, *_ in upserted]
        )

        # Phase 3: collect texts that need (re)embedding, then one Voyage call.
        need_embed: list[tuple[int, str]] = []  # (upserted index, text)
        for idx, (paper, ind_paper, _rank, _src, _created) in enumerate(upserted):
            indexable = ind_paper.abstract or ind_paper.title
            existing = existing_chunks.get(paper.id)
            if existing is None or existing.text != indexable:
                need_embed.append((idx, indexable))

        embeddings_by_idx: dict[int, list[float]] = {}
        if need_embed:
            texts = [text for _, text in need_embed]
            vectors = await self.voyage_client.embed(texts, input_type="document")
            for (idx, _text), vector in zip(need_embed, vectors, strict=True):
                embeddings_by_idx[idx] = vector

        # Phase 4: write chunks + topic associations; update candidate set.
        for idx, (paper, ind_paper, provider_rank, source_name, _created) in enumerate(
            upserted
        ):
            indexable = ind_paper.abstract or ind_paper.title
            existing = existing_chunks.get(paper.id)
            embedding = embeddings_by_idx.get(idx)

            if embedding is not None:
                chunk_result = await self.chunk_repo.ensure_chunk_for_paper(
                    paper.id, indexable, embedding
                )
                chunk_created = (
                    chunk_result[1] if isinstance(chunk_result, tuple) else False
                )
                if chunk_created or (
                    existing is not None and existing.text != indexable
                ):
                    stats.embeddings_generated += 1
                else:
                    stats.embeddings_reused += 1
                # Provisional score until post-ingest ANN refresh.
                similarity = self._cosine_similarity(query_embedding, embedding)
            else:
                stats.embeddings_reused += 1
                similarity = paper_vec_hits.get(paper.id)

            await self.search_topic_paper_repo.upsert_association(
                search_topic_id=topic.id,
                paper_id=paper.id,
                semantic_relevance_score=similarity,
                provider_rank=provider_rank,
                discovery_source=source_name,
            )

            existing_cand = by_id.get(paper.id)
            if existing_cand is None:
                cand = _Candidate(
                    paper=paper,
                    similarity_score=similarity,
                    provider_rank=provider_rank,
                    origins={"external"},
                )
                candidates.append(cand)
                by_id[paper.id] = cand
            else:
                existing_cand.origins.add("external")
                if provider_rank is not None:
                    if (
                        existing_cand.provider_rank is None
                        or provider_rank < existing_cand.provider_rank
                    ):
                        existing_cand.provider_rank = provider_rank
                if similarity is not None and (
                    existing_cand.similarity_score is None
                    or similarity > existing_cand.similarity_score
                ):
                    existing_cand.similarity_score = similarity

        return stats

    async def _resolve_effective_query(
        self,
        request: DiscoverySearchRequest,
        *,
        user_id: UUID | None,
    ) -> tuple[str, str]:
        """Resolve display (raw) + cache (normalized) query strings.

        - Non-empty explicit query is primary intent (project context is not
          concatenated, to preserve expected explicit-search caching/behavior).
        - Empty query + project_id → project topics/keywords (user-scoped).
        - Empty query + no project → profile research areas/keywords.
        - Still empty → clear validation error (never invent "research").
        """
        explicit = (request.query or "").strip()
        if explicit:
            return explicit, normalize_query(explicit)

        if request.project_id is not None:
            if user_id is None or self.project_repo is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required to search with project context",
                )
            project = await self.project_repo.get_for_user(request.project_id, user_id)
            if project is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project {request.project_id} not found",
                )
            intent = build_intent_query_from_topics(project.topics, project.keywords)
            if intent:
                return intent, normalize_query(intent)

        if self.profile_repo is not None:
            profile = await self.profile_repo.ensure_singleton()
            intent = build_intent_query_from_topics(
                profile.research_areas, profile.keywords
            )
            if intent:
                return intent, normalize_query(intent)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Query must not be empty. Provide a query, a project_id with "
                "topics/keywords, or configure profile research areas."
            ),
        )

    async def _resolve_topic(
        self,
        *,
        raw_query: str,
        normalized_query: str,
        query_embedding: list[float],
    ) -> tuple[SearchTopic, TopicMatchType]:
        exact = await self.search_topic_repo.get_by_normalized_query(normalized_query)
        if exact is not None:
            logger.info("exact_topic_cache_hit topic_id=%s", exact.id)
            return exact, "exact"

        similar = await self.search_topic_repo.find_similar(
            query_embedding,
            max_distance=self.settings.topic_max_distance,
            limit=1,
        )
        if similar:
            topic, distance = similar[0]
            logger.info(
                "semantic_topic_cache_hit topic_id=%s similarity=%.4f",
                topic.id,
                1.0 - distance,
            )
            return topic, "semantic"

        topic, created = await self.search_topic_repo.get_or_create_by_normalized_query(
            canonical_query=raw_query.strip(),
            normalized_query=normalized_query,
            embedding=query_embedding,
        )
        if created:
            logger.info("search_topic_created topic_id=%s", topic.id)
            return topic, "new"

        logger.info("exact_topic_cache_hit topic_id=%s (race resolved)", topic.id)
        return topic, "exact"

    def _merge_database_candidates(
        self,
        paper_hits: list[tuple[Paper, float]],
        topic_assocs: list[tuple[Paper, SearchTopicPaper]],
    ) -> list[_Candidate]:
        by_id: dict[UUID, _Candidate] = {}
        for paper, distance in paper_hits:
            by_id[paper.id] = _Candidate(
                paper=paper,
                similarity_score=1.0 - float(distance),
                origins={"database"},
            )

        for paper, assoc in topic_assocs:
            score = assoc.semantic_relevance_score
            rank = assoc.provider_rank
            if paper.id in by_id:
                cand = by_id[paper.id]
                cand.origins.add("database")
                if score is not None and (
                    cand.similarity_score is None or score > cand.similarity_score
                ):
                    cand.similarity_score = float(score)
                if rank is not None:
                    cand.provider_rank = (
                        rank
                        if cand.provider_rank is None
                        else min(cand.provider_rank, rank)
                    )
            else:
                by_id[paper.id] = _Candidate(
                    paper=paper,
                    similarity_score=float(score) if score is not None else None,
                    provider_rank=rank,
                    origins={"database"},
                )
        return list(by_id.values())

    def _evaluate_cache(
        self,
        *,
        topic: SearchTopic,
        topic_match_type: TopicMatchType,
        candidates: list[_Candidate],
        limit: int,
        force_refresh: bool,
    ) -> tuple[bool, CacheMissReason | None]:
        if force_refresh:
            return False, "force_refresh"

        if topic_match_type == "new" and topic.last_external_refresh_at is None:
            # Brand-new topic never refreshed externally.
            if not candidates:
                return False, "no_matching_topic"

        relevant = [
            c
            for c in candidates
            if c.similarity_score is not None
            and c.similarity_score
            >= self.settings.search_cache_paper_similarity_threshold
        ]

        if not candidates:
            return False, "no_relevant_papers"

        if not relevant:
            return False, "low_similarity"

        best = max(c.similarity_score or 0.0 for c in relevant)
        if best < self.settings.search_cache_paper_similarity_threshold:
            return False, "low_similarity"

        if len(relevant) < self.settings.search_cache_min_results:
            return False, "insufficient_results"

        if len(relevant) < limit and topic.last_external_refresh_at is None:
            return False, "insufficient_results"

        if topic.last_external_refresh_at is None:
            return False, "no_matching_topic"

        max_age = timedelta(days=self.settings.search_cache_max_age_days)
        refreshed_at = topic.last_external_refresh_at
        if refreshed_at.tzinfo is None:
            refreshed_at = refreshed_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - refreshed_at > max_age:
            return False, "stale_topic"

        incomplete = [
            c
            for c in relevant
            if not c.paper.title or (c.paper.abstract is None and not c.paper.url)
        ]
        if len(incomplete) > len(relevant) // 2:
            return False, "incomplete_metadata"

        if len(relevant) < limit:
            # Useful cached set smaller than requested limit → refresh for coverage.
            return False, "insufficient_results"

        return True, None

    async def _iter_provider_batches(
        self, query: str, *, limit: int
    ) -> AsyncIterator[_ProviderBatch]:
        """Run providers concurrently; yield each batch as it finishes."""
        if not self.clients:
            return
        per_provider = max(5, (limit + len(self.clients) - 1) // len(self.clients))
        tasks = [
            asyncio.create_task(self._search_one_provider(client, query, per_provider))
            for client in self.clients
        ]
        for finished in asyncio.as_completed(tasks):
            yield await finished

    async def _search_one_provider(
        self,
        client: ResearchSourceClient,
        query: str,
        per_provider: int,
    ) -> _ProviderBatch:
        name = client.__class__.__name__.replace("Client", "").lower()
        label_map = {
            "arxiv": "arxiv",
            "openalex": "openalex",
            "semanticscholar": "semantic_scholar",
            "dblp": "dblp",
        }
        label = label_map.get(name, name)
        try:
            results = await client.search(query, max_results=per_provider)
            return _ProviderBatch(
                label=label,
                papers=[(paper, idx + 1) for idx, paper in enumerate(results)],
            )
        except Exception as exc:
            logger.warning(
                "provider_failure provider=%s failure_type=%s",
                label,
                type(exc).__name__,
            )
            return _ProviderBatch(
                label=label,
                failure=ProviderFailure(
                    provider=label,
                    failure_type=type(exc).__name__,
                    detail=str(exc)[:200],
                ),
            )

    async def _call_providers(self, query: str, *, limit: int) -> _ProviderRunStats:
        stats = _ProviderRunStats()
        async for batch in self._iter_provider_batches(query, limit=limit):
            stats.attempted.append(batch.label)
            if batch.failure is not None:
                stats.failed.append(batch.failure)
                continue
            stats.succeeded.append(batch.label)
            for paper, rank in batch.papers:
                stats.papers.append((paper, rank, batch.label))
        return stats

    @staticmethod
    def _rank_candidates(candidates: list[_Candidate]) -> list[_Candidate]:
        """Deterministic ranking: similarity desc, provider_rank asc, title asc."""

        def sort_key(c: _Candidate) -> tuple:
            sim = c.similarity_score if c.similarity_score is not None else -1.0
            rank = c.provider_rank if c.provider_rank is not None else 10_000
            return (-sim, rank, c.paper.title.lower())

        # Deduplicate by paper id keeping best candidate.
        best: dict[UUID, _Candidate] = {}
        for cand in candidates:
            existing = best.get(cand.paper.id)
            if existing is None or sort_key(cand) < sort_key(existing):
                if existing is not None:
                    cand.origins |= existing.origins
                best[cand.paper.id] = cand
            else:
                existing.origins |= cand.origins

        return sorted(best.values(), key=sort_key)

    @staticmethod
    def _origin_label(origins: set[str]) -> ResultOrigin:
        has_db = "database" in origins
        has_ext = "external" in origins
        if has_db and has_ext:
            return "database_and_external"
        if has_ext:
            return "external"
        return "database"
