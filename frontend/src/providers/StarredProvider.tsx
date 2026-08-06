import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { listProjectsSync } from "@/api/projects";
import { listSourcesSync } from "@/api/sources";

interface StarredContextValue {
  isProjectStarred: (id: string) => boolean;
  isSourceStarred: (id: string) => boolean;
  toggleProjectStar: (id: string) => void;
  toggleSourceStar: (id: string) => void;
}

const StarredContext = createContext<StarredContextValue | null>(null);
const STARRED_STORAGE_KEY = "papersearcher_starred";

interface StarredStore {
  projects: Record<string, boolean>;
  sources: Record<string, boolean>;
}

function buildInitialStarred<T extends { id: string; starred?: boolean }>(items: T[]) {
  return Object.fromEntries(items.map((item) => [item.id, item.starred ?? false]));
}

function loadStarred(): StarredStore {
  const fromMocks: StarredStore = {
    projects: buildInitialStarred(listProjectsSync()),
    sources: buildInitialStarred(listSourcesSync()),
  };
  try {
    const raw = localStorage.getItem(STARRED_STORAGE_KEY);
    if (!raw) return fromMocks;
    const parsed = JSON.parse(raw) as Partial<StarredStore>;
    return {
      projects: {
        ...fromMocks.projects,
        ...(parsed.projects && typeof parsed.projects === "object"
          ? parsed.projects
          : {}),
      },
      sources: {
        ...fromMocks.sources,
        ...(parsed.sources && typeof parsed.sources === "object" ? parsed.sources : {}),
      },
    };
  } catch {
    return fromMocks;
  }
}

function persistStarred(store: StarredStore): void {
  localStorage.setItem(STARRED_STORAGE_KEY, JSON.stringify(store));
}

export function StarredProvider({ children }: { children: ReactNode }) {
  const [store, setStore] = useState<StarredStore>(() => loadStarred());

  const isProjectStarred = useCallback(
    (id: string) => store.projects[id] ?? false,
    [store.projects],
  );

  const isSourceStarred = useCallback(
    (id: string) => store.sources[id] ?? false,
    [store.sources],
  );

  const toggleProjectStar = useCallback((id: string) => {
    setStore((prev) => {
      const next: StarredStore = {
        ...prev,
        projects: { ...prev.projects, [id]: !prev.projects[id] },
      };
      persistStarred(next);
      return next;
    });
  }, []);

  const toggleSourceStar = useCallback((id: string) => {
    setStore((prev) => {
      const next: StarredStore = {
        ...prev,
        sources: { ...prev.sources, [id]: !prev.sources[id] },
      };
      persistStarred(next);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({
      isProjectStarred,
      isSourceStarred,
      toggleProjectStar,
      toggleSourceStar,
    }),
    [isProjectStarred, isSourceStarred, toggleProjectStar, toggleSourceStar],
  );

  return <StarredContext.Provider value={value}>{children}</StarredContext.Provider>;
}

export function useStarred() {
  const context = useContext(StarredContext);
  if (!context) {
    throw new Error("useStarred must be used within StarredProvider");
  }
  return context;
}
