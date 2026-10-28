#!/usr/bin/env node
/**
 * Start Postgres (if needed), then API + Vite together.
 */
import { execSync, spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { createConnection } from "node:net";

import { nodeBin, q, root, venvPython } from "./platform.mjs";

const concurrently = nodeBin("concurrently");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function canConnect(port, host = "127.0.0.1") {
  return new Promise((resolve) => {
    const socket = createConnection({ port, host }, () => {
      socket.end();
      resolve(true);
    });
    socket.on("error", () => resolve(false));
  });
}

async function waitForPostgres(timeoutMs = 60_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await canConnect(5432)) return;
    await sleep(1000);
  }
  throw new Error("Postgres did not become ready on :5432");
}

if (!existsSync(venvPython)) {
  console.error("Backend not set up yet. Run once:\n  npm run setup\n");
  process.exit(1);
}

if (!existsSync(concurrently)) {
  console.error("Root deps missing. Run once:\n  npm run setup\n");
  process.exit(1);
}

try {
  console.log("> docker compose up -d");
  execSync("docker compose up -d", {
    cwd: root,
    stdio: "inherit",
    env: process.env,
  });
} catch {
  console.error("\nDocker failed. Start Docker Desktop, then re-run: npm run dev\n");
  process.exit(1);
}

console.log("Waiting for Postgres…");
try {
  await waitForPostgres();
} catch (err) {
  console.error(String(err.message || err));
  process.exit(1);
}
console.log("Postgres is up.\n");

// shell: true so Windows can run the concurrently.cmd shim; quote for spaces.
const child = spawn(
  q(concurrently),
  [
    "-n",
    "api,web",
    "-c",
    "blue,green",
    "npm:dev:api",
    "npm:dev:web",
  ],
  { cwd: root, stdio: "inherit", env: process.env, shell: true },
);

child.on("exit", (code) => process.exit(code ?? 1));
