import {
  currentUser,
  mindMapEdges,
  mindMapNodes,
  projects,
  recentProjectSearches,
  recentSearches,
  sources,
  summaryTexts,
} from "@/data/mockData";
import type { MindMapEdge, MindMapNode, Project, Source, UserProfile } from "@/types";

export const mockStore = {
  projects: structuredClone(projects) as Project[],
  sources: structuredClone(sources) as Source[],
  /** projectId → source ids saved into that project (supports multi-project saves). */
  projectSaves: {} as Record<string, string[]>,
  profile: structuredClone(currentUser) as UserProfile,
  recentSearches: structuredClone(recentSearches) as string[],
  recentProjectSearches: structuredClone(recentProjectSearches) as Record<
    string,
    string[]
  >,
  /** projectId → recent search result papers (for View Next). */
  projectSearchResults: {} as Record<string, Source[]>,
  mindMapNodes: structuredClone(mindMapNodes) as MindMapNode[],
  mindMapEdges: structuredClone(mindMapEdges) as MindMapEdge[],
  summaryTexts: { ...summaryTexts },
};

// Seed mock saves from sources that already have savedOn.
for (const source of mockStore.sources) {
  if (!source.savedOn) continue;
  const projectId = mockStore.projects[0]?.id;
  if (!projectId) continue;
  const bucket = mockStore.projectSaves[projectId] ?? [];
  if (!bucket.includes(source.id)) {
    mockStore.projectSaves[projectId] = [...bucket, source.id];
  }
}
