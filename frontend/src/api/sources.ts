/**
 * Backend:
 * GET    /api/v1/papers/:paperId
 * POST   /api/v1/papers/summarize  { paper: IndPaper }
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
import { hasLeveledSummaries, isPaperUuid } from "@/lib/summaries";
import type { Source, SummaryLevel } from "@/types";

/** OpenRouter summarization regularly exceeds the default 15s axios timeout. */
const SUMMARIZE_TIMEOUT_MS = 90_000;
const SAVE_TIMEOUT_MS = 60_000;
const MAX_CONCURRENT_SUMMARIES = 2;

const inflightSummaries = new Map<string, Promise<Source>>();
let activeSummaries = 0;
const summaryWaiters: Array<() => void> = [];

async function withSummaryLimit<T>(fn: () => Promise<T>): Promise<T> {
  if (activeSummaries >= MAX_CONCURRENT_SUMMARIES) {
    await new Promise<void>((resolve) => {
      summaryWaiters.push(resolve);
    });
  }
  activeSummaries += 1;
  try {
    return await fn();
  } finally {
    activeSummaries -= 1;
    summaryWaiters.shift()?.();
  }
}

export function getSourceSync(sourceId: string): Source | undefined {
  return getCachedSource(sourceId) ?? mockStore.sources.find((s) => s.id === sourceId);
}

export function listSourcesSync(): Source[] {
  return mockStore.sources;
}

export function sourcesMatch(a: Source, b: Pick<Source, "id" | "externalId">): boolean {
  if (a.id === b.id) return true;
  if (a.externalId && b.externalId && a.externalId === b.externalId) return true;
  if (a.externalId && a.externalId === b.id) return true;
  if (b.externalId && b.externalId === a.id) return true;
  return false;
}

export async function getSource(sourceId: string): Promise<Source | undefined> {
  const id = decodeURIComponent(sourceId);
  if (env.useMocks) {
    return mockStore.sources.find((s) => s.id === id);
  }
  const cached = getCachedSource(id) ?? getCachedSource(sourceId);
  // Unsaved discovery/legacy papers use non-UUID ids and are cache-only.
  if (!isPaperUuid(id)) {
    return cached;
  }
  // Always fetch UUIDs so lazy summary backfill can run on the backend.
  try {
    const { data } = await apiClient.get<BackendPaper>(`/api/v1/papers/${id}`, {
      timeout: SUMMARIZE_TIMEOUT_MS,
    });
    return mapBackendPaperToSource(data, {
      savedOn: cached?.savedOn,
      starred: cached?.starred,
    });
  } catch {
    return cached;
  }
}

/**
 * Ensure leveled summaries + key findings exist for any source (saved or not).
 * UUID papers: GET /papers/:id (lazy backfill). Others: POST /papers/summarize.
 */
export async function ensureSourceSummaries(source: Source): Promise<Source> {
  if (env.useMocks) {
    return source;
  }
  if (hasLeveledSummaries(source)) {
    return source;
  }

  const dedupeKey = source.externalId || source.id;
  const existing = inflightSummaries.get(dedupeKey);
  if (existing) return existing;

  const task = withSummaryLimit(async () => {
    try {
      if (isPaperUuid(source.id)) {
        const fetched = await getSource(source.id);
        if (fetched && hasLeveledSummaries(fetched)) {
          return {
            ...fetched,
            savedOn: source.savedOn ?? fetched.savedOn,
            starred: source.starred ?? fetched.starred,
          };
        }
      }

      const { data } = await apiClient.post<BackendPaper>(
        "/api/v1/papers/summarize",
        { paper: sourceToIndPaper(source) },
        { timeout: SUMMARIZE_TIMEOUT_MS },
      );
      return mapBackendPaperToSource(data, {
        savedOn: source.savedOn,
        starred: source.starred,
      });
    } catch {
      return source;
    } finally {
      inflightSummaries.delete(dedupeKey);
    }
  });

  inflightSummaries.set(dedupeKey, task);
  return task;
}

export async function listSavedSources(projectId: string): Promise<Source[]> {
  if (env.useMocks) {
    const ids = new Set(mockStore.projectSaves[projectId] ?? []);
    return mockStore.sources.filter((s) => ids.has(s.id));
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
  sourceHint?: Source,
): Promise<Source> {
  if (env.useMocks) {
    const source =
      sourceHint ??
      mockStore.sources.find((s) => s.id === sourceId) ??
      getSourceSync(sourceId);
    if (!source) {
      throw new Error(`Unknown source ${sourceId}`);
    }
    const bucket = mockStore.projectSaves[projectId] ?? [];
    if (!bucket.includes(source.id)) {
      mockStore.projectSaves[projectId] = [...bucket, source.id];
    }
    const savedOn =
      source.savedOn ??
      new Date().toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    mockStore.sources = mockStore.sources.map((s) =>
      s.id === source.id ? { ...s, savedOn } : s,
    );
    const project = mockStore.projects.find((p) => p.id === projectId);
    if (project) {
      project.sourceCount = mockStore.projectSaves[projectId]?.length ?? 0;
      project.updatedAt = new Date().toISOString();
    }
    return { ...source, savedOn };
  }

  const source =
    sourceHint ??
    getSourceSync(sourceId) ??
    (await getSource(sourceId));
  if (!source) {
    throw new Error(`Unknown source ${sourceId} — search or open it before saving`);
  }
  const { data } = await apiClient.post<{
    paper: BackendPaper;
    already_saved: boolean;
  }>(
    `/api/v1/projects/${projectId}/papers`,
    { paper: sourceToIndPaper(source) },
    { timeout: SAVE_TIMEOUT_MS },
  );
  return mapBackendPaperToSource(data.paper, {
    savedOn: new Date().toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }),
    starred: source.starred,
  });
}

export async function unsaveSource(
  projectId: string,
  sourceId: string,
): Promise<void> {
  if (env.useMocks) {
    const source = getSourceSync(sourceId);
    const matchId = source?.id ?? sourceId;
    mockStore.projectSaves[projectId] = (mockStore.projectSaves[projectId] ?? []).filter(
      (id) => id !== matchId,
    );
    const stillSavedElsewhere = Object.entries(mockStore.projectSaves).some(
      ([pid, ids]) => pid !== projectId && ids.includes(matchId),
    );
    if (!stillSavedElsewhere) {
      mockStore.sources = mockStore.sources.map((s) =>
        s.id === matchId ? { ...s, savedOn: undefined } : s,
      );
    }
    const project = mockStore.projects.find((p) => p.id === projectId);
    if (project) {
      project.sourceCount = mockStore.projectSaves[projectId]?.length ?? 0;
      project.updatedAt = new Date().toISOString();
    }
    return;
  }
  const id = decodeURIComponent(sourceId);
  const cached = getCachedSource(id) ?? getCachedSource(sourceId);
  const paperId = isPaperUuid(id) ? id : cached?.id;
  if (!paperId || !isPaperUuid(paperId)) {
    throw new Error(`Cannot unsave non-persisted source ${sourceId}`);
  }
  await apiClient.delete(`/api/v1/projects/${projectId}/papers/${paperId}`);
  if (cached) {
    cacheSource({ ...cached, savedOn: undefined });
  }
}

export async function getSummary(
  sourceId: string,
  level: SummaryLevel,
  sourceHint?: Source,
): Promise<string> {
  if (env.useMocks) {
    const fromStore = mockStore.summaryTexts[level]?.trim();
    if (fromStore) return fromStore;
    const source = mockStore.sources.find((s) => s.id === sourceId);
    return source?.summaries?.[level]?.trim() || source?.description?.trim() || "";
  }

  const hint = sourceHint ?? getSourceSync(sourceId);
  const source = hint
    ? await ensureSourceSummaries(hint)
    : await getSource(sourceId);
  if (!source) return "";
  return (
    source.summaries?.[level]?.trim() ||
    source.description?.trim() ||
    ""
  );
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
