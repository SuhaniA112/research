import type { ReadingLevel, Source, SummaryLevel } from "@/types";

/** Profile reading level → summary tier (casual maps to general). */
export function readingLevelToSummaryLevel(level: ReadingLevel): SummaryLevel {
  return level === "casual" ? "general" : level;
}

export function hasLeveledSummaries(source: Source): boolean {
  const s = source.summaries;
  return Boolean(s?.general?.trim() && s?.graduate?.trim() && s?.expert?.trim());
}

export function isPaperUuid(id: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    id,
  );
}

/** Pick the stored summary for a reading level, falling back to abstract. */
export function summaryForReadingLevel(
  source: Source,
  readingLevel: ReadingLevel,
): string {
  const level = readingLevelToSummaryLevel(readingLevel);
  const leveled = source.summaries?.[level]?.trim();
  if (leveled) return leveled;
  return source.description?.trim() ?? "";
}

export function summaryForLevel(
  source: Source,
  level: SummaryLevel,
): string {
  const leveled = source.summaries?.[level]?.trim();
  if (leveled) return leveled;
  return source.description?.trim() ?? "";
}
