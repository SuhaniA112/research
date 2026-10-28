"""Personalised recommendations: hub digest, related papers, similarity to saved.

Database-first: candidates come from pgvector ANN over stored chunk embeddings,
so a digest needs one batched embedding call (cached) and a few index lookups
instead of live provider searches.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from uuid import UUID

import numpy as np

from app.models.user import User
from app.schemas.paper import PaperResponse
from app.schemas.recommendation import DigestResponse, PaperScore, RecommendedPaper
from app.services.recommendation import features as feat
from app.services.recommendation import ranking

logger = logging.getLogger(__name__)

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


def project_text(project) -> str:
    """What a project is about, as one string for embedding."""
    return ". ".join(
        p
        for p in (
            project.name,
            project.description or "",
            ", ".join(project.topics or []),
            ", ".join(project.keywords or []),
        )
        if p
    )


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
        project_embedding_repo=None,
    ) -> None:
        self.project_embedding_repo = project_embedding_repo
        self.weights = feat.load_weights()
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

    async def _project_vector(self, project) -> np.ndarray | None:
        """Stored project embedding; (re)computed only when the project's text changes.

        Storing it keeps scores identical across pages and API restarts, and avoids
        repeat embedding calls on rate-limited keys.
        """
        text = project_text(project)
        repo = self.project_embedding_repo
        row = await repo.get(project.id) if repo is not None else None
        if row is not None and row.text == text:
            return np.asarray(row.embedding, dtype=np.float64)
        if getattr(self.voyage, "api_key", ""):
            try:
                vec = (await self._embed_queries([text]))[0]
                if repo is not None:
                    await repo.upsert(project.id, text, list(vec))
                return np.asarray(vec, dtype=np.float64)
            except Exception as exc:  # noqa: BLE001 - e.g. rate limit
                logger.warning("project embedding failed (%s)", exc)
        # Stale beats missing: the text changed but re-embedding failed.
        return np.asarray(row.embedding, dtype=np.float64) if row is not None else None

    def _paper_features(
        self,
        paper,
        *,
        semantic: float | None,
        saved: float | None,
        search: float | None = None,
        context: set[str] | frozenset = frozenset(),
    ) -> dict[str, float | None]:
        """Feature vector for the weighted model (see features.py)."""
        return {
            "search": feat.similarity_feature(search),
            "semantic": feat.similarity_feature(semantic),
            "saved": feat.similarity_feature(saved),
            "recency": feat.recency_feature(getattr(paper, "year", None), datetime.now().year),
            "citations": feat.citation_feature(getattr(paper, "citation_count", None)),
            "topic": feat.topic_feature(getattr(paper, "topics", None) or [], set(context)),
        }

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
        saved = await self.project_paper_repo.list_papers_for_user(user.id)
        saved_ids = sorted(p.id for p in saved)
        key = (tuple(interests), tuple(saved_ids), _week_start())

        cached = _digest_cache.get(user.id)
        if not refresh and cached and cached[0] == key and cached[1] > time.time():
            ranked = cached[2]
        else:
            ranked = await self._rank(interests, saved_ids) if interests or saved_ids else None
            if not ranked or not ranked["entries"]:
                # Never return an empty hub: fall back to recently added papers.
                ranked = await self._rank_recent(set(saved_ids))
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
            # Tells the client to run a live search to grow the pool.
            sparse=bool(interests)
            and (ranked["method"] != "embedding" or len(entries) < SPARSE_THRESHOLD),
            method=ranked["method"],
            generated_at=ranked["generated_at"],
        )

    async def _rank(
        self,
        interests: list[str],
        saved_ids: list[UUID],
        term_vecs: np.ndarray | None = None,
    ) -> dict:
        """Rank stored papers; ``term_vecs`` skips embedding when vectors are known."""
        now = datetime.now(timezone.utc)
        exclude = set(saved_ids)
        if term_vecs is None and not getattr(self.voyage, "api_key", ""):
            return await self._rank_lexical(interests, exclude, now)

        saved_vecs = list((await self._paper_vectors(saved_ids)).values()) if saved_ids else []
        saved_centroid = ranking.centroid(saved_vecs) if saved_vecs else None

        if term_vecs is None and interests:
            try:
                term_vecs = np.asarray(await self._embed_queries(interests))
            except Exception as exc:  # noqa: BLE001 - e.g. Voyage rate limit
                logger.warning("digest: embedding interests failed (%s)", exc)
                if saved_centroid is None:
                    return await self._rank_lexical(interests, exclude, now)
                # Stored paper vectors need no API call: rank by saved papers instead.
                interests = []
        if term_vecs is None:
            # Cold start (no interests yet): rank by closeness to what the user saved.
            if saved_centroid is None:
                return {"entries": [], "method": "none", "generated_at": now}
            term_vecs = saved_centroid[None, :]
        queries = list(term_vecs)
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
        # Weighted model: similarity plus recency, citations and topic overlap.
        meta = await self.paper_repo.get_many(ids)
        context = feat.tokens(interests)
        composite = np.array(
            [
                feat.composite(
                    self._paper_features(
                        meta.get(pid),
                        semantic=float(scores["interest"][i]),
                        saved=None if np.isnan(scores["saved"][i]) else float(scores["saved"][i]),
                        context=context,
                    ),
                    self.weights,
                )
                or 0.0
                for i, pid in enumerate(ids)
            ]
        )
        order = ranking.mmr(cand, composite, k=min(len(ids), MAX_RANKED))
        entries = [
            {
                "paper_id": ids[i],
                "relevance": ranking.to_percent(scores["interest"][i]),
                "similarity": ranking.to_percent(scores["saved"][i]),
                "matched_interest": (
                    interests[int(scores["best_interest"][i])] if interests else None
                ),
            }
            for i in order
        ]
        logger.info("digest: method=embedding candidates=%d", len(entries))
        return {"entries": entries, "method": "embedding", "generated_at": now}

    async def _rank_recent(self, exclude: set[UUID]) -> dict:
        logger.info("digest: method=recent (no interests or matches)")
        papers = await self.paper_repo.list_recent(exclude=exclude, limit=MAX_RANKED)
        entries = [
            {"paper_id": p.id, "relevance": None, "similarity": None, "matched_interest": None}
            for p in papers
        ]
        return {
            "entries": entries,
            "method": "recent" if entries else "none",
            "generated_at": datetime.now(timezone.utc),
        }

    async def _rank_lexical(self, interests, exclude, now) -> dict:
        """No embeddings available: rank stored papers by topic overlap."""
        hits = await self.paper_repo.find_by_topic_overlap(
            interests, exclude=exclude, limit=MAX_RANKED
        )
        logger.info("digest: method=lexical (no embeddings available)")
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

    async def project_suggestions(self, project, *, limit: int = 10) -> list[RecommendedPaper]:
        """Stored papers that fit a project (its text + saved papers), excluding saved ones."""
        saved = await self.project_paper_repo.list_papers_for_project(project.id)
        saved_ids = sorted(p.id for p in saved)
        vec = await self._project_vector(project)
        ranked = await self._rank(
            [project_text(project)], saved_ids, vec[None, :] if vec is not None else None
        )
        if not ranked["entries"]:
            ranked = await self._rank_recent(set(saved_ids))
        page = ranked["entries"][:limit]
        papers = await self.paper_repo.get_many([e["paper_id"] for e in page])
        return [
            RecommendedPaper(
                paper=PaperResponse.model_validate(papers[e["paper_id"]]),
                relevance=e["relevance"],
                similarity=e["similarity"],
            )
            for e in page
            if e["paper_id"] in papers
        ]

    async def project_scores(
        self, project, paper_ids: list[UUID], query: str | None = None
    ) -> dict[str, PaperScore]:
        """Score papers against a project: its description, its saved papers, and a query."""
        out = {str(pid): PaperScore() for pid in paper_ids}
        targets = await self._paper_vectors(paper_ids)
        if not targets:
            return out

        raw = await self._project_vector(project)
        project_vec = ranking.unit(raw)[0] if raw is not None else None
        query_vec = None
        if query and query.strip() and getattr(self.voyage, "api_key", ""):
            try:
                query_vec = ranking.unit((await self._embed_queries([query.strip()]))[0])[0]
            except Exception as exc:  # noqa: BLE001 - rate limits etc.
                logger.warning("project scores: query embedding failed (%s)", exc)

        saved = await self.project_paper_repo.list_papers_for_project(project.id)
        saved_vecs = await self._paper_vectors([p.id for p in saved])
        saved_ids = list(saved_vecs.keys())
        meta = await self.paper_repo.get_many(list(targets))
        context = feat.tokens(
            [*(project.topics or []), *(project.keywords or []), query or ""]
        )
        saved_matrix = (
            ranking.unit(np.stack([saved_vecs[s] for s in saved_ids])) if saved_ids else None
        )

        for pid, vec in targets.items():
            v = ranking.unit(vec)[0]
            relevance = float(project_vec @ v) if project_vec is not None else None
            search = float(query_vec @ v) if query_vec is not None else None
            similarity = None
            if saved_matrix is not None:
                # A saved paper is trivially identical to itself; compare to the others.
                others = [s for sid, s in zip(saved_ids, saved_matrix @ v) if sid != pid]
                similarity = float(max(others)) if others else None
            features = self._paper_features(
                meta.get(pid), semantic=relevance, saved=similarity, search=search, context=context
            )
            out[str(pid)] = PaperScore(
                relevance=ranking.to_percent(relevance),
                similarity=ranking.to_percent(similarity),
                search_match=ranking.to_percent(search),
                score=feat.composite(features, self.weights),
                features=features,
            )
        return out

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
