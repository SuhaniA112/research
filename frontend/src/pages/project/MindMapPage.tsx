import { Pencil, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { SourceListItem } from "@/components/cards/SourceListItem";
import { ProjectLayoutHeader } from "@/components/layout/ProjectLayoutHeader";
import { PanZoomSvg, usePanZoomScale } from "@/components/ui/PanZoomSvg";
import { Tag } from "@/components/ui/Tag";
import { getIconSizeClass, IconButton } from "@/components/ui/IconButton";
import { mindMapEdges, mindMapNodes, sources } from "@/data/mockData";
import { getNodeLabelLayout, getNodeRadius } from "@/lib/mindMapLayout";
import {
  buildDepthMap,
  getChildNodes,
  getMindMapEdgeColor,
  getMindMapNodeColors,
  getNodeTypeLabel,
  getParentNode,
  getRelatedSources,
  getSubtopicRelevance,
} from "@/lib/mindMap";
import type { MindMapNode } from "@/types";

function MindMapNodeShape({
  node,
  depth,
  selected,
  onSelect,
}: {
  node: MindMapNode;
  depth: number;
  selected: boolean;
  onSelect: () => void;
}) {
  const zoomScale = usePanZoomScale();
  const radius = getNodeRadius(node.label, node.type);
  const { lines, fontSize, lineHeight } = getNodeLabelLayout(
    node.label,
    node.type,
    radius,
    zoomScale,
  );

  const { fill, text, fontWeight } = getMindMapNodeColors(depth, selected);
  const firstLineOffset = -((lines.length - 1) * lineHeight) / 2;

  return (
    <g
      className="cursor-pointer"
      onPointerDown={(event) => event.stopPropagation()}
      onClick={(event) => {
        event.stopPropagation();
        onSelect();
      }}
    >
      <circle cx={node.x} cy={node.y} r={radius + 0.8} fill="transparent" />
      <circle cx={node.x} cy={node.y} r={radius} fill={fill} />
      <text
        x={node.x}
        y={node.y}
        textAnchor="middle"
        dominantBaseline="middle"
        fill={text}
        fontSize={fontSize}
        fontWeight={fontWeight}
        pointerEvents="none"
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
    mindMapNodes.find((n) => n.type === "project") ?? mindMapNodes[0]!,
  );

  const depthMap = useMemo(() => buildDepthMap(mindMapEdges), []);
  const nodeRadii = useMemo(
    () =>
      Object.fromEntries(
        mindMapNodes.map((node) => [node.id, getNodeRadius(node.label, node.type)]),
      ),
    [],
  );

  const childNodes = useMemo(
    () => getChildNodes(selectedNode.id, mindMapEdges, mindMapNodes),
    [selectedNode.id],
  );
  const parentNode = useMemo(
    () => getParentNode(selectedNode.id, mindMapEdges, mindMapNodes),
    [selectedNode.id],
  );
  const relatedSources = useMemo(
    () => getRelatedSources(selectedNode, sources),
    [selectedNode],
  );
  const topicCount = useMemo(
    () => mindMapNodes.filter((n) => n.type === "topic").length,
    [],
  );

  return (
    <div>
      <ProjectLayoutHeader />

      <div className="mt-8 grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-brand-50">
            <PanZoomSvg viewBox="0 0 100 100">
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
                const childDepth = depthMap.get(to.id) ?? 1;

                return (
                  <line
                    key={`${edge.from}-${edge.to}`}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={getMindMapEdgeColor(childDepth)}
                    strokeWidth="0.3"
                    strokeDasharray="1 1"
                  />
                );
              })}
              {mindMapNodes.map((node) => (
                <MindMapNodeShape
                  key={node.id}
                  node={node}
                  depth={depthMap.get(node.id) ?? 0}
                  selected={selectedNode.id === node.id}
                  onSelect={() => setSelectedNode(node)}
                />
              ))}
            </PanZoomSvg>
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <p className="text-xs font-semibold tracking-wide text-gray-500">
              {getNodeTypeLabel(selectedNode.type).toUpperCase()}
            </p>
            <h3 className="mt-1 text-xl font-bold text-brand-700">{selectedNode.label}</h3>
            {selectedNode.type === "project" && (
              <p className="mt-1 text-sm text-gray-500">
                {relatedSources.length} Related Sources • {topicCount} Topics
              </p>
            )}
            {selectedNode.type === "topic" && selectedNode.sourcesSaved !== undefined && (
              <p className="mt-1 text-sm text-gray-500">
                {selectedNode.sourcesSaved} Sources Saved • {selectedNode.subTopics ?? childNodes.length}{" "}
                Sub-Topics
              </p>
            )}
            {selectedNode.type === "subtopic" && parentNode && (
              <p className="mt-1 text-sm text-gray-500">
                Under <span className="font-medium text-gray-700">{parentNode.label}</span>
              </p>
            )}
          </div>

          <section>
            <p className="text-xs font-semibold tracking-wide text-gray-500">
              {selectedNode.type === "project" ? "TOP SOURCES" : "RELATED SAVED SOURCES"}
            </p>
            <div className="mt-2 space-y-2">
              {relatedSources.length > 0 ? (
                relatedSources.map((source) => (
                  <SourceListItem
                    key={source.id}
                    title={source.title}
                    relevance={source.relevance}
                    projectId={projectId}
                    sourceId={source.id}
                    sourceReferrer={{ type: "mind-map", projectId: projectId! }}
                  />
                ))
              ) : (
                <p className="text-sm text-gray-500">No saved sources match this node yet.</p>
              )}
            </div>
            {relatedSources.length > 0 && (
              <button type="button" className="mt-2 text-sm text-brand-700 hover:underline">
                See more →
              </button>
            )}
          </section>

          {selectedNode.type === "topic" && childNodes.length > 0 && (
            <section>
              <p className="text-xs font-semibold tracking-wide text-gray-500">
                SUGGESTED SUBTOPICS
              </p>
              <div className="mt-2 space-y-2">
                {childNodes.map((child) => (
                  <button
                    key={child.id}
                    type="button"
                    onClick={() => setSelectedNode(child)}
                    className="flex w-full items-center gap-2 text-left"
                  >
                    <Tag>{child.label}</Tag>
                    <span className="text-xs text-gray-500">
                      • {getSubtopicRelevance(child.id)}% Relevant
                    </span>
                  </button>
                ))}
              </div>
            </section>
          )}

          {selectedNode.type === "project" && childNodes.length > 0 && (
            <section>
              <p className="text-xs font-semibold tracking-wide text-gray-500">TOPICS</p>
              <div className="mt-2 space-y-2">
                {childNodes.map((child) => (
                  <button
                    key={child.id}
                    type="button"
                    onClick={() => setSelectedNode(child)}
                    className="flex w-full items-center justify-between rounded-lg border border-gray-200 px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                  >
                    <span>{child.label}</span>
                    {child.sourcesSaved !== undefined && (
                      <span className="text-xs text-gray-500">{child.sourcesSaved} sources</span>
                    )}
                  </button>
                ))}
              </div>
            </section>
          )}

          <section>
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold tracking-wide text-gray-500">NOTES</p>
              <IconButton size="md" title="Add note" aria-label="Add note">
                <Plus className={getIconSizeClass("md")} />
              </IconButton>
            </div>
            <div className="relative mt-2 rounded-lg bg-surface-muted p-4">
              <textarea
                placeholder={`Notes about ${selectedNode.label}…`}
                className="w-full resize-none border-0 bg-transparent text-sm outline-none"
                rows={3}
                key={selectedNode.id}
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
