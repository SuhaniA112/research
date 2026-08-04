/**
 * Backend today:
 * GET    /api/v1/projects
 * GET    /api/v1/projects/:id
 * POST   /api/v1/projects  { name, description? }
 * DELETE /api/v1/projects/:id
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { mockStore } from "@/api/mocks/store";
import { env } from "@/config/env";
import { apiClient } from "@/lib/axios";
import type { Project, ReadingLevel } from "@/types";

export interface CreateProjectInput {
  name: string;
  description: string;
  topics: string[];
  keywords: string[];
  readingLevel: ReadingLevel;
}

interface BackendProject {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  source_count?: number;
  topics?: string[];
}

function formatUpdatedDaysAgo(updatedAt: string): number {
  const updated = new Date(updatedAt).getTime();
  if (Number.isNaN(updated)) return 0;
  return Math.max(0, Math.floor((Date.now() - updated) / 86_400_000));
}

function mapBackendProject(p: BackendProject): Project {
  return cacheProject({
    id: p.id,
    name: p.name,
    description: p.description ?? "",
    topics: p.topics ?? [],
    sourceCount: p.source_count ?? 0,
    updatedDaysAgo: formatUpdatedDaysAgo(p.updated_at),
    starred: false,
  });
}

const projectCache = new Map<string, Project>();

function cacheProject(project: Project): Project {
  projectCache.set(project.id, project);
  return project;
}

/** Sync lookup for breadcrumbs / path helpers. */
export function getProjectSync(projectId: string): Project | undefined {
  return projectCache.get(projectId) ?? mockStore.projects.find((p) => p.id === projectId);
}

export function listProjectsSync(): Project[] {
  if (projectCache.size > 0) {
    return [...projectCache.values()];
  }
  return mockStore.projects;
}

export async function listProjects(): Promise<Project[]> {
  if (env.useMocks) {
    return mockStore.projects.map(cacheProject);
  }
  const { data } = await apiClient.get<BackendProject[]>("/api/v1/projects");
  return data.map(mapBackendProject);
}

export async function getProject(projectId: string): Promise<Project | undefined> {
  if (env.useMocks) {
    const project = getProjectSync(projectId);
    return project ? cacheProject(project) : undefined;
  }
  const { data } = await apiClient.get<BackendProject>(
    `/api/v1/projects/${projectId}`,
  );
  return mapBackendProject(data);
}

export async function createProject(input: CreateProjectInput): Promise<Project> {
  if (env.useMocks) {
    const project: Project = {
      id: String(Date.now()),
      name: input.name,
      description: input.description,
      topics: input.topics,
      sourceCount: 0,
      updatedDaysAgo: 0,
      starred: false,
    };
    mockStore.projects = [project, ...mockStore.projects];
    mockStore.recentProjectSearches[project.id] = [];
    return cacheProject(project);
  }
  const { data } = await apiClient.post<BackendProject>("/api/v1/projects", {
    name: input.name,
    description: input.description || null,
  });
  return mapBackendProject(data);
}

export async function deleteProject(projectId: string): Promise<void> {
  if (env.useMocks) {
    mockStore.projects = mockStore.projects.filter((p) => p.id !== projectId);
    delete mockStore.recentProjectSearches[projectId];
  } else {
    await apiClient.delete(`/api/v1/projects/${projectId}`);
    delete mockStore.recentProjectSearches[projectId];
  }
  projectCache.delete(projectId);
  localStorage.setItem(
    "papersearcher_search_history",
    JSON.stringify({
      recentSearches: mockStore.recentSearches,
      recentProjectSearches: mockStore.recentProjectSearches,
    }),
  );
}

export function useProjects(): UseQueryResult<Project[], Error> {
  return useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });
}

export function useDeleteProject(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteProject,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
