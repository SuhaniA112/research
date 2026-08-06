import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { getProject } from "@/api/projects";
import { recordSearch, searchSources, useInvalidateSearchHistory } from "@/api/research";
import { SourceCard } from "@/components/cards/SourceCard";
import { Breadcrumbs } from "@/components/layout/Breadcrumbs";
import {
  FilterMenu,
  FilterOptionList,
  SortBySelect,
  YearRangeSlider,
  type SourceSortOption,
} from "@/components/ui/FilterMenu";
import type { Project, Source } from "@/types";

/** Providers used by discovery (available before results load). */
const RESEARCH_PROVIDERS = [
  { value: "arxiv", label: "arXiv" },
  { value: "openalex", label: "OpenAlex" },
  { value: "semantic_scholar", label: "Semantic Scholar" },
  { value: "dblp", label: "DBLP" },
] as const;

const PROVIDER_OPTIONS = RESEARCH_PROVIDERS.map((p) => p.value);
const PROVIDER_LABELS: Record<string, string> = Object.fromEntries(
  RESEARCH_PROVIDERS.map((p) => [p.value, p.label]),
);

/**
 * Earliest scholarly coverage across our providers (OpenAlex indexes early
 * modern scientific publishing from ~1665; arXiv/DBLP/S2 are later).
 */
const YEAR_MIN = 1665;
const YEAR_MAX = new Date().getFullYear(); // "Present"

function sourceYear(source: Source): number | null {
  const year = source.publishedYear;
  if (!year || year < YEAR_MIN) return null;
  return year;
}

function sortSources(sources: Source[], sortBy: SourceSortOption): Source[] {
  const copy = [...sources];
  const nullsLast = (value: number | null | undefined) =>
    value == null ? Number.NEGATIVE_INFINITY : value;

  switch (sortBy) {
    case "recent":
      return copy.sort(
        (a, b) => (sourceYear(b) ?? 0) - (sourceYear(a) ?? 0) || a.title.localeCompare(b.title),
      );
    case "oldest":
      return copy.sort(
        (a, b) =>
          (sourceYear(a) ?? 9999) - (sourceYear(b) ?? 9999) || a.title.localeCompare(b.title),
      );
    case "citations":
      return copy.sort(
        (a, b) => nullsLast(b.citations) - nullsLast(a.citations) || a.title.localeCompare(b.title),
      );
    case "similarity":
      return copy.sort(
        (a, b) =>
          nullsLast(b.similarity) - nullsLast(a.similarity) || a.title.localeCompare(b.title),
      );
    case "relevance":
    default:
      return copy.sort(
        (a, b) =>
          nullsLast(b.relevance) - nullsLast(a.relevance) || a.title.localeCompare(b.title),
      );
  }
}

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
  const [selectedProviders, setSelectedProviders] = useState<Set<string>>(
    () => new Set(),
  );
  const [yearFrom, setYearFrom] = useState(YEAR_MIN);
  const [yearTo, setYearTo] = useState(YEAR_MAX);
  const [sortBy, setSortBy] = useState<SourceSortOption>("relevance");

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

  const yearAtFullRange = yearFrom === YEAR_MIN && yearTo === YEAR_MAX;

  const filtered = useMemo(() => {
    const next = results.filter((source) => {
      const matchesProvider =
        selectedProviders.size === 0 || selectedProviders.has(source.source);
      const year = sourceYear(source);
      const matchesYear =
        yearAtFullRange ||
        (year != null && year >= yearFrom && year <= yearTo);
      return matchesProvider && matchesYear;
    });
    return sortSources(next, sortBy);
  }, [results, selectedProviders, yearFrom, yearTo, yearAtFullRange, sortBy]);

  const visible = filtered.slice(0, visibleCount);

  function toggleProvider(value: string) {
    setSelectedProviders((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
    setVisibleCount(3);
  }

  if (project === undefined) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  if (!project) {
    return <p className="text-gray-500">Project not found.</p>;
  }

  const activeFilterCount =
    selectedProviders.size +
    (yearAtFullRange ? 0 : 1) +
    (sortBy !== "relevance" ? 1 : 0);

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
        <FilterMenu activeCount={activeFilterCount} wide>
          <div className="space-y-4">
            <SortBySelect
              value={sortBy}
              onChange={(value) => {
                setSortBy(value);
                setVisibleCount(3);
              }}
            />
            <YearRangeSlider
              min={YEAR_MIN}
              max={YEAR_MAX}
              from={yearFrom}
              to={yearTo}
              maxLabel="Present"
              onChange={(from, to) => {
                setYearFrom(from);
                setYearTo(to);
                setVisibleCount(3);
              }}
              onReset={() => {
                setYearFrom(YEAR_MIN);
                setYearTo(YEAR_MAX);
                setVisibleCount(3);
              }}
            />
            <FilterOptionList
              title="PROVIDERS"
              options={[...PROVIDER_OPTIONS]}
              labels={PROVIDER_LABELS}
              selected={selectedProviders}
              onToggle={toggleProvider}
              onClear={() => {
                setSelectedProviders(new Set());
                setVisibleCount(3);
              }}
            />
          </div>
        </FilterMenu>
      </div>

      <div className="mt-6 space-y-4">
        {loading && (
          <p className="text-sm text-gray-500">
            Searching… this can take up to a minute while we query external
            research APIs.
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && filtered.length === 0 && (
          <p className="text-sm text-gray-500">
            {results.length === 0
              ? "No sources found. Try a different query, or leave the box empty to load default research results."
              : "No sources match the current filters."}
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

      {!loading && visibleCount < filtered.length && (
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
