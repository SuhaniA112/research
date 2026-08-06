import { listSavedSources } from "@/api/sources";
import { env } from "@/config/env";
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

export interface SourceValidityStats {
  scoreLabel: string;
  statusLabel: string;
  metrics: [string, string][];
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

export async function getSourceBreakdown(
  projectId: string,
): Promise<SourceBreakdownItem[]> {
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

  const saved = await listSavedSources(projectId);
  return buildSourceRecencyStats(saved);
}

export async function getSourceValidity(
  projectId: string,
): Promise<SourceValidityStats> {
  void projectId;
  if (env.useMocks) {
    return {
      scoreLabel: "82 / 100",
      statusLabel: "HIGHLY CONNECTED",
      metrics: [
        ["Cross-cited", "76%"],
        ["Peer-reviewed", "68%"],
        ["Open access", "54%"],
        ["Multi-author", "89%"],
      ],
    };
  }
  return {
    scoreLabel: "[X] / 100",
    statusLabel: "PENDING METRICS",
    metrics: [
      ["Cross-cited", "[X]%"],
      ["Peer-reviewed", "[X]%"],
      ["Open access", "[X]%"],
      ["Multi-author", "[X]%"],
    ],
  };
}
