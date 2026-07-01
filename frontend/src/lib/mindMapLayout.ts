import type { MindMapNode } from "@/types";

type NodeType = MindMapNode["type"];

const NODE_LIMITS: Record<NodeType, { min: number; max: number; charFactor: number; padding: number }> = {
  project: { min: 8, max: 18, charFactor: 0.34, padding: 3 },
  topic: { min: 5, max: 11, charFactor: 0.28, padding: 2.5 },
  subtopic: { min: 3.5, max: 7.5, charFactor: 0.22, padding: 2 },
};

const FONT_SIZE: Record<NodeType, number> = {
  project: 2.2,
  topic: 1.85,
  subtopic: 1.45,
};

const LINE_HEIGHT: Record<NodeType, number> = {
  project: 2.6,
  topic: 2.2,
  subtopic: 1.8,
};

function maxCharsPerLine(type: NodeType, radius: number): number {
  const width = radius * 1.55;
  const charWidth = type === "project" ? 1.15 : type === "topic" ? 1 : 0.85;
  return Math.max(4, Math.floor(width / charWidth));
}

export function wrapLabel(label: string, maxChars: number): string[] {
  const words = label.split(" ");
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxChars) {
      current = candidate;
    } else {
      if (current) lines.push(current);
      current = word.length > maxChars ? `${word.slice(0, maxChars - 1)}…` : word;
    }
  }

  if (current) lines.push(current);
  return lines.length > 0 ? lines : [label];
}

export function getNodeRadius(label: string, type: NodeType): number {
  const { min, max, charFactor, padding } = NODE_LIMITS[type];
  let radius = Math.min(max, Math.max(min, label.length * charFactor + padding));

  const charsPerLine = maxCharsPerLine(type, radius);
  let lines = wrapLabel(label, charsPerLine);

  if (lines.length > 1) {
    const longestLine = Math.max(...lines.map((line) => line.length));
    const lineRadius = longestLine * charFactor + padding;
    const heightRadius = (lines.length * LINE_HEIGHT[type]) / 2 + padding;
    radius = Math.min(max, Math.max(min, lineRadius, heightRadius));
    lines = wrapLabel(label, maxCharsPerLine(type, radius));
  }

  if (lines.length > 2 && type === "subtopic") {
    radius = Math.min(max, radius + (lines.length - 2) * 0.8);
  }

  return radius;
}

export function getNodeFontSize(type: NodeType, label: string, radius: number): number {
  const base = FONT_SIZE[type];
  const charsPerLine = maxCharsPerLine(type, radius);
  const lines = wrapLabel(label, charsPerLine);

  if (lines.length > 2) return base * 0.8;
  if (lines.some((line) => line.length > charsPerLine - 1)) return base * 0.88;
  return base;
}

export function getNodeLineHeight(type: NodeType): number {
  return LINE_HEIGHT[type];
}

export function getNodeLines(label: string, type: NodeType, radius: number): string[] {
  return wrapLabel(label, maxCharsPerLine(type, radius));
}
