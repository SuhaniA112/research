#!/usr/bin/env node
/**
 * One-time (or occasional) setup:
 * - copy env files if missing
 * - start Postgres
 * - install frontend + root deps
 * - create backend venv, pip install, migrate
 */
import { execSync } from "node:child_process";
import { copyFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const backend = join(root, "backend");
const frontend = join(root, "frontend");
const venvPython = join(backend, ".venv", "bin", "python");
const alembic = join(backend, ".venv", "bin", "alembic");

function run(cmd, cwd = root) {
  console.log(`\n> ${cmd}`);
  execSync(cmd, { cwd, stdio: "inherit", env: process.env, shell: true });
}

function ensureCopied(from, to, label) {
  if (existsSync(to)) {
    console.log(`✓ keep existing ${label}`);
    return;
  }
  copyFileSync(from, to);
  console.log(`✓ created ${label}`);
}

console.log("PaperSearcher setup\n");

ensureCopied(
  join(backend, ".env.example"),
  join(backend, ".env"),
  "backend/.env",
);
ensureCopied(
  join(frontend, ".env.example"),
  join(frontend, ".env.local"),
  "frontend/.env.local",
);

try {
  run("docker compose up -d");
} catch {
  console.error(
    "\nDocker failed. Start Docker Desktop, then re-run: npm run setup\n",
  );
  process.exit(1);
}

run("npm install");
run("npm install", frontend);

if (!existsSync(venvPython)) {
  run("python3 -m venv .venv", backend);
}
run(`"${venvPython}" -m pip install -r requirements.txt`, backend);
run(`"${alembic}" upgrade head`, backend);

console.log(`
Setup complete.

Next:
  npm run dev

Optional: add VOYAGE_API_KEY / OPENROUTER_API_KEY to backend/.env for fast search + embeddings.
UI only (no API): npm run dev:mock  (set VITE_USE_MOCKS=true in frontend/.env.local)
`);
