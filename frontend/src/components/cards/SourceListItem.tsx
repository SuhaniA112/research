import { SourceActions } from "@/components/source/SourceActions";
import { getSourcePageLink, type SourceReferrer } from "@/lib/sourcePaths";
import { Link } from "react-router-dom";

interface SourceListItemProps {
  title: string;
  relevance?: number;
  projectId?: string;
  sourceId?: string;
  sourceReferrer?: SourceReferrer;
}

export function SourceListItem({
  title,
  relevance,
  projectId,
  sourceId,
  sourceReferrer,
}: SourceListItemProps) {
  const canNavigate = Boolean(sourceId && projectId && sourceReferrer);
  const sourceLink =
    canNavigate && sourceReferrer
      ? getSourcePageLink(sourceId!, sourceReferrer)
      : null;

  return (
    <div className="relative flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 transition-colors hover:bg-gray-50">
      {sourceLink && (
        <Link
          to={sourceLink}
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
