#!/usr/bin/env node
/**
 * Benchmarks for login load and hub/overview latency.
 *
 *   npm run bench                         # bundle + API, baseline = main
 *   npm run bench -- --bundle --baseline <git-ref>
 *   npm run bench -- --api --runs 15      # needs `npm run dev` (or dev:api) running
 *
 * Bundle: builds this checkout and the baseline ref, compares the JS/CSS the
 * login page must download (entry + static imports, gzip).
 * API: times the old hub/overview request patterns against the new endpoints.
 * Results: .bench/results-<timestamp>.json and .bench/latest.md
 */
import { execSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

import { frontend, isWindows, root } from "./platform.mjs";

const args = process.argv.slice(2);
const flag = (name) => args.includes(`--${name}`);
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const runBundle = flag("bundle") || !flag("api");
const runApi = flag("api") || !flag("bundle");
const baselineRef = opt("baseline", "main");
const runs = Number(opt("runs", "10"));
const apiBase = opt("api-base", "http://127.0.0.1:8000/api/v1");
const benchDir = join(root, ".bench");
mkdirSync(benchDir, { recursive: true });

const kb = (bytes) => `${(bytes / 1024).toFixed(1)} KB`;
const ms = (v) => `${Math.round(v)} ms`;
const pct = (before, after) => `${(((before - after) / before) * 100).toFixed(0)}%`;

// ---------- bundle ----------

function buildAt(srcRoot, outDir) {
  const vite = join(frontend, "node_modules", "vite", "bin", "vite.js");
  rmSync(outDir, { recursive: true, force: true });
  execSync(`node "${vite}" build --manifest --outDir "${outDir}" --emptyOutDir --logLevel error`, {
    cwd: join(srcRoot, "frontend"),
    stdio: "inherit",
  });
}

function loginPayload(outDir) {
  const manifestPath = [join(outDir, ".vite", "manifest.json"), join(outDir, "manifest.json")].find(existsSync);
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  const entryKey = Object.keys(manifest).find((k) => manifest[k].isEntry);
  const files = new Set();
  const visit = (key) => {
    const chunk = manifest[key];
    if (!chunk || files.has(chunk.file)) return;
    files.add(chunk.file);
    (chunk.css ?? []).forEach((c) => files.add(c));
    (chunk.imports ?? []).forEach(visit); // static imports only; lazy routes excluded
  };
  visit(entryKey);
  const size = (f) => {
    const buf = readFileSync(join(outDir, f));
    return { raw: buf.length, gzip: gzipSync(buf).length };
  };
  const sum = (list) => list.reduce((a, f) => {
    const s = size(f);
    return { raw: a.raw + s.raw, gzip: a.gzip + s.gzip };
  }, { raw: 0, gzip: 0 });
  const allJs = Object.values(manifest).map((c) => c.file).filter((f) => f.endsWith(".js"));
  return {
    login: sum([...files]),
    loginJs: sum([...files].filter((f) => f.endsWith(".js"))),
    allJs: sum([...new Set(allJs)]),
    chunks: new Set(allJs).size,
  };
}

function benchBundle() {
  console.log(`\n== Bundle: current vs ${baselineRef} ==`);
  const currentOut = join(benchDir, "build-current");
  buildAt(root, currentOut);
  const current = loginPayload(currentOut);

  const wt = join(benchDir, "baseline-src");
  rmSync(wt, { recursive: true, force: true });
  execSync(`git worktree prune && git worktree add --detach "${wt}" ${baselineRef}`, { cwd: root, stdio: "ignore" });
  try {
    // Reuse this checkout's node_modules (junction works without admin on Windows).
    symlinkSync(join(frontend, "node_modules"), join(wt, "frontend", "node_modules"), isWindows ? "junction" : "dir");
    const baseOut = join(benchDir, "build-baseline");
    buildAt(wt, baseOut);
    const baseline = loginPayload(baseOut);
    return { baselineRef, baseline, current };
  } finally {
    execSync(`git worktree remove --force "${wt}"`, { cwd: root, stdio: "ignore" });
  }
}

// ---------- API ----------

async function call(method, path, userId, body) {
  const res = await fetch(`${apiBase}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...(userId ? { "X-User-ID": userId } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status} ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

async function timeIt(fn) {
  const t = performance.now();
  await fn();
  return performance.now() - t;
}

function summarize(samples) {
  const s = [...samples].sort((a, b) => a - b);
  const q = (p) => s[Math.min(s.length - 1, Math.floor(p * s.length))];
  return { p50: q(0.5), p95: q(0.95), mean: s.reduce((a, b) => a + b, 0) / s.length, n: s.length };
}

/** The existing user with the most projects (your real data), else a new bench user. */
async function pickUser() {
  const users = await call("GET", "/users?limit=50", null);
  let best = null;
  for (const u of users) {
    const n = (await call("GET", "/projects", u.id)).length;
    if (!best || n > best.n) best = { id: u.id, n };
  }
  if (best?.n) return best.id;
  return (await call("POST", "/users", null, {
    email: `bench-${Date.now()}@example.com`,
    full_name: "Bench User",
    password: "temporary-password-123",
  })).id;
}

async function benchApi() {
  console.log(`\n== API latency (${runs} runs each) ==`);
  const userId = opt("user-id", null) ?? (await pickUser());
  const interests = opt("interests", "machine learning,computer vision,natural language processing").split(",");
  const me = await call("GET", "/users/me", userId);
  if (!me.research_areas.length) await call("PATCH", "/users/me", userId, { research_areas: interests });
  const projects = await call("GET", "/projects", userId);
  const terms = (me.research_areas.length ? me.research_areas : interests).slice(0, 4);

  // Old hub: profile + projects (twice, as the page did) + saved lists + one discovery search per interest.
  const oldHub = async () => {
    const digest = async () => {
      const [, projs] = await Promise.all([call("GET", "/users/me", userId), call("GET", "/projects", userId)]);
      await Promise.all(projs.map((p) => call("GET", `/projects/${p.id}/papers`, userId)));
      await Promise.all(terms.map((q) => call("POST", "/research/search", userId, { query: q }).catch(() => null)));
    };
    await Promise.all([call("GET", "/users/me", userId), digest(), call("GET", "/projects", userId)]);
  };
  // New hub: three independent calls; the digest is one ranked, cached request.
  const newHub = (refresh) => () => Promise.all([
    call("GET", "/users/me", userId),
    call("GET", `/digest?limit=5${refresh ? "&refresh=true" : ""}`, userId),
    call("GET", "/projects", userId),
  ]);

  const results = {};
  const run = async (name, fn) => {
    const samples = [];
    for (let i = 0; i < runs; i++) samples.push(await timeIt(fn));
    results[name] = summarize(samples);
    console.log(`  ${name.padEnd(28)} p50 ${ms(results[name].p50)}  p95 ${ms(results[name].p95)}`);
  };

  await run("hub: old flow", oldHub);
  await run("hub: new digest (re-rank)", newHub(true));
  await run("hub: new digest (cached)", newHub(false));

  const project = projects[0];
  if (project) {
    const pid = project.id;
    await run("overview: old (3 requests)", () => Promise.all([
      call("GET", `/projects/${pid}/papers`, userId),
      call("GET", `/projects/${pid}/papers`, userId),
      call("GET", `/projects/${pid}/stats/validity`, userId),
    ]));
    await run("overview: new (/stats)", () => call("GET", `/projects/${pid}/stats`, userId));
  } else {
    console.log("  (no projects for this user; pass --user-id <your id> to time the overview stats)");
  }
  return { userId, terms, results };
}

// ---------- report ----------

const report = { created_at: new Date().toISOString() };
if (runBundle) report.bundle = benchBundle();
if (runApi) {
  try {
    report.api = await benchApi();
  } catch (err) {
    console.error(`\nAPI benchmark skipped: ${err.message}\nStart the API with \`npm run dev\` and retry with --api.`);
  }
}

const lines = ["# Benchmark results", "", `_${report.created_at}_`, ""];
if (report.bundle) {
  const { baseline: b, current: c, baselineRef: ref } = report.bundle;
  lines.push(
    `## Login page download (gzip), vs \`${ref}\``, "",
    "| | Before | After | Change |", "|---|---|---|---|",
    `| JS + CSS for /login | ${kb(b.login.gzip)} | ${kb(c.login.gzip)} | -${pct(b.login.gzip, c.login.gzip)} |`,
    `| JS for /login | ${kb(b.loginJs.gzip)} | ${kb(c.loginJs.gzip)} | -${pct(b.loginJs.gzip, c.loginJs.gzip)} |`,
    `| Total app JS | ${kb(b.allJs.gzip)} | ${kb(c.allJs.gzip)} | |`,
    `| JS chunks | ${b.chunks} | ${c.chunks} | |`, "",
  );
}
if (report.api) {
  const r = report.api.results;
  lines.push(`## API latency (${runs} runs, local)`, "", "| Request pattern | p50 | p95 |", "|---|---|---|");
  for (const [name, s] of Object.entries(r)) lines.push(`| ${name} | ${ms(s.p50)} | ${ms(s.p95)} |`);
  const old = r["hub: old flow"], cached = r["hub: new digest (cached)"];
  if (old && cached) lines.push("", `Hub p50: ${ms(old.p50)} -> ${ms(cached.p50)} (-${pct(old.p50, cached.p50)}).`);
  const ov0 = r["overview: old (3 requests)"], ov1 = r["overview: new (/stats)"];
  if (ov0 && ov1) lines.push(`Overview stats p50: ${ms(ov0.p50)} -> ${ms(ov1.p50)} (-${pct(ov0.p50, ov1.p50)}).`);
}
const md = lines.join("\n") + "\n";
writeFileSync(join(benchDir, `results-${Date.now()}.json`), JSON.stringify(report, null, 2));
writeFileSync(join(benchDir, "latest.md"), md);
console.log(`\n${md}Saved to .bench/latest.md`);
