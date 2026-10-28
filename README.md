# PaperSearcher

Monorepo: FastAPI backend + React frontend + Postgres (pgvector).

## Quick start

Requires **Node 20+**, **Python 3.11+**, and **Docker Desktop**. Works on macOS, Linux
and Windows (see [Windows notes](#windows-notes)).

```bash
git checkout frontend-backend-wiring   # or main, once merged
npm run setup                          # once
npm run dev                            # Postgres + API (:8000) + UI (:5173)
```

Then open http://localhost:5173

`npm run setup` copies env files, starts Postgres, installs deps, and runs migrations.
`npm run dev` brings up the DB (if needed) and both servers.

### Optional API keys

Edit `backend/.env`:

- `VOYAGE_API_KEY` — faster discovery + embeddings on save
- `OPENROUTER_API_KEY` — ask / generation
  (optional: without it, or when free-tier limits hit, summaries fall back to the abstract and OpenRouter is paused for the `Retry-After` window)

### Frontend-only (mocks)

```bash
# in frontend/.env.local
VITE_USE_MOCKS=true

npm run dev:mock
```

### Other scripts

| Command | What it does |
|---|---|
| `npm run db:up` / `db:down` | Start / stop Postgres only |
| `npm run db:logs` | Tail Postgres logs |
| `npm run dev:api` | API only |
| `npm run dev:web` | Vite only |
| `npm run test:api` | Backend unit + API tests |
| `npm run e2e` | Search → save → ask → unsave against a running API |
| `npm run eval` | Retrieval eval over the golden set (see below) |
| `npm run eval:diagnostics` | Embedding-space diagnostics |
| `npm run eval:report` | HTML report from the latest eval + diagnostics |

### E2E (save → ask → unsave)

1. Put real keys in `backend/.env`: `VOYAGE_API_KEY`, `OPENROUTER_API_KEY`
2. `npm run dev` (or at least API + Postgres)
3. `npm run e2e`

### Benchmarks

`npm run bench` builds this checkout and `main`, then compares how much JS/CSS the
login page downloads (gzip). With the API running it also times the hub and the
project overview against the old request patterns (`--runs`, `--user-id`,
`--baseline <ref>` to change defaults). Results land in `.bench/latest.md`.

### Retrieval evaluation

Scripts live in `backend/eval/`; results go to `backend/eval/results/` (git-ignored).

1. **Golden set** — `npm run eval:golden -- --project-id <uuid> --count 10` drafts
   question → paper pairs from a project's saved papers. Hand-check them and set
   `"reviewed": true`. An item may list several relevant papers (optionally graded):
   `"relevant": [{"source": "arxiv", "external_id": "2401.0001", "grade": 2}, ...]`.
2. **Ranking metrics** — `npm run eval -- --project-id <uuid> [--k 1 3 5 10] [--skip-generation]`
   ranks the project's papers for each question with pgvector and reports
   precision@k, recall@k, F1@k, hit@k, nDCG@k, MRR and MAP, plus the hit rate at the
   production distance gate and (unless skipped) Ask citation validity.
3. **Embedding diagnostics** — `npm run eval:diagnostics -- --project-id <uuid>` (or `--all`)
   reports vector norms, anisotropy, effective dimensionality, hubness, a 2-D PCA layout of
   papers, and — with a golden set — relevant-vs-irrelevant similarity separation (ROC AUC)
   with a distance-threshold sweep for tuning `RETRIEVAL_MAX_DISTANCE`.
4. **Weight tuning** — `npm run eval:tune -- --project-id <uuid> [--write]` scores the
   golden set with the weighted relevance model (vector similarity + project fit +
   saved-paper similarity + recency + citations + topic overlap), grid-searches the
   weights, and reports raw-similarity baseline vs current vs tuned (leave-one-out).
   `--write` saves `backend/app/services/recommendation/weights.json`; restart the API.
5. **Report** — `npm run eval:report` writes `backend/eval/results/report.html` with charts
   for all of the above. It is a single file with no external assets.

Metric and diagnostic math is unit-tested in `backend/tests/unit/test_eval_*.py`
and `test_embedding_diagnostics.py`.

## Windows notes

`npm run setup` / `npm run dev` work from PowerShell or Command Prompt; no WSL needed.

- Install **Python 3.11+** from python.org and tick *Add python.exe to PATH*. Setup finds
  it via `py -3`, then `python`; to use a specific interpreter, set `PYTHON` first
  (PowerShell: `$env:PYTHON = "C:\Path\To\python.exe"`).
- Install **Docker Desktop** with the WSL 2 backend and start it before `npm run setup`.
- The scripts resolve the venv at `backend\.venv\Scripts\` automatically, and run Python
  in UTF-8 mode so non-ASCII paper titles don't break on the Windows console.
- To call the venv directly: `backend\.venv\Scripts\python.exe` (Windows) or
  `backend/.venv/bin/python` (macOS / Linux).
- `.gitattributes` normalises line endings, so a Windows checkout no longer shows every
  file as modified when opened from WSL or another tool.
