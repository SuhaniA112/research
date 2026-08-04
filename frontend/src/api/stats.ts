import { listSavedSources } from "@/api/sources";
import { env } from "@/config/env";
import { sourceBreakdown, sourceRecency } from "@/data/mockData";
import { colors } from "@/lib/theme";

export interface SourceBreakdownItem {
  name: string;
  value: number | string;
  color: string;
}

export interface SourceRecencyItem {
  year: string;
  count: number | string;
}

export interface SourceValidityStats {
  scoreLabel: string;
  statusLabel: string;
  metrics: [string, string][];
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
): Promise<SourceRecencyItem[]> {
  if (env.useMocks) {
    void projectId;
    return sourceRecency;
  }
  await listSavedSources(projectId).catch(() => []);
  return [{ year: "—", count: "[X]" }];
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
