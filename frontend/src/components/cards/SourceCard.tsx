import type { Source } from "@/types";
import { SourcePreviewCard } from "@/components/cards/SourcePreviewCard";
import type { SourceReferrer } from "@/lib/sourcePaths";

interface SourceCardProps {
  source: Source;
  projectId?: string;
  sourceReferrer?: SourceReferrer;
  showMetrics?: boolean;
}

export function SourceCard({
  source,
  projectId,
  sourceReferrer,
  showMetrics = true,
}: SourceCardProps) {
  if (!showMetrics) {
    return (
      <SourcePreviewCard
        source={source}
        projectId={projectId}
        sourceReferrer={sourceReferrer}
        variant="compact"
      />
    );
  }
  return (
    <SourcePreviewCard
      source={source}
      projectId={projectId}
      sourceReferrer={sourceReferrer}
      variant="standard"
    />
  );
}
