import { getProjectSync, listProjectsSync } from "@/api/projects";
import { cacheSource } from "@/api/mappers";
import { getSourceSync } from "@/api/sources";
import type { Source } from "@/types";

export interface SourceBreadcrumbItem {
  label: string;
  to?: string;
}

export interface SourceNavigationState {
  breadcrumbs: SourceBreadcrumbItem[];
  /** Full source payload so detail pages work before/without DB persistence. */
  source?: Source;
}

export type SourceReferrer =
  | { type: "find-sources"; projectId: string }
  | { type: "saved-sources"; projectId: string }
  | { type: "mind-map"; projectId: string }
  | { type: "project-overview"; projectId: string }
  | { type: "hub"; projectId?: string }
  | { type: "continue"; projectId: string; breadcrumbs: SourceBreadcrumbItem[] };

export function encodeSourceId(sourceId: string): string {
  return encodeURIComponent(sourceId);
}

function getSourcePagePath(sourceId: string, projectId?: string): string {
  const resolvedProjectId = projectId ?? listProjectsSync()[0]?.id ?? "hub";
  return `/projects/${resolvedProjectId}/sources/${encodeSourceId(sourceId)}`;
}

function buildSourceBreadcrumbs(referrer: SourceReferrer): SourceBreadcrumbItem[] {
  switch (referrer.type) {
    case "continue":
      return referrer.breadcrumbs;
    case "hub":
      return [{ label: "Hub", to: "/hub" }];
    case "find-sources":
    case "saved-sources":
    case "mind-map":
    case "project-overview": {
      const project = getProjectSync(referrer.projectId);
      const items: SourceBreadcrumbItem[] = [
        { label: "All Projects", to: "/projects" },
        { label: project?.name ?? "Project", to: `/projects/${referrer.projectId}` },
      ];
      if (referrer.type === "find-sources") {
        items.push({
          label: "Find Sources",
          to: `/projects/${referrer.projectId}/find-sources`,
        });
      } else if (referrer.type === "saved-sources") {
        items.push({
          label: "Saved Sources",
          to: `/projects/${referrer.projectId}/saved`,
        });
      } else if (referrer.type === "mind-map") {
        items.push({
          label: "Mind Map",
          to: `/projects/${referrer.projectId}/mind-map`,
        });
      }
      return items;
    }
  }
}

export function getSourcePageLink(
  sourceId: string,
  referrer: SourceReferrer,
  source?: Source,
): { to: string; state: SourceNavigationState } {
  const projectId =
    referrer.type === "hub"
      ? (referrer.projectId ?? listProjectsSync()[0]?.id ?? "hub")
      : referrer.type === "continue"
        ? referrer.projectId
        : referrer.projectId;

  if (source) {
    cacheSource(source);
  }

  return {
    to: getSourcePagePath(sourceId, projectId),
    state: {
      breadcrumbs: buildSourceBreadcrumbs(referrer),
      source,
    },
  };
}

export function getDefaultSourceBreadcrumbs(projectId: string): SourceBreadcrumbItem[] {
  return buildSourceBreadcrumbs({ type: "project-overview", projectId });
}

export function getFindSourcesPath(projectId: string, query?: string): string {
  const base = `/projects/${projectId}/find-sources`;
  if (!query) return base;
  return `${base}?q=${encodeURIComponent(query)}`;
}

export function getPublicationUrl(sourceId: string): string {
  return getSourceSync(sourceId)?.publicationUrl ?? "#";
}
