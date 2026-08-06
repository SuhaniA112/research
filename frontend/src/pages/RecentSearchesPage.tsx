import { Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listProjects } from "@/api/projects";
import {
  clearRecentSearches,
  deleteRecentSearch,
  listRecentSearches,
  useInvalidateSearchHistory,
} from "@/api/research";
import { getIconSizeClass, IconButton } from "@/components/ui/IconButton";
import { getFindSourcesPath } from "@/lib/sourcePaths";

export function RecentSearchesPage() {
  const invalidateSearchHistory = useInvalidateSearchHistory();
  const [defaultProjectId, setDefaultProjectId] = useState("1");
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    const [projects, searches] = await Promise.all([
      listProjects(),
      listRecentSearches(),
    ]);
    setDefaultProjectId(projects[0]?.id ?? "1");
    setRecentSearches(searches);
  }

  useEffect(() => {
    void refresh().finally(() => setLoading(false));
  }, []);

  async function handleDelete(query: string) {
    await deleteRecentSearch(query);
    setRecentSearches((prev) => prev.filter((item) => item !== query));
    invalidateSearchHistory();
  }

  async function handleClearAll() {
    const ok = window.confirm("Clear all recent searches?");
    if (!ok) return;
    await clearRecentSearches();
    setRecentSearches([]);
    invalidateSearchHistory();
  }

  if (loading) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  return (
    <div>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recent Searches</h1>
          <p className="mt-1 text-sm text-gray-600">
            Your search history across all projects.
          </p>
        </div>
        {recentSearches.length > 0 && (
          <button
            type="button"
            onClick={() => void handleClearAll()}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="mt-6 space-y-2">
        {recentSearches.length === 0 ? (
          <p className="text-sm text-gray-500">No recent searches yet.</p>
        ) : (
          recentSearches.map((search) => (
            <div
              key={search}
              className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 hover:bg-gray-50"
            >
              <Link
                to={getFindSourcesPath(defaultProjectId, search)}
                className="flex min-w-0 flex-1 items-center gap-2 truncate text-sm text-gray-700 hover:text-brand-700"
              >
                <span className="min-w-0 flex-1 truncate">{search}</span>
                <Search className="h-4 w-4 shrink-0 text-gray-400" />
              </Link>
              <IconButton
                size="md"
                title="Delete search"
                aria-label={`Delete search ${search}`}
                onClick={() => void handleDelete(search)}
                className="ml-1 shrink-0 text-gray-400 hover:bg-red-50 hover:text-red-600"
              >
                <Trash2 className={getIconSizeClass("md")} />
              </IconButton>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
