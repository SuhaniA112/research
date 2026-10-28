#!/usr/bin/env node
/**
 * Run the backend venv's Python with the given arguments, on any OS.
 *
 *   node scripts/py.mjs scripts/e2e_save_ask.py          (cwd: repo root)
 *   node scripts/py.mjs --backend -m eval.run_eval ...   (cwd: backend/)
 *
 * Used by the npm scripts so nobody has to type `.venv/bin/python` (macOS/Linux)
 * vs `.venv\Scripts\python.exe` (Windows).
 */
import { spawn } from "node:child_process";

import { backend, pythonEnv, requireVenv, root, venvPython } from "./platform.mjs";

requireVenv();

let args = process.argv.slice(2);
let cwd = root;
if (args[0] === "--backend") {
  cwd = backend;
  args = args.slice(1);
}

const child = spawn(venvPython, args, { cwd, stdio: "inherit", env: pythonEnv() });
child.on("exit", (code) => process.exit(code ?? 1));
