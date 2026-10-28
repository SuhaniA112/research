"""Personalised recommendations: hub digest, related papers, similarity to saved.

Database-first: candidates come from pgvector ANN over stored chunk embeddings,
so a digest needs one batched embedding call (cached) and a few index lookups
instead of live provider searches.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from uuid import UUID

import numpy as np

from app.models.user import User
from app.schemas.paper import PaperResponse
from app.schemas.recommendation import DigestResponse, RecommendedPaper
from app.services.recommendation import ranking

MAX_INTERESTS = 8
POOL_PER_QUERY = 25
MAX_RANKED = 50
SPARSE_THRESHOLD = 10
CANDIDATE_MAX_DISTANCE = 0.75
# Second pass when nothing is that close: still recommend the nearest papers.
RELAXED_MAX_DISTANCE = 2.0
DIGEST_TTL_SECONDS = 60 * 60
EMBED_CACHE_SIZE = 2048

_embed_cache: "OrderedDict[tuple[str, str], list[float]]" = OrderedDict()
_digest_cache: dict[UUID, tuple[tuple, float, dict]] = {}


def collect_interests(
    research_areas: list[str], keywords: list[str], projects: list
) -> list[str]:
    """Profile terms first, then project topics/keywords; case-insensitive dedupe."""
    seen: set[str] = set()
    out: list[str] = []
    raw = list(research_areas or []) + list(keywords or [])
    for project in projects:
        raw += list(project.topics or []) + list(project.keywords or [])
    for term in raw:
        t = (term or "").strip()
        if t and t.casefold() not in seen:
            seen.add(t.casefold())
            out.append(t)
    return out[:MAX_INTERESTS]


def _week_start() -> str:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=now.weekday())).date().isoformat()


def clear_caches() -> None:
    _embed_cache.clear()
    _digest_cache.clear()


class RecommendationService:
    def __init__(
        self,
        profile_repo,
        project_repo,
        project_paper_repo,
        chunk_repo,
        paper_repo,
        voyage_client,
    ) -> None:
        self.profile_repo = profile_repo
        self.project_repo = project_repo
        self.project_paper_repo = project_paper_repo
        self.chunk_repo = chunk_repo
        self.paper_repo = paper_repo
        self.voyage = voyage_client

    # --- embeddings -----------------------------------------------------

    async def _embed_queries(self, texts: list[str]) -> list[list[float]]:
        """Embed with an in-process LRU so repeat digests skip the network."""
        model = getattr(self.voyage, "model", "")
        missing = [t for t in texts if (model, t) not in _embed_cache]
        if missing:
            vectors = await self.voyage.embed(missing, input_type="query")
            for text, vec in zip(missing, vectors):
                _embed_cache[(model, text)] = list(vec)
                if len(_embed_cache) > EMBED_CACHE_SIZE:
                    _embed_cache.popitem(last=False)
        out = []
        for t in texts:
            _embed_cache.move_to_end((model, t))
            out.append(_embed_cache[(model, t)])
        return out

    async def _paper_vectors(self, paper_ids: list[UUID]) -> dict[UUID, np.ndarray]:
        chunks = await self.chunk_repo.get_for_papers(paper_ids)
        return {
            pid: np.asarray(chunk.embedding, dtype=np.float64)
            for pid, chunk in chunks.items()
            if chunk.embedding is not None
        }

    # --- digest ---------------------------------------------------------

    async def digest(
        self, user: User, *, limit: int = 5, offset: int = 0, refresh: bool = False
    ) -> DigestResponse:
        profile = await self.profile_repo.ensure_for_user(user)
        projects = await self.project_repo.list_for_user(user.id)
        interests = collect_interests(profile.research_areas, profile.keywords, projects)
        now = datetime.now(timezone.utc)
        if not interests:
            return DigestResponse(generated_at=now)

        saved = await self.project_paper_repo.list_papers_for_user(user.id)
        saved_ids = sorted(p.id for p in saved)
        key = (tuple(interests), tuple(saved_ids), _week_start())

        cached = _digest_cache.get(user.id)
        if not refresh and cached and cached[0] == key and cached[1] > time.time():
            ranked = cached[2]
        else:
            ranked = await self._rank(interests, saved_ids)
            _digest_cache[user.id] = (key, time.time() + DIGEST_TTL_SECONDS, ranked)

        entries = ranked["entries"]
        page = entries[offset : offset + limit]
        papers = await self.paper_repo.get_many([e["paper_id"] for e in page])
        items = [
            RecommendedPaper(
                paper=PaperResponse.model_validate(papers[e["paper_id"]]),
                relevance=e["relevance"],
                similarity=e["similarity"],
                matched_interest=e["matched_interest"],
            )
            for e in page
            if e["paper_id"] in papers
        ]
        return DigestResponse(
            interests=interests,
            items=items,
            total=len(entries),
            offset=offset,
            has_more=offset + limit < len(entries),
            sparse=len(entries) < SPARSE_THRESHOLD,
            method=ranked["method"],
            generated_at=ranked["generated_at"],
        )

    async def _rank(self, interests: list[str], saved_ids: list[UUID]) -> dict:
        now = datetime.now(timezone.utc)
        exclude = set(saved_ids)
        if not getattr(self.voyage, "api_key", ""):
            return await self._rank_lexical(interests, exclude, now)

        try:
            term_vecs = np.asarray(await self._embed_queries(interests))
        except Exception:  # noqa: BLE001 - embedding outage falls back to topics
            return await self._rank_lexical(interests, exclude, now)

        saved_vecs = list((await self._paper_vectors(saved_ids)).values()) if saved_ids else []
        queries = list(term_vecs)
        saved_centroid = ranking.centroid(saved_vecs) if saved_vecs else None
        if saved_centroid is not None:
            queries.append(saved_centroid)

        candidate_ids: list[UUID] = []
        seen: set[UUID] = set()
        for max_distance in (CANDIDATE_MAX_DISTANCE, RELAXED_MAX_DISTANCE):
            for q in queries:
                hits = await self.chunk_repo.search_global(
                    list(q), max_distance=max_distance, limit=POOL_PER_QUERY
                )
                for paper, _ in hits:
                    if paper.id not in exclude and paper.id not in seen:
                        seen.add(paper.id)
                        candidate_ids.append(paper.id)
            if candidate_ids:
                break

        vectors = await self._paper_vectors(candidate_ids)
        ids = [pid for pid in candidate_ids if pid in vectors]
        if not ids:
            return await self._rank_lexical(interests, exclude, now)

        cand = np.stack([vectors[pid] for pid in ids])
        scores = ranking.score_candidates(
            cand, term_vecs, np.stack(saved_vecs) if saved_vecs else None
        )
        order = ranking.mmr(cand, scores["score"], k=min(len(ids), MAX_RANKED))
        entries = [
            {
                "paper_id": ids[i],
                "relevance": ranking.to_percent(scores["interest"][i]),
                "similarity": ranking.to_percent(scores["saved"][i]),
                "matched_interest": interests[int(scores["best_interest"][i])],
            }
            for i in order
        ]
        return {"entries": entries, "method": "embedding", "generated_at": now}

    async def _rank_lexical(self, interests, exclude, now) -> dict:
        """No embeddings available: rank stored papers by topic overlap."""
        hits = await self.paper_repo.find_by_topic_overlap(
            interests, exclude=exclude, limit=MAX_RANKED
        )
        lowered = {t.casefold(): t for t in interests}
        entries = []
        for paper, _overlap in hits:
            match = next(
                (lowered[t.casefold()] for t in (paper.topics or []) if t.casefold() in lowered),
                None,
            )
            entries.append(
                {"paper_id": paper.id, "relevance": None, "similarity": None, "matched_interest": match}
            )
        return {"entries": entries, "method": "lexical" if entries else "none", "generated_at": now}

    # --- related / similarity --------------------------------------------

    async def related(self, paper_id: UUID, *, limit: int = 5) -> list[RecommendedPaper]:
        """Papers nearest to this one in embedding space, diversified with MMR."""
        vec = (await self._paper_vectors([paper_id])).get(paper_id)
        if vec is None:
            return []
        hits = await self.chunk_repo.search_global(
            list(vec), max_distance=CANDIDATE_MAX_DISTANCE, limit=limit * 4 + 1
        )
        pool = [(p, d) for p, d in hits if p.id != paper_id]
        if not pool:
            return []
        vectors = await self._paper_vectors([p.id for p, _ in pool])
        pool = [(p, d) for p, d in pool if p.id in vectors]
        if not pool:
            return []
        cand = np.stack([vectors[p.id] for p, _ in pool])
        sims = np.array([1.0 - d for _, d in pool])
        order = ranking.mmr(cand, sims, k=min(limit, len(pool)))
        return [
            RecommendedPaper(
                paper=PaperResponse.model_validate(pool[i][0]),
                relevance=ranking.to_percent(sims[i]),
            )
            for i in order
        ]

    async def similarity_to_saved(
        self, project_id: UUID, paper_ids: list[UUID]
    ) -> dict[str, int | None]:
        """Max cosine of each paper to the project's saved papers (0-100)."""
        saved = await self.project_paper_repo.list_papers_for_project(project_id)
        saved_vecs = await self._paper_vectors([p.id for p in saved])
        targets = await self._paper_vectors(paper_ids)
        out: dict[str, int | None] = {str(pid): None for pid in paper_ids}
        if not saved_vecs or not targets:
            return out
        saved_matrix = ranking.unit(np.stack(list(saved_vecs.values())))
        for pid, vec in targets.items():
            sims = saved_matrix @ ranking.unit(vec)[0]
            # A saved paper is trivially 100% similar to itself; skip it.
            others = [s for sid, s in zip(saved_vecs.keys(), sims) if sid != pid]
            out[str(pid)] = ranking.to_percent(max(others)) if others else None
        return out
