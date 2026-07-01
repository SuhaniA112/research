import { Pencil, Plus, Sparkles } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { SourceListItem } from "@/components/cards/SourceListItem";
import { Breadcrumbs } from "@/components/layout/Breadcrumbs";
import { SaveToProjectButton, PublicationLink } from "@/components/source/SourceActions";
import { getIconSizeClass, IconButton, IconButtonGroup } from "@/components/ui/IconButton";
import { SourceMetricsPanel } from "@/components/source/SourceMetricsPanel";
import { PillButton } from "@/components/ui/PillButton";
import { Tag } from "@/components/ui/Tag";
import { getProject, getSource, sources, summaryTexts } from "@/data/mockData";
import type { SummaryLevel } from "@/types";

export function SourceDetailPage() {
  const { projectId, sourceId } = useParams<{ projectId: string; sourceId: string }>();
  const project = getProject(projectId ?? "");
  const source = getSource(sourceId ?? "");
  const [summaryLevel, setSummaryLevel] = useState<SummaryLevel>("general");

  if (!project || !source) {
    return <p className="text-gray-500">Source not found.</p>;
  }

  const relatedPapers = sources.filter((s) => s.id !== source.id).slice(0, 3);
  const citedSources = sources.filter((s) => s.id !== source.id).slice(1, 4);

  return (
    <div>
      <Breadcrumbs
        items={[
          { label: "All Projects", to: "/projects" },
          { label: project.name, to: `/projects/${project.id}` },
          { label: "Find Sources", to: `/projects/${project.id}/find-sources` },
          { label: source.title },
        ]}
      />

      <div className="mt-4 border-b border-gray-200 pb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{source.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {source.topics.map((t) => (
                <Tag key={t}>{t}</Tag>
              ))}
              <span className="text-sm text-gray-500">
                {source.source} • Published {source.publishedMonth} {source.publishedYear}
              </span>
            </div>
            <p className="mt-2 text-sm text-gray-600">
              Author(s): {source.authors.join(", ")}
            </p>
          </div>
          <IconButtonGroup>
            <SaveToProjectButton sourceId={source.id} size="lg" />
            <PublicationLink sourceId={source.id} size="lg" />
          </IconButtonGroup>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-3 gap-8">
        <div className="col-span-2 space-y-6">
          <div>
            <p className="text-xs font-semibold tracking-wide text-gray-500">SUMMARY LEVEL:</p>
            <div className="mt-2 flex gap-2">
              <PillButton
                active={summaryLevel === "general"}
                onClick={() => setSummaryLevel("general")}
              >
                General
              </PillButton>
              <PillButton
                active={summaryLevel === "graduate"}
                onClick={() => setSummaryLevel("graduate")}
              >
                Graduate
              </PillButton>
              <PillButton
                active={summaryLevel === "expert"}
                onClick={() => setSummaryLevel("expert")}
              >
                Expert
              </PillButton>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-gray-700">
              {summaryTexts[summaryLevel]}
            </p>
            <span className="mt-3 flex items-center gap-1 text-xs text-brand-600">
              <Sparkles className="h-3.5 w-3.5" />
              AI Generated Description
            </span>
          </div>

          <div className="rounded-xl border border-gray-200 p-4">
            <p className="text-xs font-semibold tracking-wide text-gray-500">KEY FINDINGS</p>
            <ul className="mt-3 space-y-2 text-sm text-gray-700">
              {source.keyFindings.map((f) => (
                <li key={f.text} className="list-inside list-disc">
                  {f.text} <span className="font-semibold">Found in {f.section}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold tracking-wide text-gray-500">NOTES</p>
              <IconButton size="md" title="Add note" aria-label="Add note">
                <Plus className={getIconSizeClass("md")} />
              </IconButton>
            </div>
            <div className="mt-3 space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="relative rounded-lg bg-surface-muted p-4">
                  <textarea
                    placeholder="Write your notes here"
                    className="w-full resize-none border-0 bg-transparent text-sm outline-none"
                    rows={2}
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
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="overflow-hidden rounded-xl border border-gray-200">
            <SourceMetricsPanel source={source} className="w-full border-l-0" />
          </div>

          <section>
            <p className="text-xs font-semibold tracking-wide text-gray-500">RELATED PAPERS</p>
            <div className="mt-2 space-y-2">
              {relatedPapers.map((s) => (
                <SourceListItem
                  key={s.id}
                  title={s.title}
                  relevance={s.relevance}
                  projectId={projectId}
                  sourceId={s.id}
                />
              ))}
            </div>
          </section>

          <section>
            <p className="text-xs font-semibold tracking-wide text-gray-500">CITES</p>
            <p className="text-xs text-gray-500">List of sources cited by this one.</p>
            <div className="mt-2 space-y-2">
              {citedSources.map((s) => (
                <SourceListItem
                  key={s.id}
                  title={s.title}
                  projectId={projectId}
                  sourceId={s.id}
                />
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
