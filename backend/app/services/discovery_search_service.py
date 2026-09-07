"""Database-first research discovery with external-provider fallback.

Ranking (deterministic, no LLM):
1. Primary: semantic similarity (cosine similarity = 1 - pgvector cosine_distance).
2. Secondary: provider_rank ascending when similarity ties (external results).
3. Tertiary: title ascending for full determinism.

Result origins:
- database: paper found only via global cache / topic associations
- external: paper newly returned by providers this request
- database_and_external: paper already in DB and also returned by providers
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

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
        raw_query, normalized = await self._resolve_effective_query(
            request, user_id=user_id
        )
        limit = request.limit or self.settings.search_default_limit
        force_refresh = request.force_refresh

        [query_embedding] = await self.voyage_client.embed(
            [normalized], input_type="query"
        )

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
            "discovery_cache_decision search_topic_id=%s topic_match=%s "
            "cache_hit=%s miss_reason=%s cached_candidates=%s",
            topic.id,
            topic_match_type,
            cache_hit,
            miss_reason,
            len(candidates),
        )

        provider_stats = _ProviderRunStats()
        papers_inserted = 0
        papers_reused = 0
        embeddings_generated = 0
        embeddings_reused = 0
        external_search_performed = False

        if not cache_hit:
            # Release DB work before slow provider calls: flush so topic exists,
            # but do not hold a long transaction across HTTP.
            await self.paper_repo.session.flush()

            provider_stats = await self._call_providers(normalized, limit=limit)
            external_search_performed = True

            for ind_paper, provider_rank, source_name in provider_stats.papers:
                try:
                    paper, created = await self.paper_repo.upsert_from_ind_paper(
                        ind_paper
                    )
                except ValueError:
                    continue

                if created:
                    papers_inserted += 1
                else:
                    papers_reused += 1

                indexable = ind_paper.abstract or ind_paper.title
                existing_chunk = await self.chunk_repo.get_for_paper(paper.id)
                if existing_chunk is None or existing_chunk.text != indexable:
                    [embedding] = await self.voyage_client.embed(
                        [indexable], input_type="document"
                    )
                    chunk_result = await self.chunk_repo.ensure_chunk_for_paper(
                        paper.id, indexable, embedding
                    )
                    chunk_created = (
                        chunk_result[1] if isinstance(chunk_result, tuple) else False
                    )
                    if chunk_created or (
                        existing_chunk is not None and existing_chunk.text != indexable
                    ):
                        embeddings_generated += 1
                    else:
                        embeddings_reused += 1
                else:
                    embeddings_reused += 1

                # Similarity vs query for ranking after persistence.
                paper_vec_hits = {p.id: 1.0 - dist for p, dist in paper_hits}
                similarity = paper_vec_hits.get(paper.id)
                if similarity is None and existing_chunk is None:
                    # Fresh embed — approximate via ensuring we have a score later
                    # from re-search; for now leave None and use provider_rank.
                    pass

                await self.search_topic_paper_repo.upsert_association(
                    search_topic_id=topic.id,
                    paper_id=paper.id,
                    semantic_relevance_score=similarity,
                    provider_rank=provider_rank,
                    discovery_source=source_name,
                )

                key = paper.id
                if key not in {c.paper.id for c in candidates}:
                    candidates.append(
                        _Candidate(
                            paper=paper,
                            similarity_score=similarity,
                            provider_rank=provider_rank,
                            origins={"external"},
                        )
                    )
                else:
                    for cand in candidates:
                        if cand.paper.id == key:
                            cand.origins.add("external")
                            if provider_rank is not None:
                                if (
                                    cand.provider_rank is None
                                    or provider_rank < cand.provider_rank
                                ):
                                    cand.provider_rank = provider_rank
                            break

            await self.search_topic_repo.mark_external_refresh(
                topic.id, result_count=len(provider_stats.papers)
            )

            # Refresh vector hits after new embeddings so ranking includes them.
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
        results = [
            DiscoverySearchResultItem(
                paper=PaperResponse.model_validate(c.paper),
                similarity_score=c.similarity_score,
                result_origin=self._origin_label(c.origins),
            )
            for c in ranked
        ]

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
            "external=%s providers_attempted=%s providers_succeeded=%s "
            "providers_failed=%s cached_candidates=%s external_candidates=%s "
            "papers_inserted=%s papers_reused=%s embeddings_generated=%s "
            "embeddings_reused=%s final_count=%s duration_ms=%.1f",
            execution.id,
            cache_hit,
            external_search_performed,
            provider_stats.attempted,
            provider_stats.succeeded,
            [f.provider for f in provider_stats.failed],
            len(candidates),
            len(provider_stats.papers),
            papers_inserted,
            papers_reused,
            embeddings_generated,
            embeddings_reused,
            len(results),
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
        )

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

    async def _call_providers(self, query: str, *, limit: int) -> _ProviderRunStats:
        stats = _ProviderRunStats()
        if not self.clients:
            return stats
        per_provider = max(5, (limit + len(self.clients) - 1) // len(self.clients))

        async def _one(client: ResearchSourceClient) -> None:
            name = client.__class__.__name__.replace("Client", "").lower()
            # Normalize provider labels to match source field conventions.
            label_map = {
                "arxiv": "arxiv",
                "openalex": "openalex",
                "semanticscholar": "semantic_scholar",
                "dblp": "dblp",
            }
            label = label_map.get(name, name)
            stats.attempted.append(label)
            try:
                results = await client.search(query, max_results=per_provider)
                stats.succeeded.append(label)
                for idx, paper in enumerate(results):
                    stats.papers.append((paper, idx + 1, label))
            except Exception as exc:
                logger.warning(
                    "provider_failure provider=%s failure_type=%s",
                    label,
                    type(exc).__name__,
                )
                stats.failed.append(
                    ProviderFailure(
                        provider=label,
                        failure_type=type(exc).__name__,
                        detail=str(exc)[:200],
                    )
                )

        await asyncio.gather(*[_one(client) for client in self.clients])
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
