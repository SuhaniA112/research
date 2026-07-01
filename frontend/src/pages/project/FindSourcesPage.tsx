import { Filter, Search } from "lucide-react";
import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { SourceCard } from "@/components/cards/SourceCard";
import { Breadcrumbs } from "@/components/layout/Breadcrumbs";
import { getProject, sources } from "@/data/mockData";

export function FindSourcesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams] = useSearchParams();
  const project = getProject(projectId ?? "");
  const [search, setSearch] = useState(() => searchParams.get("q") ?? "");
  const [visibleCount, setVisibleCount] = useState(3);

  const filtered = sources.filter(
    (s) => !search || s.title.toLowerCase().includes(search.toLowerCase()),
  );
  const visible = filtered.slice(0, visibleCount);

  if (!project) {
    return <p className="text-gray-500">Project not found.</p>;
  }

  return (
    <div>
      <Breadcrumbs
        items={[
          { label: "All Projects", to: "/projects" },
          { label: project.name, to: `/projects/${project.id}` },
          { label: "Find Sources" },
        ]}
      />
      <h1 className="mt-4 text-2xl font-bold text-gray-900">Find Sources</h1>

      <div className="mt-6 flex gap-3">
        <div className="relative min-w-[240px] flex-1">
          <input
            type="text"
            placeholder="Search by source name, topic, keywords, etc."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-3 pr-10 text-sm focus:border-brand-700 focus:outline-none focus:ring-1 focus:ring-brand-700"
          />
          <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        </div>
        <button
          type="button"
          className="flex items-center gap-2 rounded-lg bg-brand-100 px-4 py-2 text-sm font-medium text-brand-700"
        >
          <Filter className="h-4 w-4" />
          Filter
        </button>
      </div>

      <div className="mt-6 space-y-4">
        {visible.map((source) => (
          <SourceCard key={source.id} source={source} projectId={projectId} />
        ))}
      </div>

      {visibleCount < filtered.length && (
        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => setVisibleCount((c) => c + 2)}
            className="text-sm font-semibold tracking-wide text-brand-700 hover:underline"
          >
            LOAD MORE
          </button>
        </div>
      )}
    </div>
  );
}
