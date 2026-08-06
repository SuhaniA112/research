import { colors } from "@/lib/theme";
import type { MindMapEdge, MindMapNode, Project, Source } from "@/types";

const ROOT_ID = "center";

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function placeOnCircle(
  cx: number,
  cy: number,
  radius: number,
  index: number,
  total: number,
  startAngle = -Math.PI / 2,
): { x: number; y: number } {
  const angle = startAngle + (2 * Math.PI * index) / Math.max(total, 1);
  return {
    x: clamp(cx + radius * Math.cos(angle), 8, 92),
    y: clamp(cy + radius * Math.sin(angle), 8, 92),
  };
}

function sourceHaystack(source: Source): string {
  return `${source.title} ${source.topics.join(" ")} ${source.relevantTo.join(" ")}`.toLowerCase();
}

function sourcesForTopic(topic: string, sources: Source[]): Source[] {
  const needle = topic.toLowerCase();
  return sources.filter((source) => {
    if (source.topics.some((t) => t.toLowerCase() === needle)) return true;
    return sourceHaystack(source).includes(needle);
  });
}

/** Build a mind map from project topics + saved papers when no backend map exists. */
export function buildMindMapFromProject(
  project: Pick<Project, "name" | "topics">,
  sources: Source[],
): { nodes: MindMapNode[]; edges: MindMapEdge[] } {
  const nodes: MindMapNode[] = [
    {
      id: ROOT_ID,
      label: project.name || "Project",
      type: "project",
      x: 50,
      y: 50,
    },
  ];
  const edges: MindMapEdge[] = [];

  let topics = project.topics.map((t) => t.trim()).filter(Boolean);
  if (topics.length === 0) {
    const fromSources = new Set<string>();
    for (const source of sources) {
      for (const topic of source.topics) {
        const trimmed = topic.trim();
        if (trimmed) fromSources.add(trimmed);
      }
    }
    topics = [...fromSources].slice(0, 8);
  }

  topics.forEach((topic, index) => {
    const topicId = `t${index}`;
    const pos = placeOnCircle(50, 50, 28, index, topics.length);
    const matching = sourcesForTopic(topic, sources);

    const subtopicLabels: string[] = [];
    const seen = new Set<string>([topic.toLowerCase()]);
    for (const source of matching) {
      for (const tag of source.topics) {
        const key = tag.trim().toLowerCase();
        if (!key || seen.has(key)) continue;
        if (topics.some((t) => t.toLowerCase() === key)) continue;
        seen.add(key);
        subtopicLabels.push(tag.trim());
        if (subtopicLabels.length >= 4) break;
      }
      if (subtopicLabels.length >= 4) break;
    }

    nodes.push({
      id: topicId,
      label: topic,
      type: "topic",
      x: pos.x,
      y: pos.y,
      sourcesSaved: matching.length,
      subTopics: subtopicLabels.length,
    });
    edges.push({ from: ROOT_ID, to: topicId });

    subtopicLabels.forEach((sub, subIndex) => {
      const spread = (subIndex - (subtopicLabels.length - 1) / 2) * 0.55;
      const baseAngle =
        -Math.PI / 2 + (2 * Math.PI * index) / Math.max(topics.length, 1) + spread;
      const subPos = {
        x: clamp(pos.x + 14 * Math.cos(baseAngle), 6, 94),
        y: clamp(pos.y + 14 * Math.sin(baseAngle), 6, 94),
      };
      const subId = `${topicId}-s${subIndex}`;
      nodes.push({
        id: subId,
        label: sub,
        type: "subtopic",
        x: subPos.x,
        y: subPos.y,
      });
      edges.push({ from: topicId, to: subId });
    });
  });

  return { nodes, edges };
}

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
    const haystack = sourceHaystack(source);
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
        b.matchScore - a.matchScore ||
        (b.source.relevance ?? 0) - (a.source.relevance ?? 0),
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
