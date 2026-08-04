#!/usr/bin/env node
/** Start FastAPI with the local venv. */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const backend = join(root, "backend");
const uvicorn = join(backend, ".venv", "bin", "uvicorn");

if (!existsSync(uvicorn)) {
  console.error("Backend venv missing. Run: npm run setup");
  process.exit(1);
}

const child = spawn(
  uvicorn,
  ["app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
  { cwd: backend, stdio: "inherit", env: process.env },
);

child.on("exit", (code) => process.exit(code ?? 1));
