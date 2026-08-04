import { getProject } from "@/api/projects";
import { listSavedSources } from "@/api/sources";
import { mockStore } from "@/api/mocks/store";
import { env } from "@/config/env";
import { buildMindMapFromProject } from "@/lib/mindMap";
import type { MindMapEdge, MindMapNode } from "@/types";

export interface MindMapData {
  nodes: MindMapNode[];
  edges: MindMapEdge[];
}

export async function getMindMap(projectId: string): Promise<MindMapData> {
  if (env.useMocks) {
    void projectId;
    return {
      nodes: mockStore.mindMapNodes,
      edges: mockStore.mindMapEdges,
    };
  }

  const [project, sources] = await Promise.all([
    getProject(projectId),
    listSavedSources(projectId),
  ]);

  if (!project) {
    return { nodes: [], edges: [] };
  }

  // No mind-map backend yet — derive a map from project topics + saved papers
  return buildMindMapFromProject(project, sources);
}
