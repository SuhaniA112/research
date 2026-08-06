import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import { getProject } from "@/api/projects";
import { listSavedSources, unsaveSource } from "@/api/sources";
import { SavedSourceCard } from "@/components/cards/ArticleCard";
import { ProjectLayoutHeader } from "@/components/layout/ProjectLayoutHeader";
import { FilterMenu, FilterOptionList } from "@/components/ui/FilterMenu";
import { PillButton } from "@/components/ui/PillButton";
import { useStarred } from "@/providers/StarredProvider";
import type { Project, Source } from "@/types";

function matchesSearch(source: Source, query: string): boolean {
  if (!query) return true;
  const haystack = [
    source.title,
    source.description,
    source.source,
    ...source.topics,
    ...source.authors,
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query.toLowerCase());
}

export function SavedSourcesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();
  const [project, setProject] = useState<Project | null | undefined>(undefined);
  const [sources, setSources] = useState<Source[]>([]);
  const [filter, setFilter] = useState<"all" | "starred">("all");
  const [search, setSearch] = useState("");
  const [selectedTopics, setSelectedTopics] = useState<Set<string>>(() => new Set());
  const [selectedProviders, setSelectedProviders] = useState<Set<string>>(
    () => new Set(),
  );
  const { isSourceStarred } = useStarred();

  async function refreshSources(id: string) {
    const next = await listSavedSources(id);
    setSources(next);
  }

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    void getProject(projectId).then((p) => setProject(p ?? null));
    void refreshSources(projectId);
  }, [projectId]);

  const topicOptions = useMemo(
    () =>
      [...new Set(sources.flatMap((source) => source.topics).filter(Boolean))].sort(
        (a, b) => a.localeCompare(b),
      ),
    [sources],
  );

  const providerOptions = useMemo(
    () =>
      [...new Set(sources.map((source) => source.source).filter(Boolean))].sort(
        (a, b) => a.localeCompare(b),
      ),
    [sources],
  );

  const savedSources = sources.filter((s) => {
    const matchesStar = filter === "all" || isSourceStarred(s.id);
    const matchesTopic =
      selectedTopics.size === 0 ||
      s.topics.some((topic) => selectedTopics.has(topic));
    const matchesProvider =
      selectedProviders.size === 0 || selectedProviders.has(s.source);
    return (
      matchesStar &&
      matchesTopic &&
      matchesProvider &&
      matchesSearch(s, search) &&
      Boolean(s.savedOn)
    );
  });

  async function handleRemove(sourceId: string) {
    if (!projectId) return;
    const ok = window.confirm("Remove this source from the project?");
    if (!ok) return;
    await unsaveSource(projectId, sourceId);
    setSources((prev) => prev.filter((source) => source.id !== sourceId));
    await queryClient.invalidateQueries({ queryKey: ["projects"] });
  }

  function toggleValue(setter: typeof setSelectedTopics, value: string) {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }

  if (project === undefined) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  if (!project) {
    return <p className="text-gray-500">Project not found.</p>;
  }

  const activeFilterCount = selectedTopics.size + selectedProviders.size;

  return (
    <div>
      <ProjectLayoutHeader />

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
        <FilterMenu activeCount={activeFilterCount}>
          <div className="space-y-4">
            <FilterOptionList
              title="TOPICS"
              options={topicOptions}
              selected={selectedTopics}
              onToggle={(value) => toggleValue(setSelectedTopics, value)}
              onClear={() => setSelectedTopics(new Set())}
              emptyText="No topics on saved sources yet."
            />
            <FilterOptionList
              title="PROVIDERS"
              options={providerOptions}
              selected={selectedProviders}
              onToggle={(value) => toggleValue(setSelectedProviders, value)}
              onClear={() => setSelectedProviders(new Set())}
              emptyText="No providers yet."
            />
          </div>
        </FilterMenu>
      </div>

      <div className="mt-4 flex gap-2">
        <PillButton active={filter === "all"} onClick={() => setFilter("all")}>
          All
        </PillButton>
        <PillButton active={filter === "starred"} onClick={() => setFilter("starred")}>
          Starred
        </PillButton>
      </div>

      <div className="mt-6 space-y-4">
        {savedSources.length === 0 ? (
          <p className="text-sm text-gray-500">
            {sources.length === 0
              ? "No saved sources yet."
              : "No sources match the current filters."}
          </p>
        ) : (
          savedSources.map((source) => (
            <SavedSourceCard
              key={source.id}
              source={source}
              projectId={projectId!}
              onRemove={(id) => void handleRemove(id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
