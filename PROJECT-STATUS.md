# PaperSearcher — Project Status

This document describes what exists on `main` / current wiring branches today
and what remains to be done. Updated 2026-08-04.

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
- Offline eval harness under `backend/eval/`

**Auth**

- `User` model / CRUD by UUID exists; **no** login/session/`/users/me` yet
- `Project.user_id` is unused for ownership

### Frontend

React app talks to the API through `frontend/src/api/*` adapters.

- `VITE_USE_MOCKS=false` → real projects, search, save/unsave, paper GET, client mind map
- Soft-empty / `[X]%` for digest, summaries, related/citing, stats, profile `/me`
- Search history is **localStorage**-backed (sidebar stays in sync on delete)
- Root scripts: `npm run setup`, `npm run dev` (Postgres + API + Vite)

## What needs to be done

1. **API keys + E2E** — set real `VOYAGE_API_KEY` / `OPENROUTER_API_KEY` in `backend/.env`,
   run API, then `backend/.venv/bin/python scripts/e2e_save_ask.py`
   (ask is API-only for verification; **no Ask UI** — out of product scope)
2. **Auth** — login/session, `/users/me`, scope projects by `user_id`
3. **Summaries / digest** — leveled AI summaries + hub digest still need backends (or hide)
4. **Stats / related / key findings** — breakdown/validity still placeholders; related/cites empty
5. **Persist project create fields** — topics/keywords/reading level dropped on create
6. **Profile password actions** — Change password / Delete account unfinished
7. **Page-level ask citations** — persist `page_number` / `content_type` on chunks (ADR 0002);
   only relevant if ask stays API/eval-only
8. **HNSW** on `Chunk.embedding` when row counts grow (~10k+)

### Out of scope

- **Ask UI** — backend `POST /projects/{id}/ask` remains for eval/E2E; no chat/Q&A screen in the app
