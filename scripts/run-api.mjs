#!/usr/bin/env node
/** Start FastAPI with the local venv. */
import { spawn } from "node:child_process";

import { backend, pythonEnv, requireVenv, venvPython } from "./platform.mjs";

requireVenv();

// `python -m uvicorn` avoids depending on the platform-specific uvicorn shim.
// Only app code triggers reloads (not tests, eval output, or .venv).
const args = [
  "-m", "uvicorn", "app.main:app", "--reload", "--reload-dir", "app",
  "--host", "127.0.0.1", "--port", "8000",
];

let stopping = false;
let restarts = 0;
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    stopping = true;
  });
}

// On Windows the reloader occasionally exits after a code change; bring it back.
function start() {
  const child = spawn(venvPython, args, { cwd: backend, stdio: "inherit", env: pythonEnv() });
  child.on("exit", (code) => {
    if (stopping || code === 0 || restarts >= 5) process.exit(code ?? 1);
    restarts += 1;
    console.log(`API exited (code ${code}); restarting (${restarts}/5)...`);
    setTimeout(start, 1000);
  });
}
start();
