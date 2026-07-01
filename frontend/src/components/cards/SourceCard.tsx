import type { Source } from "@/types";
import { SourcePreviewCard } from "@/components/cards/SourcePreviewCard";

interface SourceCardProps {
  source: Source;
  projectId?: string;
  showMetrics?: boolean;
}

export function SourceCard({ source, projectId, showMetrics = true }: SourceCardProps) {
  if (!showMetrics) {
    return <SourcePreviewCard source={source} projectId={projectId} variant="compact" />;
  }
  return <SourcePreviewCard source={source} projectId={projectId} variant="standard" />;
}
