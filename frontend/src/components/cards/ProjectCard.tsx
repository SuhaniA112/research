import { Link } from "react-router-dom";

import { StarButton } from "@/components/ui/StarButton";
import { Tag } from "@/components/ui/Tag";
import { useStarred } from "@/providers/StarredProvider";
import type { Project } from "@/types";

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  const { isProjectStarred, toggleProjectStar } = useStarred();
  const starred = isProjectStarred(project.id);

  return (
    <Link
      to={`/projects/${project.id}`}
      className="flex flex-col rounded-xl border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-gray-900">{project.name}</h3>
        <div className="relative z-10 shrink-0">
          <StarButton starred={starred} onToggle={() => toggleProjectStar(project.id)} />
        </div>
      </div>
      <p className="mt-2 line-clamp-3 text-sm text-gray-600">{project.description}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {project.topics.map((topic) => (
          <Tag key={topic}>{topic}</Tag>
        ))}
        <Tag variant="green">{project.sourceCount} Sources</Tag>
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3 text-xs text-gray-500">
        <span>{project.sourceCount} Sources</span>
        <span>Updated {project.updatedDaysAgo} Days Ago</span>
      </div>
    </Link>
  );
}
