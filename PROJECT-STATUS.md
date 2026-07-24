# PaperSearcher — Project Status

This document describes what exists on `main` today, what's built but not yet merged, and what remains to be done.
It reflects the state as of 2026-07-24.

## What exists on `main`

### Backend

FastAPI + async SQLAlchemy + Postgres, with a repository → service → endpoint layering (see `backend/app/`).
Schema is created via `Base.metadata.create_all` at startup; there is no migration tool (no Alembic).

**Discovery** is the only working data-fetching feature.
`ResearchService` queries four external Source Provider APIs live (Arxiv, OpenAlex, Semantic Scholar, DBLP) for a hardcoded list of interests and returns deduplicated results.
Nothing is persisted; every call re-fetches from the internet.

The only persisted domain model is `User`.
There is no login/session/auth wiring despite the model existing.

There is no `Project` or `Paper` model on `main`.
There is no vector database, no embeddings, no LLM integration, and no evaluation tooling.

### Frontend

A full set of UI screens exists (dashboard, all-projects, project overview, find sources, saved sources, source detail, mind map, onboarding, profile) built against static mock data in `frontend/src/data/mockData.ts`.
None of it talks to a real backend for Projects or Sources.
The "Save to Project" button (`SourceActions.tsx`) only updates local component state; it does not call any API.

## Built, not yet merged

Branch `feature/save-to-project-rag` implements a full Save → Ingest → Retrieve → Answer pipeline, designed through a domain-modeling/grilling session and an implementation plan:

- `Project`, `Paper` (globally deduped by source + external_id), `Chunk` (pgvector-backed embedding), and `ProjectPaper` (the save join table) models.
- Saving a paper to a Project triggers inline ingestion: the paper is persisted, its abstract (or title, if the source has no abstract) is embedded via Voyage AI, and stored as a `Chunk`.
- A Project-scoped `ask` endpoint: embeds the question, runs a pgvector cosine-similarity search scoped to that Project's saved papers, refuses to answer below a similarity threshold, and otherwise calls an LLM via OpenRouter for a generated answer with structured citations back to the source papers.
- An offline eval harness (`backend/eval/`): a script to synthetically generate a golden question set from ingested papers (meant to be hand-reviewed before trusting it), and a script to score both retrieval hit-rate and citation validity separately.
- `CONTEXT.md` (domain glossary) and `docs/adr/0001-pgvector-for-embeddings.md` (the pgvector-vs-dedicated-vector-database decision) also live only on that branch.

That branch is not yet merged because full verification needs real `VOYAGE_API_KEY` and `OPENROUTER_API_KEY` values, which haven't been supplied yet.
Everything short of an actual embedding/generation call has been verified: the Postgres image switch to `pgvector/pgvector:pg16`, the `vector` extension bootstrap, schema creation for all four new tables, Project CRUD, and the save flow's logic up to the point it calls Voyage.

## What needs to be done

1. Supply real Voyage AI and OpenRouter API keys, then finish end-to-end verification on the feature branch: save, cross-project dedup, ask (both the "no relevant sources" and "answered with citations" paths), unsave, and the eval scripts.
2. Merge `feature/save-to-project-rag` into `main` once verified.
3. Wire the frontend to the new backend: a real "Save to Project" call, and a new ask-a-question UI (no chat/Q&A UI exists anywhere in the frontend yet).
4. Add authentication. `Project` already has a nullable `user_id` column for forward compatibility, but nothing enforces it and there is no login flow.
5. Full-text PDF ingestion. Deliberately deferred; v1 only indexes title + abstract.
6. An HNSW index on `Chunk.embedding`. Deliberately deferred until row counts grow past roughly 10k; the exact-search query and `vector_cosine_ops` choice already anticipate this.
7. A migration tool. Schema changes currently require editing models and relying on `create_all`, which only adds new tables and does not alter existing ones.
