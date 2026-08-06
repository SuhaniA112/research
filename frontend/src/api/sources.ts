/**
 * Backend:
 * GET    /api/v1/papers/:paperId
 * GET    /api/v1/projects/:projectId/papers
 * POST   /api/v1/projects/:projectId/papers  { paper: IndPaper }
 * DELETE /api/v1/projects/:projectId/papers/:paperId
 */
import {
  cacheSource,
  getCachedSource,
  mapBackendPaperToSource,
  sourceToIndPaper,
  type BackendPaper,
} from "@/api/mappers";
import { mockStore } from "@/api/mocks/store";
import { env } from "@/config/env";
import { apiClient } from "@/lib/axios";
import type { Source, SummaryLevel } from "@/types";

export function getSourceSync(sourceId: string): Source | undefined {
  return getCachedSource(sourceId) ?? mockStore.sources.find((s) => s.id === sourceId);
}

export function listSourcesSync(): Source[] {
  return mockStore.sources;
}

export async function getSource(sourceId: string): Promise<Source | undefined> {
  if (env.useMocks) {
    return mockStore.sources.find((s) => s.id === sourceId);
  }
  const cached = getCachedSource(sourceId);
  if (cached) return cached;
  try {
    const { data } = await apiClient.get<BackendPaper>(`/api/v1/papers/${sourceId}`);
    return mapBackendPaperToSource(data);
  } catch {
    return undefined;
  }
}

export async function listSavedSources(projectId: string): Promise<Source[]> {
  if (env.useMocks) {
    void projectId;
    return mockStore.sources.filter((s) => Boolean(s.savedOn));
  }
  const { data } = await apiClient.get<BackendPaper[]>(
    `/api/v1/projects/${projectId}/papers`,
  );
  const today = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return data.map((paper) =>
    mapBackendPaperToSource(paper, { savedOn: today }),
  );
}

export async function saveSource(
  projectId: string,
  sourceId: string,
): Promise<void> {
  if (env.useMocks) {
    mockStore.sources = mockStore.sources.map((s) =>
      s.id === sourceId
        ? {
            ...s,
            savedOn:
              s.savedOn ??
              new Date().toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              }),
          }
        : s,
    );
    const project = mockStore.projects.find((p) => p.id === projectId);
    if (project) {
      project.sourceCount += 1;
      project.updatedDaysAgo = 0;
    }
    return;
  }

  const source = getSourceSync(sourceId);
  if (!source) {
    throw new Error(`Unknown source ${sourceId} — search or open it before saving`);
  }
  const { data } = await apiClient.post<{
    paper: BackendPaper;
    already_saved: boolean;
  }>(`/api/v1/projects/${projectId}/papers`, {
    paper: sourceToIndPaper(source),
  });
  mapBackendPaperToSource(data.paper, {
    savedOn: new Date().toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }),
  });
}

export async function unsaveSource(
  projectId: string,
  sourceId: string,
): Promise<void> {
  if (env.useMocks) {
    mockStore.sources = mockStore.sources.map((s) =>
      s.id === sourceId ? { ...s, savedOn: undefined } : s,
    );
    const project = mockStore.projects.find((p) => p.id === projectId);
    if (project && project.sourceCount > 0) {
      project.sourceCount -= 1;
      project.updatedDaysAgo = 0;
    }
    return;
  }
  await apiClient.delete(`/api/v1/projects/${projectId}/papers/${sourceId}`);
  const cached = getCachedSource(sourceId);
  if (cached) {
    cacheSource({ ...cached, savedOn: undefined });
  }
}

export async function getSummary(
  sourceId: string,
  level: SummaryLevel,
): Promise<string> {
  // No leveled summary API yet — cards and source page share source.description.
  // `level` reserved for when General/Graduate/Expert summaries exist.
  void level;
  const source = env.useMocks
    ? mockStore.sources.find((s) => s.id === sourceId)
    : (getCachedSource(sourceId) ?? (await getSource(sourceId)));
  return source?.description?.trim() ?? "";
}

export async function listRelatedSources(
  sourceId: string,
  limit = 3,
): Promise<Source[]> {
  if (env.useMocks) {
    return mockStore.sources.filter((s) => s.id !== sourceId).slice(0, limit);
  }
  void sourceId;
  void limit;
  return [];
}

export async function listCitingSources(
  sourceId: string,
  limit = 3,
): Promise<Source[]> {
  if (env.useMocks) {
    return mockStore.sources
      .filter((s) => s.id !== sourceId)
      .slice(1, 1 + limit);
  }
  void sourceId;
  void limit;
  return [];
}
