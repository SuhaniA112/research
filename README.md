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

### Auth

By default both sides run in **mock auth mode** — every request is authenticated
as a fixed local dev user, no Clerk account needed. This is the out-of-the-box
setup from `npm run setup` / `npm run dev`.

To exercise real Clerk sign-in/sign-up locally:

1. Create a Clerk application at [clerk.com](https://clerk.com) (email/password only
   is enough to start).
2. In `backend/.env`, set `AUTH_MODE=clerk` and fill in `CLERK_SECRET_KEY` and
   `CLERK_JWT_KEY` (dashboard: API Keys → Show JWT Public Key).
3. In `frontend/.env.local`, set `VITE_AUTH_MODE=clerk` and fill in
   `VITE_CLERK_PUBLISHABLE_KEY`.
4. Both sides must be switched together — mixing `mock` and `clerk` across
   frontend/backend won't authenticate correctly.

`AUTH_MODE=mock` is refused at startup whenever `APP_ENV=production`, so it can't
accidentally ship live.

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

### E2E (save → ask → unsave)

1. Put real keys in `backend/.env`: `VOYAGE_API_KEY`, `OPENROUTER_API_KEY`
2. `npm run dev` (or at least API + Postgres)
3. `backend/.venv/bin/python scripts/e2e_save_ask.py`
