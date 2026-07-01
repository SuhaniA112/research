import { useParams } from "react-router-dom";
import { Search } from "lucide-react";
import { Link } from "react-router-dom";

import { Breadcrumbs } from "@/components/layout/Breadcrumbs";
import { ProjectTabBar } from "@/components/layout/ProjectTabBar";
import { getProject } from "@/data/mockData";

interface ProjectLayoutHeaderProps {
  showTabs?: boolean;
  breadcrumbSuffix?: string;
}

export function ProjectLayoutHeader({
  showTabs = true,
  breadcrumbSuffix,
}: ProjectLayoutHeaderProps) {
  const { projectId } = useParams<{ projectId: string }>();
  const project = getProject(projectId ?? "");

  if (!project) return null;

  const breadcrumbItems: { label: string; to?: string }[] = [
    { label: "All Projects", to: "/projects" },
    { label: project.name, to: `/projects/${project.id}` },
  ];
  if (breadcrumbSuffix) {
    breadcrumbItems.push({ label: breadcrumbSuffix });
  }

  return (
    <>
      <Breadcrumbs items={breadcrumbItems} />
      <div className="mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
          <p className="mt-1 text-sm text-gray-500">
            Updated {project.updatedDaysAgo} Days Ago • {project.sourceCount} Sources
          </p>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-600">
            {project.description}
          </p>
        </div>
        <Link
          to={`/projects/${project.id}/find-sources`}
          className="flex items-center gap-2 rounded-lg bg-brand-100 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-200"
        >
          <Search className="h-4 w-4" />
          Find Sources
        </Link>
      </div>
      {showTabs && (
        <div className="mt-6">
          <ProjectTabBar />
        </div>
      )}
    </>
  );
}
