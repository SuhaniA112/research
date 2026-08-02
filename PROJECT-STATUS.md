# PaperSearcher — Project Status

This document describes what exists on `main` today and what remains to be done.
It reflects the state as of 2026-08-01, after merging `feature/save-to-project-rag` and `indexer` into `main`.

## What exists on `main`

### Backend

FastAPI + async SQLAlchemy + Postgres, with a repository → service → endpoint layering (see `backend/app/`).
Schema is created via `Base.metadata.create_all` at startup; there is no migration tool (no Alembic).

**Discovery** is one working data-fetching feature.
`ResearchService` queries four external Source Provider APIs live (Arxiv, OpenAlex, Semantic Scholar, DBLP) for a hardcoded list of interests and returns deduplicated results.
Nothing from Discovery is persisted; every call re-fetches from the internet.

**Save → Ingest → Retrieve → Answer** is the other, and it is now the full pipeline, not the abstract-only v1 originally scoped:

- `Project`, `Paper` (globally deduped by source + external_id), `Chunk` (pgvector-backed embedding), and `ProjectPaper` (the save join table) models.
- Saving a paper to a Project triggers inline ingestion via `PaperIndexer`: full PDF text is extracted and split into page-aware chunks when `pdf_url` is present, falling back to the abstract, falling back to the title, so a paper is never unembeddable. Each chunk is embedded via Voyage AI and stored as a `Chunk` row (`ChunkRepository.create_many_for_paper`).
- A Project-scoped `ask` endpoint: embeds the question, runs a pgvector cosine-similarity search scoped to that Project's saved papers, refuses to answer below a similarity threshold, and otherwise calls an LLM via OpenRouter for a generated answer with structured citations back to the source papers.
- An offline eval harness (`backend/eval/`): a script to synthetically generate a golden question set from ingested papers (meant to be hand-reviewed before trusting it), and a script to score both retrieval hit-rate and citation validity separately.
- `CONTEXT.md` (domain glossary), `docs/adr/0001-pgvector-for-embeddings.md`, and `docs/adr/0002-paper-indexer-drives-ingestion.md` (why `IngestionService` calls `PaperIndexer` instead of embedding the abstract directly) document the design.

The only persisted domain model outside this pipeline is `User`.
There is no login/session/auth wiring despite the model existing.

Full end-to-end verification (an actual embedding/generation call) still needs real `VOYAGE_API_KEY` and `OPENROUTER_API_KEY` values, which haven't been supplied yet.
Everything short of that has been verified: imports, the merged dependency set (`pymupdf`, `langchain-text-splitters`, `pgvector`) installs cleanly, and `PaperIndexer.prepare_chunks()` produces correct chunks for both the abstract-present and title-fallback cases.

### Frontend

A full set of UI screens exists (dashboard, all-projects, project overview, find sources, saved sources, source detail, mind map, onboarding, profile) built against static mock data in `frontend/src/data/mockData.ts`.
None of it talks to a real backend for Projects or Sources.
The "Save to Project" button (`SourceActions.tsx`) only updates local component state; it does not call any API.

## What needs to be done

1. Supply real Voyage AI and OpenRouter API keys, then finish end-to-end verification: save (including the multi-chunk full-text path), cross-project dedup, ask (both the "no relevant sources" and "answered with citations" paths), unsave, and the eval scripts.
2. Wire the frontend to the new backend: a real "Save to Project" call, and a new ask-a-question UI (no chat/Q&A UI exists anywhere in the frontend yet).
3. Add authentication. `Project` already has a nullable `user_id` column for forward compatibility, but nothing enforces it and there is no login flow.
4. An HNSW index on `Chunk.embedding`. Deliberately deferred until row counts grow past roughly 10k; the exact-search query and `vector_cosine_ops` choice already anticipate this.
5. A migration tool. Schema changes currently require editing models and relying on `create_all`, which only adds new tables and does not alter existing ones.
6. Optionally persist per-chunk metadata (`page_number`, `content_type`) that `PaperIndexer` already computes but `Chunk` doesn't yet store, to support page-level citations in the `ask` response. See `docs/adr/0002-paper-indexer-drives-ingestion.md`.
