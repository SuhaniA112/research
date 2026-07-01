import { getSource, projects } from "@/data/mockData";

export function getSourcePagePath(sourceId: string, projectId?: string): string {
  const resolvedProjectId = projectId ?? projects[0]?.id ?? "1";
  return `/projects/${resolvedProjectId}/sources/${sourceId}`;
}

export function getFindSourcesPath(projectId: string, query?: string): string {
  const base = `/projects/${projectId}/find-sources`;
  if (!query) return base;
  return `${base}?q=${encodeURIComponent(query)}`;
}

export function getPublicationUrl(sourceId: string): string {
  return getSource(sourceId)?.publicationUrl ?? "#";
}
