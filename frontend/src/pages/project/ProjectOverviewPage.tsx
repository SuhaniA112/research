import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Search, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { getProject } from "@/api/projects";
import { applyCachedProjectScores, scoreForProject } from "@/api/recommendations";
import {
  deleteProjectSearch,
  getRecentProjectSearches,
  getViewNextSources,
  useInvalidateSearchHistory,
} from "@/api/research";
import {
  getSourceBreakdown,
  getSourceRecency,
  getSourceValidity,
  type SourceBreakdownItem,
  type SourceRecencyStats,
  type SourceValidityStats,
} from "@/api/stats";
import { SourcePreviewCard } from "@/components/cards/SourcePreviewCard";
import { ProjectLayoutHeader } from "@/components/layout/ProjectLayoutHeader";
import { ProjectStatCard } from "@/components/stats/ProjectStatCard";
import { SourceBreakdownCard } from "@/components/stats/SourceBreakdownCard";
import { SourceRecencyCard } from "@/components/stats/SourceRecencyCard";
import { getIconSizeClass, IconButton } from "@/components/ui/IconButton";
import { getFindSourcesPath } from "@/lib/sourcePaths";
import type { Project, Source } from "@/types";

const VALIDITY_PLACEHOLDER: SourceValidityStats["metrics"] = [
  "Cross-cited",
  "Peer-reviewed",
  "Open access",
  "Multi-author",
].map((label) => ({ label, value: "—", hint: "" }));

/** Half-circle gauge whose filled arc tracks the 0–100 validity score. */
function ValidityGauge({ score }: { score: number | null }) {
  const arc = "M 10 50 A 40 40 0 0 1 90 50";
  const fraction = score == null ? 0 : Math.max(0, Math.min(score, 100)) / 100;
  return (
    <svg viewBox="0 0 100 55" className="h-20 w-40" aria-hidden="true">
      <path d={arc} fill="none" strokeWidth={8} className="stroke-gray-200" />
      {fraction > 0 ? (
        <path
          d={arc}
          fill="none"
          strokeWidth={8}
          pathLength={100}
          strokeDasharray={`${fraction * 100} 100`}
          className="stroke-metrics"
        />
      ) : null}
    </svg>
  );
}

export function ProjectOverviewPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const invalidateSearchHistory = useInvalidateSearchHistory();
  const [project, setProject] = useState<Project | null | undefined>(undefined);
  const [viewNext, setViewNext] = useState<Source[]>([]);
  const [searches, setSearches] = useState<string[]>([]);
  const [breakdown, setBreakdown] = useState<SourceBreakdownItem[]>([]);
  const [recency, setRecency] = useState<SourceRecencyStats | null>(null);
  const [validity, setValidity] = useState<SourceValidityStats | null>(null);

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    void getProject(projectId).then((p) => setProject(p ?? null));
    void getViewNextSources(projectId, 2)
      .then((next) => {
        setViewNext(applyCachedProjectScores(projectId, next));
        return scoreForProject(projectId, next).then(setViewNext);
      })
      .catch(() => undefined);
    void getRecentProjectSearches(projectId).then(setSearches);
    void getSourceBreakdown(projectId).then(setBreakdown);
    void getSourceRecency(projectId).then(setRecency);
    void getSourceValidity(projectId).then(setValidity);
  }, [projectId]);

  if (project === undefined) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  if (!project) {
    return <p className="text-gray-500">Project not found.</p>;
  }

  return (
    <div>
      <ProjectLayoutHeader />

      <div className="mt-8 grid grid-cols-3 gap-8">
        <div className="col-span-2 space-y-8">
          <section>
            <h2 className="mb-4 text-xs font-semibold tracking-wide text-gray-500">VIEW NEXT</h2>
            <div className="space-y-4">
              {viewNext.length > 0 ? (
                viewNext.map((source) => (
                  <SourcePreviewCard
                    key={source.id}
                    source={source}
                    projectId={projectId}
                    sourceReferrer={{ type: "project-overview", projectId: projectId! }}
                    variant="standard"
                  />
                ))
              ) : (
                <p className="text-sm text-gray-500">
                  No unread papers from your searches yet. Find sources to get
                  recommendations here.
                </p>
              )}
            </div>
            <Link
              to={getFindSourcesPath(projectId!, searches[0])}
              className="mt-3 inline-block text-sm text-brand-700 hover:underline"
            >
              Find more sources →
            </Link>
          </section>

          <section>
            <h2 className="mb-4 text-xs font-semibold tracking-wide text-gray-500">
              RECENT SEARCHES
            </h2>
            <div className="space-y-2">
              {searches.length > 0 ? (
                searches.map((search) => (
                  <div
                    key={search}
                    className="flex items-center justify-between rounded-lg bg-surface-muted px-4 py-3 hover:bg-gray-200"
                  >
                    <Link
                      to={getFindSourcesPath(projectId!, search)}
                      className="flex min-w-0 flex-1 items-center gap-2 truncate text-sm text-gray-700 hover:text-brand-700"
                    >
                      <span className="min-w-0 flex-1 truncate">{search}</span>
                      <Search className="h-4 w-4 shrink-0 text-gray-400" />
                    </Link>
                    <IconButton
                      size="md"
                      title="Delete search"
                      aria-label={`Delete search ${search}`}
                      onClick={() => {
                        void deleteProjectSearch(projectId!, search).then(() => {
                          setSearches((prev) => prev.filter((item) => item !== search));
                          invalidateSearchHistory();
                        });
                      }}
                      className="ml-1 shrink-0 text-gray-400 hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 className={getIconSizeClass("md")} />
                    </IconButton>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">No recent searches yet.</p>
              )}
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <h2 className="text-xs font-semibold tracking-wide text-gray-500">PROJECT STATS</h2>

          <SourceBreakdownCard data={breakdown} />

          <SourceRecencyCard stats={recency} />

          <ProjectStatCard
            title="SOURCE VALIDITY"
            subtitle="How connected & cross-referenced your sources are"
          >
            <div className="flex flex-col items-center">
              <ValidityGauge score={validity?.score ?? null} />
              <p className="text-2xl font-bold">
                {validity?.scoreLabel ?? "— / 100"}
              </p>
              <p className="text-xs font-semibold text-metrics">
                {validity?.statusLabel ?? "LOADING"}
              </p>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {(validity?.metrics ?? VALIDITY_PLACEHOLDER).map((metric) => (
                <div
                  key={metric.label}
                  className="rounded-lg bg-white p-2 text-center"
                  title={metric.hint || undefined}
                >
                  <p className="text-xs text-gray-500">{metric.label}</p>
                  <p className="text-sm font-semibold">{metric.value}</p>
                </div>
              ))}
            </div>
          </ProjectStatCard>
        </div>
      </div>
    </div>
  );
}
