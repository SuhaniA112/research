import { Search } from "lucide-react";
import { Link } from "react-router-dom";

import { projects, recentSearches } from "@/data/mockData";
import { getFindSourcesPath } from "@/lib/sourcePaths";

export function RecentSearchesPage() {
  const defaultProjectId = projects[0]?.id ?? "1";

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900">Recent Searches</h1>
      <p className="mt-1 text-sm text-gray-600">Your search history across all projects.</p>

      <div className="mt-6 space-y-2">
        {recentSearches.map((search) => (
          <Link
            key={search}
            to={getFindSourcesPath(defaultProjectId, search)}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 hover:bg-gray-50"
          >
            <span className="text-sm text-gray-700">{search}</span>
            <Search className="h-4 w-4 text-gray-400" />
          </Link>
        ))}
      </div>
    </div>
  );
}
