import { colors } from "@/lib/theme";
import type { MindMapEdge, MindMapNode, Source } from "@/types";

const ROOT_ID = "center";

export function buildDepthMap(
  edges: MindMapEdge[],
  rootId = ROOT_ID,
): Map<string, number> {
  const depths = new Map<string, number>([[rootId, 0]]);
  const queue = [rootId];

  while (queue.length > 0) {
    const id = queue.shift()!;
    const depth = depths.get(id)!;

    for (const edge of edges) {
      if (edge.from === id && !depths.has(edge.to)) {
        depths.set(edge.to, depth + 1);
        queue.push(edge.to);
      }
    }
  }

  return depths;
}

export function getChildNodes(
  nodeId: string,
  edges: MindMapEdge[],
  nodes: MindMapNode[],
): MindMapNode[] {
  const childIds = edges.filter((e) => e.from === nodeId).map((e) => e.to);
  return childIds
    .map((id) => nodes.find((n) => n.id === id))
    .filter((n): n is MindMapNode => n !== undefined);
}

export function getParentNode(
  nodeId: string,
  edges: MindMapEdge[],
  nodes: MindMapNode[],
): MindMapNode | undefined {
  const parentId = edges.find((e) => e.to === nodeId)?.from;
  return parentId ? nodes.find((n) => n.id === parentId) : undefined;
}

export function getMindMapNodeColors(depth: number, selected: boolean) {
  if (depth === 0) {
    return {
      fill: selected ? colors.brand.accent : colors.brand.DEFAULT,
      text: colors.bg.DEFAULT,
      fontWeight: "600",
    };
  }

  if (depth === 1) {
    return {
      fill: selected ? colors.brand.accent : colors.brand.light,
      text: selected ? colors.bg.DEFAULT : colors.fg.secondary,
      fontWeight: "600",
    };
  }

  return {
    fill: selected ? colors.brand.light : colors.brand.subtle,
    text: colors.fg.secondary,
    fontWeight: "400",
  };
}

export function getMindMapEdgeColor(childDepth: number) {
  return childDepth <= 1 ? colors.brand.light : colors.brand.subtle;
}

export function getRelatedSources(node: MindMapNode, allSources: Source[]): Source[] {
  const terms = node.label.toLowerCase().split(/\s+/).filter((t) => t.length > 2);

  const scored = allSources.map((source) => {
    const haystack = `${source.title} ${source.relevantTo.join(" ")}`.toLowerCase();
    const matchScore = terms.reduce(
      (score, term) => (haystack.includes(term) ? score + 1 : score),
      0,
    );
    return { source, matchScore };
  });

  const limit = node.type === "project" ? 4 : 3;

  return scored
    .filter(({ matchScore }) => node.type === "project" || matchScore > 0)
    .sort(
      (a, b) =>
        b.matchScore - a.matchScore || b.source.relevance - a.source.relevance,
    )
    .slice(0, limit)
    .map(({ source }) => source);
}

const SUBTOPIC_RELEVANCE: Record<string, number> = {
  st1: 91,
  st2: 85,
  st3: 88,
  st4: 76,
  st5: 82,
  st6: 79,
  st7: 94,
  st8: 87,
};

export function getSubtopicRelevance(nodeId: string): number {
  return SUBTOPIC_RELEVANCE[nodeId] ?? 80;
}

export function getNodeTypeLabel(type: MindMapNode["type"]): string {
  switch (type) {
    case "project":
      return "Project";
    case "topic":
      return "Topic";
    case "subtopic":
      return "Sub-Topic";
  }
}
