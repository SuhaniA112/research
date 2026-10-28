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
import { join } from "node:path";

import {
  backend,
  findSystemPython,
  frontend,
  isWindows,
  pythonEnv,
  q,
  root,
  venvBin,
  venvPython,
} from "./platform.mjs";

const alembic = venvBin("alembic");

function run(cmd, cwd = root, env = process.env) {
  console.log(`\n> ${cmd}`);
  execSync(cmd, { cwd, stdio: "inherit", env, shell: true });
}

function ensureCopied(from, to, label) {
  if (existsSync(to)) {
    console.log(`✓ keep existing ${label}`);
    return;
  }
  copyFileSync(from, to);
  console.log(`✓ created ${label}`);
}

console.log(`PaperSearcher setup (${isWindows ? "Windows" : process.platform})\n`);

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
  const systemPython = findSystemPython();
  if (!systemPython) {
    console.error(
      isWindows
        ? "\nPython 3.11+ not found. Install it from python.org (tick \"Add to PATH\"), " +
            "or set PYTHON=<path to python.exe>, then re-run: npm run setup\n"
        : "\nPython 3.11+ not found. Install it, or set PYTHON=<path>, then re-run: npm run setup\n",
    );
    process.exit(1);
  }
  run(`${systemPython} -m venv .venv`, backend);
}
run(`${q(venvPython)} -m pip install -r requirements.txt`, backend, pythonEnv());
run(`${q(alembic)} upgrade head`, backend, pythonEnv());

console.log(`
Setup complete.

Next:
  npm run dev

Optional: add VOYAGE_API_KEY / OPENROUTER_API_KEY to backend/.env for fast search + embeddings.
UI only (no API): npm run dev:mock  (set VITE_USE_MOCKS=true in frontend/.env.local)
`);
