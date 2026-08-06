#!/usr/bin/env python3
"""End-to-end check: search → save → ask → unsave.

Requires a running API (uvicorn on :8000), Postgres, and non-empty:
  VOYAGE_API_KEY
  OPENROUTER_API_KEY
in backend/.env (loaded by the API process).

Usage (from repo root, API already running):
  backend/.venv/bin/python scripts/e2e_save_ask.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / "backend" / ".env"
BASE = os.environ.get("E2E_API_BASE", "http://127.0.0.1:8000/api/v1")


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def request(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            payload: object = json.loads(raw) if raw else None
            return resp.status, payload
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {"detail": raw}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return err.code, payload


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    env = load_dotenv(ENV_PATH)
    voyage = env.get("VOYAGE_API_KEY", "").strip()
    openrouter = env.get("OPENROUTER_API_KEY", "").strip()
    if not voyage or not openrouter:
        fail(
            "VOYAGE_API_KEY and OPENROUTER_API_KEY must be set in backend/.env "
            "before running this E2E check."
        )

    print("1) Create project")
    status, project = request(
        "POST",
        "/projects",
        {"name": "E2E Save/Ask Probe", "description": "temporary e2e project"},
    )
    if status != 201 or not isinstance(project, dict):
        fail(f"create project → {status} {project}")
    project_id = project["id"]
    print(f"   project_id={project_id}")

    print("2) Discovery search")
    status, search = request(
        "POST",
        "/research/search",
        {"query": "accessibility voice user interfaces", "limit": 5},
    )
    if status != 200 or not isinstance(search, dict):
        fail(f"search → {status} {search}")
    results = search.get("results") or []
    if not results:
        fail("search returned no results (check Voyage key / discovery path)")
    paper = results[0]["paper"]
    paper_id = paper["id"]
    print(f"   paper_id={paper_id} title={paper.get('title', '')[:80]!r}")

    print("3) Save paper (triggers ingest)")
    status, saved = request(
        "POST",
        f"/projects/{project_id}/papers",
        {
            "paper": {
                "title": paper["title"],
                "abstract": paper.get("abstract"),
                "authors": paper.get("authors") or [],
                "year": paper.get("year"),
                "url": paper.get("url"),
                "pdf_url": paper.get("pdf_url"),
                "source": paper["source"],
                "external_id": paper["external_id"],
                "topics": paper.get("topics") or [],
            }
        },
    )
    if status not in (200, 201) or not isinstance(saved, dict):
        fail(f"save → {status} {saved}")
    saved_id = saved["paper"]["id"]
    print(f"   saved paper_id={saved_id} already_saved={saved.get('already_saved')}")

    print("4) GET /papers/:id")
    status, fetched = request("GET", f"/papers/{saved_id}")
    if status != 200 or not isinstance(fetched, dict):
        fail(f"get paper → {status} {fetched}")
    print(f"   ok title={fetched.get('title', '')[:80]!r}")

    print("5) Ask")
    status, ask = request(
        "POST",
        f"/projects/{project_id}/ask",
        {"question": "What is this paper about in one sentence?"},
    )
    if status != 200 or not isinstance(ask, dict):
        fail(f"ask → {status} {ask}")
    answer = (ask.get("answer") or "").strip()
    if not answer:
        fail(f"ask returned empty answer: {ask}")
    print(f"   answer={answer[:160]!r}")

    print("6) Unsave")
    status, _ = request("DELETE", f"/projects/{project_id}/papers/{saved_id}")
    if status != 204:
        fail(f"unsave → {status}")

    print("7) Delete project")
    status, _ = request("DELETE", f"/projects/{project_id}")
    if status != 204:
        fail(f"delete project → {status}")

    print("\nPASS: save → ingest → ask → unsave")


if __name__ == "__main__":
    main()
