/**
 * Real mode prefers database-first discovery:
 * POST /api/v1/research/search
 *
 * Falls back to legacy live providers when discovery fails
 * (e.g. missing VOYAGE_API_KEY):
 * GET /api/v1/research/papers
 */
import { mapBackendPaperToSource, type BackendPaper } from "@/api/mappers";
import { mockStore } from "@/api/mocks/store";
import { env } from "@/config/env";
import { searchResearch } from "@/features/research/api/searchResearch";
import { apiClient } from "@/lib/axios";
import type { Source } from "@/types";
import {
  useQuery,
  useQueryClient,
  type QueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { useCallback } from "react";

export const searchHistoryQueryKey = ["search-history"] as const;

export function invalidateSearchHistory(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: searchHistoryQueryKey });
}

interface IndPaper {
  title: string;
  abstract?: string | null;
  authors?: string[];
  year?: number | null;
  url?: string | null;
  pdf_url?: string | null;
  source: string;
  external_id?: string | null;
  topics?: string[];
}

interface LegacySearchResponse {
  interests: string[];
  total_results: number;
  papers: IndPaper[];
}

function indPaperToBackendPaper(paper: IndPaper, index: number): BackendPaper {
  const externalId =
    paper.external_id?.trim() ||
    `${paper.source}:${paper.title}`.slice(0, 200) ||
    `legacy-${index}`;
  return {
    id: externalId,
    source: paper.source,
    external_id: externalId,
    title: paper.title,
    abstract: paper.abstract,
    authors: paper.authors,
    year: paper.year,
    url: paper.url,
    pdf_url: paper.pdf_url,
    topics: paper.topics,
  };
}

async function searchLegacyPapers(query: string): Promise<Source[]> {
  // Legacy fans out to 4 providers × 3 interests with rate-limit sleeps (~20–60s).
  const { data } = await apiClient.get<LegacySearchResponse>(
    "/api/v1/research/papers",
    { timeout: 90_000 },
  );
  const mapped = data.papers.map((paper, index) =>
    mapBackendPaperToSource(indPaperToBackendPaper(paper, index)),
  );
  const q = query.trim().toLowerCase();
  if (!q) return mapped;
  return mapped.filter(
    (s) =>
      s.title.toLowerCase().includes(q) ||
      s.description.toLowerCase().includes(q) ||
      s.topics.some((t) => t.toLowerCase().includes(q)) ||
      s.authors.some((a) => a.toLowerCase().includes(q)),
  );
}

export async function searchSources(query = ""): Promise<Source[]> {
  if (env.useMocks) {
    const q = query.trim().toLowerCase();
    if (!q) return mockStore.sources;
    return mockStore.sources.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.topics.some((t) => t.toLowerCase().includes(q)) ||
        s.authors.some((a) => a.toLowerCase().includes(q)),
    );
  }

  const q = query.trim() || "research";

  try {
    const response = await searchResearch({
      query: q,
      limit: 20,
    });
    return response.results.map((item) => {
      const paper = item.paper;
      const similarity =
        item.similarity_score == null
          ? null
          : Math.round(Math.min(1, Math.max(0, item.similarity_score)) * 100);
      return mapBackendPaperToSource(paper, {
        similarity,
        relevance: similarity,
      });
    });
  } catch {
    // Discovery needs Voyage; legacy multi-provider search still works without it.
    return searchLegacyPapers(q);
  }
}

export async function recordSearch(projectId: string, query: string): Promise<void> {
  const q = query.trim();
  if (!q) return;

  const list = mockStore.recentProjectSearches[projectId] ?? [];
  mockStore.recentProjectSearches[projectId] = [
    q,
    ...list.filter((item) => item !== q),
  ].slice(0, 10);
  mockStore.recentSearches = [
    q,
    ...mockStore.recentSearches.filter((item) => item !== q),
  ].slice(0, 20);
  persistSearchHistory();
}

const SEARCH_HISTORY_KEY = "papersearcher_search_history";

function persistSearchHistory(): void {
  localStorage.setItem(
    SEARCH_HISTORY_KEY,
    JSON.stringify({
      recentSearches: mockStore.recentSearches,
      recentProjectSearches: mockStore.recentProjectSearches,
    }),
  );
}

function hydrateSearchHistory(): void {
  try {
    const raw = localStorage.getItem(SEARCH_HISTORY_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as {
      recentSearches?: string[];
      recentProjectSearches?: Record<string, string[]>;
    };
    if (Array.isArray(parsed.recentSearches)) {
      mockStore.recentSearches = parsed.recentSearches;
    }
    if (parsed.recentProjectSearches && typeof parsed.recentProjectSearches === "object") {
      mockStore.recentProjectSearches = parsed.recentProjectSearches;
    }
  } catch {
    // ignore corrupt local storage
  }
}

hydrateSearchHistory();

export async function listRecentSearches(): Promise<string[]> {
  hydrateSearchHistory();
  return [...mockStore.recentSearches];
}

export async function getRecentProjectSearches(
  projectId: string,
): Promise<string[]> {
  hydrateSearchHistory();
  return [...(mockStore.recentProjectSearches[projectId] ?? [])];
}

export async function getAllProjectSearches(): Promise<Record<string, string[]>> {
  hydrateSearchHistory();
  return Object.fromEntries(
    Object.entries(mockStore.recentProjectSearches).map(([id, searches]) => [
      id,
      [...searches],
    ]),
  );
}

export function useProjectSearchHistory(): UseQueryResult<
  Record<string, string[]>,
  Error
> {
  return useQuery({
    queryKey: searchHistoryQueryKey,
    queryFn: getAllProjectSearches,
  });
}

export function useInvalidateSearchHistory(): () => void {
  const queryClient = useQueryClient();
  return useCallback(() => invalidateSearchHistory(queryClient), [queryClient]);
}

export async function deleteRecentSearch(query: string): Promise<void> {
  hydrateSearchHistory();
  mockStore.recentSearches = mockStore.recentSearches.filter((item) => item !== query);
  for (const projectId of Object.keys(mockStore.recentProjectSearches)) {
    mockStore.recentProjectSearches[projectId] = (
      mockStore.recentProjectSearches[projectId] ?? []
    ).filter((item) => item !== query);
  }
  persistSearchHistory();
}

export async function deleteProjectSearch(
  projectId: string,
  query: string,
): Promise<void> {
  hydrateSearchHistory();
  mockStore.recentProjectSearches[projectId] = (
    mockStore.recentProjectSearches[projectId] ?? []
  ).filter((item) => item !== query);
  // Keep global history unless this query only existed for that project
  const stillUsed = Object.values(mockStore.recentProjectSearches).some((list) =>
    list.includes(query),
  );
  if (!stillUsed) {
    mockStore.recentSearches = mockStore.recentSearches.filter((item) => item !== query);
  }
  persistSearchHistory();
}

export async function clearRecentSearches(): Promise<void> {
  mockStore.recentSearches = [];
  mockStore.recentProjectSearches = {};
  persistSearchHistory();
}
