import { Pencil, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { SourceListItem } from "@/components/cards/SourceListItem";
import { ProjectLayoutHeader } from "@/components/layout/ProjectLayoutHeader";
import { Tag } from "@/components/ui/Tag";
import { getIconSizeClass, IconButton } from "@/components/ui/IconButton";
import { mindMapEdges, mindMapNodes, sources } from "@/data/mockData";
import {
  getNodeFontSize,
  getNodeLineHeight,
  getNodeLines,
  getNodeRadius,
} from "@/lib/mindMapLayout";
import type { MindMapNode } from "@/types";

function MindMapNodeShape({
  node,
  selected,
  onSelect,
}: {
  node: MindMapNode;
  selected: boolean;
  onSelect: () => void;
}) {
  const radius = getNodeRadius(node.label, node.type);
  const fontSize = getNodeFontSize(node.type, node.label, radius);
  const lineHeight = getNodeLineHeight(node.type);
  const lines = getNodeLines(node.label, node.type, radius);

  const isCenter = node.type === "project";
  const isTopic = node.type === "topic";
  const fill = isCenter
    ? "#701a4f"
    : isTopic
      ? selected
        ? "#a21caf"
        : "#c026d3"
      : "#e5e7eb";
  const textFill = isCenter || isTopic ? "white" : "#374151";
  const firstLineOffset = -((lines.length - 1) * lineHeight) / 2;

  return (
    <g className="cursor-pointer" onClick={onSelect}>
      <circle cx={node.x} cy={node.y} r={radius} fill={fill} />
      <text
        x={node.x}
        y={node.y}
        textAnchor="middle"
        dominantBaseline="middle"
        fill={textFill}
        fontSize={fontSize}
        fontWeight={isCenter || isTopic ? "600" : "400"}
      >
        {lines.map((line, index) => (
          <tspan key={`${node.id}-${index}`} x={node.x} dy={index === 0 ? firstLineOffset : lineHeight}>
            {line}
          </tspan>
        ))}
      </text>
    </g>
  );
}

export function MindMapPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [selectedNode, setSelectedNode] = useState<MindMapNode>(
    mindMapNodes.find((n) => n.type === "topic") ?? mindMapNodes[1]!,
  );

  const relatedSources = sources.slice(0, 3);
  const nodeRadii = useMemo(
    () =>
      Object.fromEntries(
        mindMapNodes.map((node) => [node.id, getNodeRadius(node.label, node.type)]),
      ),
    [],
  );

  return (
    <div>
      <ProjectLayoutHeader />

      <div className="mt-8 grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <div className="relative aspect-[4/3] rounded-xl bg-brand-50 p-4">
            <svg className="h-full w-full" viewBox="0 0 100 100">
              {mindMapEdges.map((edge) => {
                const from = mindMapNodes.find((n) => n.id === edge.from);
                const to = mindMapNodes.find((n) => n.id === edge.to);
                if (!from || !to) return null;

                const fromR = nodeRadii[from.id] ?? 4;
                const toR = nodeRadii[to.id] ?? 4;
                const dx = to.x - from.x;
                const dy = to.y - from.y;
                const distance = Math.hypot(dx, dy) || 1;
                const x1 = from.x + (dx / distance) * fromR;
                const y1 = from.y + (dy / distance) * fromR;
                const x2 = to.x - (dx / distance) * toR;
                const y2 = to.y - (dy / distance) * toR;

                return (
                  <line
                    key={`${edge.from}-${edge.to}`}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="#c4b5fd"
                    strokeWidth="0.3"
                    strokeDasharray="1 1"
                  />
                );
              })}
              {mindMapNodes.map((node) => (
                <MindMapNodeShape
                  key={node.id}
                  node={node}
                  selected={selectedNode.id === node.id}
                  onSelect={() => setSelectedNode(node)}
                />
              ))}
            </svg>
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <p className="text-xs font-semibold tracking-wide text-gray-500">SELECTED NODE</p>
            <h3 className="mt-1 text-xl font-bold text-brand-700">[{selectedNode.label}]</h3>
            {selectedNode.sourcesSaved !== undefined && (
              <p className="mt-1 text-sm text-gray-500">
                {selectedNode.sourcesSaved} Sources Saved • {selectedNode.subTopics ?? 0}{" "}
                Sub-Topics
              </p>
            )}
          </div>

          <section>
            <p className="text-xs font-semibold tracking-wide text-gray-500">
              RELATED SAVED SOURCES
            </p>
            <div className="mt-2 space-y-2">
              {relatedSources.map((source) => (
                <SourceListItem
                  key={source.id}
                  title={source.title}
                  relevance={source.relevance}
                  projectId={projectId}
                  sourceId={source.id}
                />
              ))}
            </div>
            <button type="button" className="mt-2 text-sm text-brand-700 hover:underline">
              See more →
            </button>
          </section>

          <section>
            <p className="text-xs font-semibold tracking-wide text-gray-500">
              SUGGESTED SUBTOPICS
            </p>
            <div className="mt-2 space-y-2">
              {["speech synthesis", "command parsing"].map((sub) => (
                <div key={sub} className="flex items-center gap-2">
                  <Tag>{sub}</Tag>
                  <span className="text-xs text-gray-500">• 85% Relevant</span>
                </div>
              ))}
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold tracking-wide text-gray-500">NOTES</p>
              <IconButton size="md" title="Add note" aria-label="Add note">
                <Plus className={getIconSizeClass("md")} />
              </IconButton>
            </div>
            <div className="relative mt-2 rounded-lg bg-surface-muted p-4">
              <textarea
                placeholder="Write your notes here"
                className="w-full resize-none border-0 bg-transparent text-sm outline-none"
                rows={3}
              />
              <IconButton
                size="sm"
                className="absolute bottom-1 right-1 text-gray-400 hover:bg-transparent hover:text-gray-600"
                title="Edit note"
                aria-label="Edit note"
              >
                <Pencil className={getIconSizeClass("sm")} />
              </IconButton>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
