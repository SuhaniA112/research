import { Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { StarButton } from "@/components/ui/StarButton";
import { Tag } from "@/components/ui/Tag";
import { getIconSizeClass, IconButton } from "@/components/ui/IconButton";
import { useStarred } from "@/providers/StarredProvider";
import type { Project } from "@/types";

interface ProjectCardProps {
  project: Project;
  onDelete?: (projectId: string) => void;
  deleting?: boolean;
}

export function ProjectCard({ project, onDelete, deleting = false }: ProjectCardProps) {
  const { isProjectStarred, toggleProjectStar } = useStarred();
  const starred = isProjectStarred(project.id);

  return (
    <div className="relative flex flex-col rounded-xl border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md">
      <Link to={`/projects/${project.id}`} className="absolute inset-0 rounded-xl" aria-label={project.name} />
      <div className="relative z-10 flex items-start justify-between gap-2">
        <Link to={`/projects/${project.id}`} className="min-w-0">
          <h3 className="font-semibold text-gray-900 hover:text-brand-700">{project.name}</h3>
        </Link>
        <div className="flex shrink-0 items-center gap-1">
          <StarButton starred={starred} onToggle={() => toggleProjectStar(project.id)} />
          {onDelete && (
            <IconButton
              size="md"
              title="Delete project"
              aria-label={`Delete ${project.name}`}
              disabled={deleting}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const ok = window.confirm(
                  `Delete project “${project.name}”? Saved papers for this project will be unlinked.`,
                );
                if (ok) onDelete(project.id);
              }}
              className="text-gray-400 hover:bg-red-50 hover:text-red-600"
            >
              <Trash2 className={getIconSizeClass("md")} />
            </IconButton>
          )}
        </div>
      </div>
      <p className="relative z-0 mt-2 line-clamp-3 text-sm text-gray-600">{project.description}</p>
      <div className="relative z-0 mt-3 flex flex-wrap gap-1.5">
        {project.topics.map((topic) => (
          <Tag key={topic}>{topic}</Tag>
        ))}
        <Tag variant="metrics">
          {project.sourceCount} {project.sourceCount === 1 ? "Source" : "Sources"}
        </Tag>
      </div>
      <div className="relative z-0 mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs text-gray-500">
        <span>
          {project.sourceCount} {project.sourceCount === 1 ? "Source" : "Sources"}
        </span>
        <span>
          {project.updatedDaysAgo === 0
            ? "Updated today"
            : project.updatedDaysAgo === 1
              ? "Updated 1 day ago"
              : `Updated ${project.updatedDaysAgo} days ago`}
        </span>
      </div>
    </div>
  );
}
