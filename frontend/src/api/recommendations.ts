/**
 * Backend recommender endpoints:
 * GET  /api/v1/digest?limit&offset&refresh
 * GET  /api/v1/papers/:id/related
 * POST /api/v1/projects/:id/similarity
 */
import { cacheSources, mapBackendPaperToSource, type BackendPaper } from "@/api/mappers";
import { apiClient } from "@/lib/axios";
import { getStoredUserId } from "@/lib/userContext";
import type { Source } from "@/types";

interface BackendRecommended {
  paper: BackendPaper;
  relevance: number | null;
  similarity: number | null;
  matched_interest: string | null;
}

interface BackendDigest {
  interests: string[];
  items: BackendRecommended[];
  total: number;
  offset: number;
  has_more: boolean;
  sparse: boolean;
  method: "embedding" | "lexical" | "recent" | "none";
  generated_at: string;
}

export interface DigestPage {
  interests: string[];
  items: Source[];
  total: number;
  hasMore: boolean;
  sparse: boolean;
  // "live": filled client-side from live searches when nothing stored matched.
  method: BackendDigest["method"] | "live";
  generatedAt: string;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const isPaperUuid = (id: string) => UUID_RE.test(id);

function toSource(item: BackendRecommended): Source {
  return mapBackendPaperToSource(item.paper, {
    relevance: item.relevance,
    similarity: item.similarity,
    relevantTo: item.matched_interest ? [item.matched_interest] : item.paper.topics ?? [],
  });
}

export async function fetchDigestPage(
  options: { limit?: number; offset?: number; refresh?: boolean } = {},
): Promise<DigestPage> {
  const { data } = await apiClient.get<BackendDigest>("/api/v1/digest", {
    params: { limit: options.limit ?? 5, offset: options.offset ?? 0, refresh: options.refresh ?? false },
    // The first digest after a cold start embeds interests; allow extra time.
    timeout: 30_000,
  });
  return {
    interests: data.interests,
    items: cacheSources(data.items.map(toSource)),
    total: data.total,
    hasMore: data.has_more,
    sparse: data.sparse,
    method: data.method,
    generatedAt: data.generated_at,
  };
}

/* Last digest page per user in localStorage, so the hub paints instantly. */
const DIGEST_SNAPSHOT_KEY = "papersearcher_digest_snapshot_v1";

export function readDigestSnapshot(): DigestPage | null {
  try {
    const raw = localStorage.getItem(DIGEST_SNAPSHOT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { userId: string | null; page: DigestPage };
    if (parsed.userId !== getStoredUserId()) return null;
    cacheSources(parsed.page.items);
    return parsed.page;
  } catch {
    return null;
  }
}

export function writeDigestSnapshot(page: DigestPage): void {
  try {
    localStorage.setItem(
      DIGEST_SNAPSHOT_KEY,
      JSON.stringify({ userId: getStoredUserId(), page }),
    );
  } catch {
    // Storage full or blocked: the hub just loads without a snapshot.
  }
}

export async function fetchRelatedPapers(paperId: string, limit = 3): Promise<Source[]> {
  if (!isPaperUuid(paperId)) return [];
  const { data } = await apiClient.get<BackendRecommended[]>(
    `/api/v1/papers/${paperId}/related`,
    { params: { limit } },
  );
  return cacheSources(data.map(toSource));
}

/** Stored papers that fit a project (no live search); used for an empty search box. */
export async function fetchProjectSuggestions(projectId: string, limit = 12): Promise<Source[]> {
  if (!isPaperUuid(projectId)) return [];
  const { data } = await apiClient.get<BackendRecommended[]>(
    `/api/v1/projects/${projectId}/suggestions`,
    { params: { limit } },
  );
  return cacheSources(data.map(toSource));
}

interface BackendPaperScore {
  relevance: number | null;
  similarity: number | null;
  search_match: number | null;
  score: number | null;
}

type ProjectScore = Pick<Source, "relevance" | "similarity">;
const projectScoreCache = new Map<string, ProjectScore>();
const scoreKey = (projectId: string, paperId: string) => `${projectId}:${paperId}`;

/**
 * Show only project-relative scores: last known values from the cache, else
 * none. Keeps the numbers identical across hub, search, saved and detail pages.
 * The previous search relevance is kept in matchScore so ordering doesn't jump.
 */
export function applyCachedProjectScores(projectId: string | undefined, sources: Source[]): Source[] {
  if (!projectId || !isPaperUuid(projectId)) return sources;
  return sources.map((s) => {
    const cached = projectScoreCache.get(scoreKey(projectId, s.id));
    return {
      ...s,
      matchScore: s.matchScore ?? (s.relevance != null ? s.relevance / 100 : null),
      relevance: cached?.relevance ?? null,
      similarity: cached?.similarity ?? null,
    };
  });
}

/**
 * Score sources against a project: relevance = fit to the project,
 * similarity = closeness to its saved papers, matchScore = ranking blend
 * (including the search text when given). Missing scores keep prior values.
 */
export async function scoreForProject(
  projectId: string,
  sources: Source[],
  query?: string,
): Promise<Source[]> {
  if (!isPaperUuid(projectId)) return sources;
  const ids = sources.map((s) => s.id).filter(isPaperUuid).slice(0, 100);
  if (ids.length === 0) return sources;
  const { data } = await apiClient.post<{ scores: Record<string, BackendPaperScore> }>(
    `/api/v1/projects/${projectId}/scores`,
    { paper_ids: ids, query: query?.trim() || null },
  );
  return cacheSources(
    sources.map((s) => {
      const sc = data.scores[s.id];
      if (!sc) return s;
      const key = scoreKey(projectId, s.id);
      const prev = projectScoreCache.get(key);
      const next = {
        relevance: sc.relevance ?? prev?.relevance ?? null,
        similarity: sc.similarity ?? prev?.similarity ?? null,
      };
      projectScoreCache.set(key, next);
      return { ...s, ...next, matchScore: sc.score ?? s.matchScore ?? null };
    }),
  );
}
