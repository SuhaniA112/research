# PaperSearcher

Monorepo: FastAPI backend + React frontend + Postgres (pgvector).

## Quick start

Requires **Node 20+**, **Python 3.11+**, and **Docker Desktop**.

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
