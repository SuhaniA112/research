import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { Search, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { getProject } from "@/api/projects";
import { deleteProjectSearch, getRecentProjectSearches, useInvalidateSearchHistory } from "@/api/research";
import { listSavedSources } from "@/api/sources";
import {
  getSourceBreakdown,
  getSourceRecency,
  getSourceValidity,
  type SourceBreakdownItem,
  type SourceRecencyItem,
  type SourceValidityStats,
} from "@/api/stats";
import { SourcePreviewCard } from "@/components/cards/SourcePreviewCard";
import { ProjectLayoutHeader } from "@/components/layout/ProjectLayoutHeader";
import { ProjectStatCard } from "@/components/stats/ProjectStatCard";
import { SourceBreakdownCard } from "@/components/stats/SourceBreakdownCard";
import { getIconSizeClass, IconButton } from "@/components/ui/IconButton";
import { getFindSourcesPath } from "@/lib/sourcePaths";
import { colors } from "@/lib/theme";
import type { Project, Source } from "@/types";

export function ProjectOverviewPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const invalidateSearchHistory = useInvalidateSearchHistory();
  const [project, setProject] = useState<Project | null | undefined>(undefined);
  const [viewNext, setViewNext] = useState<Source[]>([]);
  const [searches, setSearches] = useState<string[]>([]);
  const [breakdown, setBreakdown] = useState<SourceBreakdownItem[]>([]);
  const [recency, setRecency] = useState<SourceRecencyItem[]>([]);
  const [validity, setValidity] = useState<SourceValidityStats | null>(null);

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    void getProject(projectId).then((p) => setProject(p ?? null));
    void listSavedSources(projectId).then((sources) => setViewNext(sources.slice(0, 2)));
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
                  No saved sources yet. Find and save papers to see them here.
                </p>
              )}
            </div>
            <Link
              to={`/projects/${projectId}/saved`}
              className="mt-3 inline-block text-sm text-brand-700 hover:underline"
            >
              See more of your sources →
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
                      className="min-w-0 flex-1 truncate text-sm text-gray-700 hover:text-brand-700"
                    >
                      {search}
                    </Link>
                    <div className="ml-2 flex shrink-0 items-center gap-1">
                      <Search className="h-4 w-4 text-gray-400" />
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
                        className="text-gray-400 hover:bg-red-50 hover:text-red-600"
                      >
                        <Trash2 className={getIconSizeClass("md")} />
                      </IconButton>
                    </div>
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

          <ProjectStatCard
            title="SOURCE RECENCY"
            subtitle={`${viewNext.length > 0 || project.sourceCount > 0 ? project.sourceCount || "—" : "—"} sources from 2020 onwards`}
            badge={
              <span className="rounded-full bg-metrics-bg px-2 py-0.5 text-xs font-medium text-metrics">
                {typeof recency[0]?.count === "number" ? "18 since 2021" : "[X]% since 2021"}
              </span>
            }
          >
            {recency.length > 0 && typeof recency[0]?.count === "number" ? (
              <ResponsiveContainer width="100%" height={100}>
                <BarChart data={recency}>
                  <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                  <YAxis hide />
                  <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                    {recency.map((entry) => (
                      <Cell
                        key={entry.year}
                        fill={
                          Number(entry.year) >= 2021 ? colors.brand.accent : colors.fg.muted
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-6 text-center text-2xl font-bold text-metrics">[X]%</p>
            )}
          </ProjectStatCard>

          <ProjectStatCard
            title="SOURCE VALIDITY"
            subtitle="How connected & cross-referenced your sources are"
          >
            <div className="flex flex-col items-center">
              <div className="relative h-20 w-40 overflow-hidden">
                <div className="absolute inset-0 rounded-t-full border-8 border-gray-200" />
                {validity && !validity.scoreLabel.includes("[X]") ? (
                  <div
                    className="absolute inset-0 rounded-t-full border-8 border-metrics"
                    style={{ clipPath: "inset(0 0 50% 0)" }}
                  />
                ) : null}
              </div>
              <p className="text-2xl font-bold">
                {validity?.scoreLabel ?? "[X] / 100"}
              </p>
              <p className="text-xs font-semibold text-metrics">
                {validity?.statusLabel ?? "PENDING METRICS"}
              </p>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {(
                validity?.metrics ??
                ([
                  ["Cross-cited", "[X]%"],
                  ["Peer-reviewed", "[X]%"],
                  ["Open access", "[X]%"],
                  ["Multi-author", "[X]%"],
                ] as [string, string][])
              ).map(([label, value]) => (
                <div key={label} className="rounded-lg bg-white p-2 text-center">
                  <p className="text-xs text-gray-500">{label}</p>
                  <p className="text-sm font-semibold">{value}</p>
                </div>
              ))}
            </div>
          </ProjectStatCard>
        </div>
      </div>
    </div>
  );
}
