import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { projects, sources } from "@/data/mockData";

interface StarredContextValue {
  isProjectStarred: (id: string) => boolean;
  isSourceStarred: (id: string) => boolean;
  toggleProjectStar: (id: string) => void;
  toggleSourceStar: (id: string) => void;
}

const StarredContext = createContext<StarredContextValue | null>(null);

function buildInitialStarred<T extends { id: string; starred?: boolean }>(items: T[]) {
  return Object.fromEntries(items.map((item) => [item.id, item.starred ?? false]));
}

export function StarredProvider({ children }: { children: ReactNode }) {
  const [starredProjects, setStarredProjects] = useState<Record<string, boolean>>(() =>
    buildInitialStarred(projects),
  );
  const [starredSources, setStarredSources] = useState<Record<string, boolean>>(() =>
    buildInitialStarred(sources),
  );

  const isProjectStarred = useCallback(
    (id: string) => starredProjects[id] ?? false,
    [starredProjects],
  );

  const isSourceStarred = useCallback(
    (id: string) => starredSources[id] ?? false,
    [starredSources],
  );

  const toggleProjectStar = useCallback((id: string) => {
    setStarredProjects((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const toggleSourceStar = useCallback((id: string) => {
    setStarredSources((prev) => ({ ...prev, [id]: !prev[id] }));
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
