import { SourceActions } from "@/components/source/SourceActions";
import { getSourcePagePath } from "@/lib/sourcePaths";
import { Link } from "react-router-dom";

interface SourceListItemProps {
  title: string;
  relevance?: number;
  projectId?: string;
  sourceId?: string;
}

export function SourceListItem({ title, relevance, projectId, sourceId }: SourceListItemProps) {
  const canNavigate = Boolean(sourceId && projectId);

  return (
    <div className="relative flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 transition-colors hover:bg-gray-50">
      {canNavigate && (
        <Link
          to={getSourcePagePath(sourceId!, projectId)}
          className="absolute inset-0 rounded-lg"
          aria-label={`View ${title}`}
        />
      )}
      <span className="relative z-0 min-w-0 truncate pr-3 text-sm text-gray-900">
        {title}
        {relevance !== undefined && (
          <span className="text-gray-500"> • {relevance}% Relevant</span>
        )}
      </span>
      {sourceId && (
        <SourceActions
          sourceId={sourceId}
          projectId={projectId}
          size="md"
          className="relative z-10"
        />
      )}
    </div>
  );
}
