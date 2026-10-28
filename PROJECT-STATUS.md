# PaperSearcher — Project Status

This document describes what exists on `main` / current wiring branches today
and what remains to be done. Updated 2026-10-28.

## What exists

### Backend

FastAPI + async SQLAlchemy + Postgres (pgvector). Schema is applied with **Alembic**
(`alembic upgrade head`); startup does **not** call `create_all`.

**Discovery**

- `POST /api/v1/research/search` — database-first discovery (Voyage embeddings when keyed)
- Legacy `GET /api/v1/research/papers` — live Source Provider fetch fallback

**Projects / papers**

- Project CRUD (`GET/POST/DELETE /projects`, `GET /projects/{id}`)
- Save / list / unsave papers on a project
- `GET /api/v1/papers/{id}` — paper detail by id (supports source-page refresh)
- Project responses include `source_count` and aggregated `topics` from saved papers

**Save → Ingest → Ask**

- Saving triggers `PaperIndexer` (PDF → abstract → title fallback) + Voyage embeddings
- `POST /projects/{id}/ask` — retrieval + OpenRouter answer with citations
- Offline eval harness under `backend/eval/`: golden set, ranking metrics
  (precision/recall/F1/hit/nDCG@k, MRR, MAP), embedding diagnostics (anisotropy,
  effective dimensionality, hubness, PCA, relevance separation + threshold sweep),
  and an HTML report with charts (`npm run eval`, `eval:diagnostics`, `eval:report`)

**Summaries / key findings**

- `POST /api/v1/papers/summarize` — leveled summaries (general / graduate / expert) + key findings

**Source validity stats**

- Providers now report `citation_count`, `venue`, `is_open_access`, `is_peer_reviewed`
  on papers (migration `0009`; NULL = provider did not say; fills in on next refresh)
- `GET /api/v1/projects/{id}/stats/validity` — Cross-cited / Peer-reviewed / Open access /
  Multi-author percentages over saved papers (each counted only over papers with data),
  plus a 0–100 score and status label. Logic in `app/services/source_validity.py`

**Recommendations & stats**

- `GET /api/v1/digest` — personalised hub papers: interest + saved-paper embeddings,
  pgvector ANN, MMR diversity, cached per user; paged, falls back to topic overlap
- `GET /api/v1/papers/{id}/related`, `POST /api/v1/projects/{id}/similarity`
- `GET /api/v1/projects/{id}/stats` — breakdown, recency, validity, topics in one call
- Ranking uses a weighted feature model (`recommendation/features.py`): similarity to the
  search, project and saved papers plus recency, citations and topic overlap; weights are
  tuned on the golden set with `npm run eval:tune` (leave-one-out validated)
- Profiles are per user (`/users/me` scoped by the current user)

**Auth**

- `User` model / CRUD by UUID exists; **no** login/session/`/users/me` yet
- `Project.user_id` is unused for ownership

### Frontend

React app talks to the API through `frontend/src/api/*` adapters.

- `VITE_USE_MOCKS=false` → real projects, search, save/unsave, paper GET, client mind map
- Soft-empty / `[X]%` for digest, summaries, related/citing, stats, profile `/me`
- Search history is **localStorage**-backed (sidebar stays in sync on delete)
- Root scripts: `npm run setup`, `npm run dev` (Postgres + API + Vite) — cross-platform
  (macOS, Linux, Windows; see README "Windows notes")

## What needs to be done

1. **API keys + E2E** — set real `VOYAGE_API_KEY` / `OPENROUTER_API_KEY` in `backend/.env`,
   run API, then `npm run e2e`
   (ask is API-only for verification; **no Ask UI** — out of product scope)
2. **Auth** — in progress on `auth-clerk-migration` (Clerk); login/session, `/users/me`,
   scope projects by `user_id`
3. **Citing papers** — needs a citation graph (Semantic Scholar/OpenAlex); still empty
4. **Profile password actions** — Change password / Delete account unfinished (depends on auth)
5. **Validity backfill (optional)** — papers saved before migration `0009` only get
   citation / venue / OA / peer-review data when a search re-fetches them

### Out of scope

- **Ask UI** — backend `POST /projects/{id}/ask` remains for eval/E2E; no chat/Q&A screen in the app
