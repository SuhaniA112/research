import { listSavedSources } from "@/api/sources";
import { env } from "@/config/env";
import { sourceBreakdown, sourceRecency } from "@/data/mockData";
import { colors } from "@/lib/theme";
import type { Source } from "@/types";

export interface SourceBreakdownItem {
  name: string;
  value: number | string;
  color: string;
}

export interface SourceRecencyItem {
  year: string;
  count: number;
}

export interface SourceRecencyStats {
  bars: SourceRecencyItem[];
  /** Cutoff year maximizing sources from this year onwards (via densest 3-year window). */
  sinceYear: number;
  sinceCount: number;
  total: number;
  /** Chart start year — used for color gradient. */
  startYear: number;
  /** Always the current calendar year for “last 3 years” coloring. */
  presentYear: number;
}

export interface SourceValidityStats {
  scoreLabel: string;
  statusLabel: string;
  metrics: [string, string][];
}

function yearOf(source: Source): number | null {
  const year = source.publishedYear;
  if (!year || year < 1900 || year > 2100) return null;
  return year;
}

/**
 * Build recency chart + “X since Year” from saved sources.
 *
 * sinceYear = start of the densest 3-year publication window
 * (the year after which / from which the most sources cluster),
 * sinceCount = sources with publishedYear >= sinceYear.
 */
export function buildSourceRecencyStats(sources: Source[]): SourceRecencyStats | null {
  const years = sources
    .map(yearOf)
    .filter((year): year is number => year != null)
    .sort((a, b) => a - b);

  if (years.length === 0) return null;

  const minYear = years[0]!;
  const maxYear = years[years.length - 1]!;
  const presentYear = new Date().getFullYear();
  // Anchor the chart on “present” so last-3-years coloring is correct
  const endYear = Math.max(maxYear, presentYear);
  const startYear = Math.min(minYear, Math.max(endYear - 6, minYear));

  const counts = new Map<number, number>();
  for (let y = startYear; y <= endYear; y++) counts.set(y, 0);
  for (const year of years) {
    if (year < startYear || year > endYear) continue;
    counts.set(year, (counts.get(year) ?? 0) + 1);
  }

  // Densest 3-year window → “since” cutoff (most sources clustered from this year)
  let sinceYear = Math.max(startYear, endYear - 2);
  let bestWindow = -1;
  for (let y = startYear; y <= endYear; y++) {
    let windowCount = 0;
    for (let w = y; w <= Math.min(y + 2, endYear); w++) {
      windowCount += counts.get(w) ?? 0;
    }
    if (windowCount >= bestWindow) {
      bestWindow = windowCount;
      sinceYear = y;
    }
  }

  const sinceCount = years.filter((year) => year >= sinceYear).length;

  const bars: SourceRecencyItem[] = [];
  for (let y = startYear; y <= endYear; y++) {
    bars.push({
      year: String(y),
      count: counts.get(y) ?? 0,
    });
  }

  return {
    bars,
    sinceYear,
    sinceCount,
    total: years.length,
    startYear,
    presentYear,
  };
}

export async function getSourceBreakdown(
  projectId: string,
): Promise<SourceBreakdownItem[]> {
  if (env.useMocks) {
    void projectId;
    return sourceBreakdown;
  }
  await listSavedSources(projectId).catch(() => []);
  return [
    { name: "Journals", value: "[X]", color: colors.fg.muted },
    { name: "Preprints", value: "[X]", color: colors.fg.secondary },
    { name: "Others", value: "[X]", color: colors.border },
  ];
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
    const sinceYear = 2021;
    const sinceCount = bars
      .filter((b) => Number(b.year) >= sinceYear)
      .reduce((sum, b) => sum + b.count, 0);
    return {
      bars,
      sinceYear,
      sinceCount,
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
