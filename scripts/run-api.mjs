#!/usr/bin/env node
/** Start FastAPI with the local venv. */
import { spawn } from "node:child_process";

import { backend, pythonEnv, requireVenv, venvPython } from "./platform.mjs";

requireVenv();

// `python -m uvicorn` avoids depending on the platform-specific uvicorn shim.
const child = spawn(
  venvPython,
  ["-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
  { cwd: backend, stdio: "inherit", env: pythonEnv() },
);

child.on("exit", (code) => process.exit(code ?? 1));
