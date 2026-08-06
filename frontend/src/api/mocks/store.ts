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
  profile: structuredClone(currentUser) as UserProfile,
  recentSearches: structuredClone(recentSearches) as string[],
  recentProjectSearches: structuredClone(recentProjectSearches) as Record<
    string,
    string[]
  >,
  mindMapNodes: structuredClone(mindMapNodes) as MindMapNode[],
  mindMapEdges: structuredClone(mindMapEdges) as MindMapEdge[],
  summaryTexts: { ...summaryTexts },
};

export function resetMockStore(): void {
  mockStore.projects = structuredClone(projects) as Project[];
  mockStore.sources = structuredClone(sources) as Source[];
  mockStore.profile = structuredClone(currentUser) as UserProfile;
  mockStore.recentSearches = structuredClone(recentSearches) as string[];
  mockStore.recentProjectSearches = structuredClone(
    recentProjectSearches,
  ) as Record<string, string[]>;
  mockStore.mindMapNodes = structuredClone(mindMapNodes) as MindMapNode[];
  mockStore.mindMapEdges = structuredClone(mindMapEdges) as MindMapEdge[];
  mockStore.summaryTexts = { ...summaryTexts };
}
