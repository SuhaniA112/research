import { Filter, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { getProject } from "@/api/projects";
import { recordSearch, searchSources, useInvalidateSearchHistory } from "@/api/research";
import { SourceCard } from "@/components/cards/SourceCard";
import { Breadcrumbs } from "@/components/layout/Breadcrumbs";
import type { Project, Source } from "@/types";

export function FindSourcesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams] = useSearchParams();
  const invalidateSearchHistory = useInvalidateSearchHistory();
  const [project, setProject] = useState<Project | null | undefined>(undefined);
  const [search, setSearch] = useState(() => searchParams.get("q") ?? "");
  const [results, setResults] = useState<Source[]>([]);
  const [visibleCount, setVisibleCount] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    void getProject(projectId).then((p) => setProject(p ?? null));
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    const handle = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      void searchSources(search)
        .then((sources) => {
          if (cancelled) return;
          setResults(sources);
          setVisibleCount(3);
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setResults([]);
          setError(err instanceof Error ? err.message : "Search failed");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
      if (search.trim()) {
        void recordSearch(projectId, search).then(() => {
          if (!cancelled) invalidateSearchHistory();
        });
      }
    }, 400);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [projectId, search, invalidateSearchHistory]);

  const visible = results.slice(0, visibleCount);

  if (project === undefined) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

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
        {loading && (
          <p className="text-sm text-gray-500">
            Searching… this can take up to a minute while we query external
            research APIs.
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && results.length === 0 && (
          <p className="text-sm text-gray-500">
            No sources found. Try a different query, or leave the box empty to load
            default research results.
          </p>
        )}
        {!loading &&
          visible.map((source) => (
            <SourceCard
              key={source.id}
              source={source}
              projectId={projectId}
              sourceReferrer={{ type: "find-sources", projectId: projectId! }}
            />
          ))}
      </div>

      {!loading && visibleCount < results.length && (
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
