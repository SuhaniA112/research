import { Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useDeleteProject, useProjects } from "@/api/projects";
import { ProjectCard } from "@/components/cards/ProjectCard";
import { PillButton } from "@/components/ui/PillButton";
import { useStarred } from "@/providers/StarredProvider";

export function AllProjectsPage() {
  const [filter, setFilter] = useState<"all" | "starred">("all");
  const [search, setSearch] = useState("");
  const { isProjectStarred } = useStarred();
  const { data: projects = [], isLoading, error } = useProjects();
  const deleteProject = useDeleteProject();

  const filtered = projects.filter((p) => {
    const matchesFilter = filter === "all" || isProjectStarred(p.id);
    const matchesSearch =
      !search || p.name.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  if (isLoading) {
    return <p className="text-sm text-gray-500">Loading projects…</p>;
  }

  if (error) {
    return (
      <p className="text-sm text-red-600">
        {error instanceof Error ? error.message : "Failed to load projects"}
      </p>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">All Projects</h1>
      <p className="mt-1 text-sm text-gray-600">
        Organize your research into focused workspaces.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <div className="flex gap-2">
          <PillButton active={filter === "all"} onClick={() => setFilter("all")}>
            All
          </PillButton>
          <PillButton active={filter === "starred"} onClick={() => setFilter("starred")}>
            Starred
          </PillButton>
        </div>
        <div className="relative min-w-[240px] flex-1">
          <input
            type="text"
            placeholder="Search by project name, topic, etc."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-3 pr-10 text-sm focus:border-brand-700 focus:outline-none focus:ring-1 focus:ring-brand-700"
          />
          <Search className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        </div>
        <Link
          to="/projects/new"
          className="flex items-center gap-2 rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700"
        >
          <Plus className="h-4 w-4" />
          New Project
        </Link>
      </div>

      {deleteProject.isError && (
        <p className="mt-4 text-sm text-red-600">
          {deleteProject.error instanceof Error
            ? deleteProject.error.message
            : "Failed to delete project"}
        </p>
      )}

      <div className="mt-8 grid grid-cols-2 gap-4">
        {filtered.map((project) => (
          <ProjectCard
            key={project.id}
            project={project}
            onDelete={(id) => deleteProject.mutate(id)}
            deleting={deleteProject.isPending && deleteProject.variables === project.id}
          />
        ))}
      </div>
    </div>
  );
}
