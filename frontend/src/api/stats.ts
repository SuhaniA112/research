import { listSavedSources } from "@/api/sources";
import { env } from "@/config/env";
import { apiClient } from "@/lib/axios";
import { sourceRecency } from "@/data/mockData";
import { colors } from "@/lib/theme";
import type { Source } from "@/types";

export interface SourceBreakdownItem {
  name: string;
  value: number;
  color: string;
}

export interface SourceRecencyItem {
  year: string;
  count: number;
}

export interface SourceRecencyStats {
  bars: SourceRecencyItem[];
  /** Earliest published year among saved sources. */
  earliestYear: number;
  total: number;
  /** Chart start year — used for color gradient. */
  startYear: number;
  /** Chart end year (max of latest source year and current year). */
  presentYear: number;
}

export interface SourceValidityMetric {
  label: string;
  /** Display value, e.g. "76%"; "—" when no provider reported the field. */
  value: string;
  /** e.g. "12 of 16 sources with data". */
  hint: string;
}

export interface SourceValidityStats {
  /** 0–100, or null when there is nothing to score yet. */
  score: number | null;
  scoreLabel: string;
  statusLabel: string;
  metrics: SourceValidityMetric[];
}

interface BackendSourceValidity {
  score: number | null;
  status: string;
  total_sources: number;
  metrics: {
    key: string;
    label: string;
    percent: number | null;
    count: number;
    known: number;
  }[];
}

const VALIDITY_LABELS = ["Cross-cited", "Peer-reviewed", "Open access", "Multi-author"];

function placeholderValidity(statusLabel: string): SourceValidityStats {
  return {
    score: null,
    scoreLabel: "— / 100",
    statusLabel,
    metrics: VALIDITY_LABELS.map((label) => ({ label, value: "—", hint: "" })),
  };
}

export function mapSourceValidity(data: BackendSourceValidity): SourceValidityStats {
  return {
    score: data.score,
    scoreLabel: data.score == null ? "— / 100" : `${data.score} / 100`,
    statusLabel: data.status,
    metrics: data.metrics.map((m) => ({
      label: m.label,
      value: m.percent == null ? "—" : `${m.percent}%`,
      hint:
        m.known === 0
          ? "Not reported by these sources' providers yet"
          : `${m.count} of ${m.known} source${m.known === 1 ? "" : "s"} with data`,
    })),
  };
}

const PROVIDER_LABELS: Record<string, string> = {
  arxiv: "arXiv",
  openalex: "OpenAlex",
  semantic_scholar: "Semantic Scholar",
  dblp: "DBLP",
};

const BREAKDOWN_COLORS = [
  colors.fg.secondary, // darkest — highest share
  colors.fg.muted,
  colors.border, // lightest — lowest share
] as const;

function formatSourceType(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "Unknown";
  return PROVIDER_LABELS[trimmed.toLowerCase()] ?? trimmed;
}

/**
 * Top 2 source providers/venues by count; remaining types roll into Other.
 * Values are percentages of saved sources. Darkest color = highest share.
 */
function buildSourceBreakdown(sources: Source[]): SourceBreakdownItem[] {
  if (sources.length === 0) return [];

  const counts = new Map<string, number>();
  for (const source of sources) {
    const label = formatSourceType(source.source);
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }

  const ranked = [...counts.entries()].sort(
    (a, b) => b[1] - a[1] || a[0].localeCompare(b[0]),
  );
  const top = ranked.slice(0, 2);
  const otherCount = ranked.slice(2).reduce((sum, [, n]) => sum + n, 0);

  const groups: { name: string; count: number }[] = top.map(([name, count]) => ({
    name,
    count,
  }));
  if (otherCount > 0) {
    groups.push({ name: "Other", count: otherCount });
  }

  // Color by amount (darkest = highest), independent of top-2 vs Other order
  groups.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));

  const total = sources.length;
  return groups.map((group, index) => ({
    name: group.name,
    value: Math.round((group.count / total) * 100),
    color: BREAKDOWN_COLORS[index] ?? colors.border,
  }));
}

function yearOf(source: Source): number | null {
  const year = source.publishedYear;
  if (!year || year < 1900 || year > 2100) return null;
  return year;
}

/**
 * Build recency chart from saved sources.
 * Subtitle uses total sources counted from the earliest publication year.
 */
function buildSourceRecencyStats(sources: Source[]): SourceRecencyStats | null {
  const years = sources
    .map(yearOf)
    .filter((year): year is number => year != null)
    .sort((a, b) => a - b);

  if (years.length === 0) return null;

  const earliestYear = years[0]!;
  const maxYear = years[years.length - 1]!;
  const presentYear = new Date().getFullYear();
  const endYear = Math.max(maxYear, presentYear);
  const startYear = Math.min(earliestYear, Math.max(endYear - 6, earliestYear));

  const counts = new Map<number, number>();
  for (let y = startYear; y <= endYear; y++) counts.set(y, 0);
  for (const year of years) {
    if (year < startYear || year > endYear) continue;
    counts.set(year, (counts.get(year) ?? 0) + 1);
  }

  const bars: SourceRecencyItem[] = [];
  for (let y = startYear; y <= endYear; y++) {
    bars.push({
      year: String(y),
      count: counts.get(y) ?? 0,
    });
  }

  return {
    bars,
    earliestYear,
    total: years.length,
    startYear,
    presentYear,
  };
}

interface BackendProjectStats {
  total_sources: number;
  breakdown: { name: string; count: number; percent: number }[];
  recency: {
    bars: { year: number; count: number }[];
    earliest_year: number;
    total: number;
    start_year: number;
    present_year: number;
  } | null;
  validity: BackendSourceValidity;
  topics: { topic: string; count: number }[];
}

// Only dedupes the cards' simultaneous requests; saves show up on the next visit.
const STATS_TTL_MS = 5_000;
const statsRequests = new Map<string, { at: number; promise: Promise<BackendProjectStats> }>();

/** GET /projects/:id/stats once, shared by the three overview cards. */
function getProjectStats(projectId: string): Promise<BackendProjectStats> {
  const hit = statsRequests.get(projectId);
  if (hit && Date.now() - hit.at < STATS_TTL_MS) return hit.promise;
  const promise = apiClient
    .get<BackendProjectStats>(`/api/v1/projects/${projectId}/stats`)
    .then((r) => r.data);
  statsRequests.set(projectId, { at: Date.now(), promise });
  promise.catch(() => statsRequests.delete(projectId));
  return promise;
}

export function invalidateProjectStats(projectId: string): void {
  statsRequests.delete(projectId);
}

export async function getSourceBreakdown(
  projectId: string,
): Promise<SourceBreakdownItem[]> {
  if (!env.useMocks) {
    try {
      const stats = await getProjectStats(projectId);
      return stats.breakdown.map((item, index) => ({
        name: item.name,
        value: item.percent,
        color: BREAKDOWN_COLORS[index] ?? colors.border,
      }));
    } catch {
      // Fall through to the client-side calculation.
    }
  }
  const saved = await listSavedSources(projectId).catch(() => []);
  return buildSourceBreakdown(saved);
}

export async function getSourceRecency(
  projectId: string,
): Promise<SourceRecencyStats | null> {
  if (env.useMocks) {
    void projectId;
    // Prefer computing from mock saved sources; fall back to static series
    const saved = await listSavedSources(projectId);
    const fromSaved = buildSourceRecencyStats(saved);
    if (fromSaved) return fromSaved;

    const presentYear = new Date().getFullYear();
    const bars: SourceRecencyItem[] = sourceRecency.map((item) => ({
      year: item.year,
      count: item.count,
    }));
    const startYear = Number(bars[0]?.year ?? presentYear - 6);
    const earliestYear = startYear;
    return {
      bars,
      earliestYear,
      total: bars.reduce((sum, b) => sum + b.count, 0),
      startYear,
      presentYear,
    };
  }

  try {
    const { recency } = await getProjectStats(projectId);
    if (!recency) return null;
    return {
      bars: recency.bars.map((b) => ({ year: String(b.year), count: b.count })),
      earliestYear: recency.earliest_year,
      total: recency.total,
      startYear: recency.start_year,
      presentYear: recency.present_year,
    };
  } catch {
    const saved = await listSavedSources(projectId);
    return buildSourceRecencyStats(saved);
  }
}

export async function getSourceValidity(
  projectId: string,
): Promise<SourceValidityStats> {
  if (env.useMocks) {
    return {
      score: 82,
      scoreLabel: "82 / 100",
      statusLabel: "HIGHLY CONNECTED",
      metrics: [
        { label: "Cross-cited", value: "76%", hint: "" },
        { label: "Peer-reviewed", value: "68%", hint: "" },
        { label: "Open access", value: "54%", hint: "" },
        { label: "Multi-author", value: "89%", hint: "" },
      ],
    };
  }
  try {
    return mapSourceValidity((await getProjectStats(projectId)).validity);
  } catch {
    return placeholderValidity("UNAVAILABLE");
  }
}
