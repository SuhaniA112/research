"""Generate leveled paper summaries and key findings via OpenRouter."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.services.generation.openrouter_client import OpenRouterClient, OpenRouterError

logger = logging.getLogger(__name__)

_MAX_SOURCE_CHARS = 14_000
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

_SYSTEM_PROMPT = """You summarize academic papers for a research app.
Return ONLY valid JSON with this exact shape:
{
  "general": "plain-language summary for a non-expert",
  "graduate": "technical but accessible summary for a graduate student",
  "expert": "dense expert summary emphasizing methods, results, and limitations",
  "key_findings": [
    {"text": "concrete finding", "section": "Results"}
  ]
}
Rules:
- general / graduate / expert must each be 2–4 sentences and meaningfully different in reading level.
- key_findings: 3–5 items; section is a best-effort paper section label (e.g. Results, Discussion, Methods).
- Do not invent citations or DOIs. If the source text is thin, still produce best-effort summaries from what is given.
"""


@dataclass
class PaperSummaryResult:
    general: str
    graduate: str
    expert: str
    key_findings: list[dict[str, str]]


class PaperSummarizer:
    def __init__(self, openrouter_client: OpenRouterClient) -> None:
        self.openrouter_client = openrouter_client

    async def summarize(
        self, *, title: str, source_text: str
    ) -> PaperSummaryResult | None:
        if not self.openrouter_client.api_key:
            return None

        body = (source_text or "").strip() or title
        if len(body) > _MAX_SOURCE_CHARS:
            body = body[:_MAX_SOURCE_CHARS] + "\n\n[truncated]"

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Title: {title}\n\nSource text:\n{body}",
            },
        ]

        try:
            raw = await self.openrouter_client.chat_completion(messages)
        except (OpenRouterError, Exception) as exc:
            logger.warning("Paper summarization failed: %s", exc)
            return None

        return self._parse(raw)

    def _parse(self, raw: str) -> PaperSummaryResult | None:
        text = raw.strip()
        match = _JSON_BLOCK.search(text)
        if match:
            text = match.group(0)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Paper summarizer returned non-JSON content")
            return None

        general = str(data.get("general") or "").strip()
        graduate = str(data.get("graduate") or "").strip()
        expert = str(data.get("expert") or "").strip()
        if not (general and graduate and expert):
            logger.warning("Paper summarizer missing one or more summary levels")
            return None

        findings_raw = data.get("key_findings") or []
        findings: list[dict[str, str]] = []
        if isinstance(findings_raw, list):
            for item in findings_raw:
                if not isinstance(item, dict):
                    continue
                finding_text = str(item.get("text") or "").strip()
                if not finding_text:
                    continue
                findings.append(
                    {
                        "text": finding_text,
                        "section": str(item.get("section") or "").strip() or "Paper",
                    }
                )

        return PaperSummaryResult(
            general=general,
            graduate=graduate,
            expert=expert,
            key_findings=findings,
        )
