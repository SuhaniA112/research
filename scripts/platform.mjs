/**
 * Cross-platform helpers shared by setup / dev / run scripts.
 *
 * Windows differs from macOS/Linux in three ways that matter here:
 * - venv executables live in `.venv\Scripts\*.exe`, not `.venv/bin/*`
 * - the Python launcher is usually `py -3` or `python`, not `python3`
 * - npm's `node_modules/.bin` shims are `*.cmd` files
 */
import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const isWindows = process.platform === "win32";

export const root = join(dirname(fileURLToPath(import.meta.url)), "..");
export const backend = join(root, "backend");
export const frontend = join(root, "frontend");

const MIN_PYTHON = [3, 11];

/** Path to an executable inside backend/.venv, e.g. venvBin("uvicorn"). */
export function venvBin(name) {
  return isWindows
    ? join(backend, ".venv", "Scripts", `${name}.exe`)
    : join(backend, ".venv", "bin", name);
}

export const venvPython = venvBin("python");

/** Path to a CLI installed in the root node_modules/.bin. */
export function nodeBin(name) {
  return join(root, "node_modules", ".bin", isWindows ? `${name}.cmd` : name);
}

/** Quote a path for a shell command line (handles spaces on all platforms). */
export function q(path) {
  return `"${path}"`;
}

/**
 * Environment for Python child processes. PYTHONUTF8 makes open()/print()
 * default to UTF-8 on Windows instead of the console code page (cp1252),
 * which otherwise breaks on non-ASCII paper titles and abstracts.
 */
export function pythonEnv(extra = {}) {
  return { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8", ...extra };
}

function pythonVersion(cmd) {
  try {
    const out = execSync(
      `${cmd} -c "import sys; print(sys.version_info[0], sys.version_info[1])"`,
      { stdio: ["ignore", "pipe", "ignore"] },
    )
      .toString()
      .trim();
    const [major, minor] = out.split(/\s+/).map(Number);
    return Number.isFinite(major) && Number.isFinite(minor) ? [major, minor] : null;
  } catch {
    return null;
  }
}

/**
 * Find a system Python >= 3.11 to create the venv with.
 * Honors $PYTHON first, then tries the platform's usual launchers.
 */
export function findSystemPython() {
  const candidates = [
    process.env.PYTHON,
    ...(isWindows ? ["py -3", "python", "python3"] : ["python3", "python"]),
  ].filter(Boolean);

  for (const cmd of candidates) {
    const version = pythonVersion(cmd);
    if (!version) continue;
    const [major, minor] = version;
    if (major > MIN_PYTHON[0] || (major === MIN_PYTHON[0] && minor >= MIN_PYTHON[1])) {
      return cmd;
    }
    console.warn(`  (skipping ${cmd}: Python ${major}.${minor} < ${MIN_PYTHON.join(".")})`);
  }
  return null;
}

export function requireVenv(hint = "npm run setup") {
  if (!existsSync(venvPython)) {
    console.error(`Backend venv missing. Run once:\n  ${hint}\n`);
    process.exit(1);
  }
}
