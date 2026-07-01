import { useParams } from "react-router-dom";
import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { Search } from "lucide-react";
import { Link } from "react-router-dom";

import { SourcePreviewCard } from "@/components/cards/SourcePreviewCard";
import { ProjectLayoutHeader } from "@/components/layout/ProjectLayoutHeader";
import { ProjectStatCard } from "@/components/stats/ProjectStatCard";
import { SourceBreakdownCard } from "@/components/stats/SourceBreakdownCard";
import { getProject, recentProjectSearches, sourceRecency, sources } from "@/data/mockData";
import { getFindSourcesPath } from "@/lib/sourcePaths";

export function ProjectOverviewPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const project = getProject(projectId ?? "");
  const viewNext = sources.slice(0, 2);
  const searches = recentProjectSearches[projectId ?? ""] ?? [];

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
              {viewNext.map((source) => (
                <SourcePreviewCard
                  key={source.id}
                  source={source}
                  projectId={projectId}
                  variant="standard"
                />
              ))}
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
              {searches.map((search) => (
                <Link
                  key={search}
                  to={getFindSourcesPath(projectId!, search)}
                  className="flex items-center justify-between rounded-lg bg-surface-muted px-4 py-3 hover:bg-gray-200"
                >
                  <span className="text-sm text-gray-700">{search}</span>
                  <Search className="h-4 w-4 text-gray-400" />
                </Link>
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-4">
          <h2 className="text-xs font-semibold tracking-wide text-gray-500">PROJECT STATS</h2>

          <SourceBreakdownCard />

          <ProjectStatCard
            title="SOURCE RECENCY"
            subtitle={`${project.sourceCount} sources from 2020 onwards`}
            badge={
              <span className="rounded-full bg-metric-green-light px-2 py-0.5 text-xs font-medium text-metric-green">
                18 since 2021
              </span>
            }
          >
            <ResponsiveContainer width="100%" height={100}>
              <BarChart data={sourceRecency}>
                <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                <YAxis hide />
                <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                  {sourceRecency.map((entry) => (
                    <Cell
                      key={entry.year}
                      fill={Number(entry.year) >= 2021 ? "#a21caf" : "#9ca3af"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ProjectStatCard>

          <ProjectStatCard
            title="SOURCE VALIDITY"
            subtitle="How connected & cross-referenced your sources are"
          >
            <div className="flex flex-col items-center">
              <div className="relative h-20 w-40 overflow-hidden">
                <div className="absolute inset-0 rounded-t-full border-8 border-gray-200" />
                <div
                  className="absolute inset-0 rounded-t-full border-8 border-metric-green"
                  style={{ clipPath: "inset(0 0 50% 0)" }}
                />
              </div>
              <p className="text-2xl font-bold">82 / 100</p>
              <p className="text-xs font-semibold text-metric-green">HIGHLY CONNECTED</p>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {[
                ["Cross-cited", "76%"],
                ["Peer-reviewed", "68%"],
                ["Open access", "54%"],
                ["Multi-author", "89%"],
              ].map(([label, value]) => (
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
