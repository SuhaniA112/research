import { Filter, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getProject } from "@/api/projects";
import { listSavedSources } from "@/api/sources";
import { SavedSourceCard } from "@/components/cards/ArticleCard";
import { ProjectLayoutHeader } from "@/components/layout/ProjectLayoutHeader";
import { PillButton } from "@/components/ui/PillButton";
import { useStarred } from "@/providers/StarredProvider";
import type { Project, Source } from "@/types";

export function SavedSourcesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null | undefined>(undefined);
  const [sources, setSources] = useState<Source[]>([]);
  const [filter, setFilter] = useState<"all" | "starred">("all");
  const [search, setSearch] = useState("");
  const { isSourceStarred } = useStarred();

  useEffect(() => {
    if (!projectId) {
      setProject(null);
      return;
    }
    void getProject(projectId).then((p) => setProject(p ?? null));
    void listSavedSources(projectId).then(setSources);
  }, [projectId]);

  const savedSources = sources.filter((s) => {
    const matchesFilter = filter === "all" || isSourceStarred(s.id);
    const matchesSearch =
      !search || s.title.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch && s.savedOn;
  });

  if (project === undefined) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  if (!project) {
    return <p className="text-gray-500">Project not found.</p>;
  }

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
        <button
          type="button"
          className="flex items-center gap-2 rounded-lg bg-brand-100 px-4 py-2 text-sm font-medium text-brand-700"
        >
          <Filter className="h-4 w-4" />
          Filter
        </button>
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
        {savedSources.map((source) => (
          <SavedSourceCard key={source.id} source={source} projectId={projectId!} />
        ))}
      </div>
    </div>
  );
}
