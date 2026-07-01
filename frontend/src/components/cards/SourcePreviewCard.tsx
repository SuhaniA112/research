import { Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { SourceActions } from "@/components/source/SourceActions";
import { SourceMetricsPanel } from "@/components/source/SourceMetricsPanel";
import { Tag } from "@/components/ui/Tag";
import { getSourcePageLink, type SourceReferrer } from "@/lib/sourcePaths";
import type { Source } from "@/types";

interface SourcePreviewCardProps {
  source: Source;
  projectId?: string;
  sourceReferrer?: SourceReferrer;
  variant?: "featured" | "standard" | "compact";
}

export function SourcePreviewCard({
  source,
  projectId,
  sourceReferrer,
  variant = "standard",
}: SourcePreviewCardProps) {
  const referrer =
    sourceReferrer ??
    (projectId
      ? { type: "project-overview" as const, projectId }
      : { type: "hub" as const });
  const sourceLink = getSourcePageLink(source.id, referrer);
  const showKeyFindings = variant === "featured";

  if (variant === "compact") {
    return (
      <div className="flex flex-col rounded-xl border border-gray-200 bg-white transition-shadow hover:shadow-md">
        <Link to={sourceLink} className="flex flex-1 flex-col p-5 pb-0">
          <div className="flex flex-wrap items-center gap-2">
            {source.topics.map((topic) => (
              <Tag key={topic}>{topic}</Tag>
            ))}
            <span className="text-xs text-gray-500">
              {source.source} • Published {source.publishedMonth} {source.publishedYear}
            </span>
          </div>
          <h3 className="mt-2 font-semibold text-gray-900 group-hover:text-brand-700">
            {source.title}
          </h3>
          <p className="mt-2 line-clamp-3 text-sm text-gray-600">{source.description}</p>
          <div className="mt-auto flex gap-2 pt-4">
            <span className="rounded bg-metrics-bg px-2 py-0.5 text-xs font-semibold text-metrics">
              {source.relevance}% RELEVANT
            </span>
            <span className="rounded bg-metrics-bg px-2 py-0.5 text-xs font-semibold text-metrics">
              {source.similarity}% SIMILAR
            </span>
          </div>
        </Link>
        <div className="flex justify-end px-5 pb-5 pt-2">
          <SourceActions sourceId={source.id} projectId={projectId} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex overflow-hidden rounded-xl border border-gray-200 bg-white transition-shadow hover:shadow-md">
      <div className="flex min-w-0 flex-1 flex-col">
        <Link to={sourceLink} className="flex flex-1 flex-col p-5 pb-0">
          <div className="flex flex-wrap items-center gap-2">
            {source.topics.map((topic) => (
              <Tag key={topic}>{topic}</Tag>
            ))}
            <span className="text-xs text-gray-500">
              {source.source} • Published {source.publishedMonth} {source.publishedYear}
            </span>
          </div>

          <h3
            className={`mt-2 font-bold text-gray-900 ${
              variant === "featured" ? "text-xl" : "text-base"
            }`}
          >
            {source.title}
          </h3>

          <p className="mt-2 text-sm leading-relaxed text-gray-600">{source.description}</p>

          <span className="mt-3 flex items-center gap-1 text-xs text-brand-600">
            <Sparkles className="h-3.5 w-3.5" />
            AI Generated Description
          </span>

          {showKeyFindings && (
            <div className="mt-4 rounded-lg border border-gray-200 bg-surface-muted p-4">
              <p className="text-xs font-semibold tracking-wide text-gray-500">KEY FINDINGS</p>
              <ul className="mt-2 space-y-1.5 text-sm text-gray-700">
                {source.keyFindings.map((f) => (
                  <li key={f.text} className="list-inside list-disc">
                    {f.text} <span className="font-semibold">Found in {f.section}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Link>

        <div className="flex justify-end px-5 pb-5 pt-4">
          <SourceActions sourceId={source.id} projectId={projectId} />
        </div>
      </div>

      <Link to={sourceLink} className="shrink-0 hover:bg-gray-100/60">
        <SourceMetricsPanel source={source} />
      </Link>
    </div>
  );
}
