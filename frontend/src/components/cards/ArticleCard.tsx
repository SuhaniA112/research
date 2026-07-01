import { Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

import { SourceActions } from "@/components/source/SourceActions";
import {
  getIconSizeClass,
  IconButton,
  IconButtonGroup,
} from "@/components/ui/IconButton";
import { StarButton } from "@/components/ui/StarButton";
import { Tag } from "@/components/ui/Tag";
import { getSourcePageLink, type SourceReferrer } from "@/lib/sourcePaths";
import { useStarred } from "@/providers/StarredProvider";
import type { Source } from "@/types";

interface SavedSourceCardProps {
  source: Source;
  projectId: string;
  sourceReferrer?: SourceReferrer;
}

export function SavedSourceCard({
  source,
  projectId,
  sourceReferrer,
}: SavedSourceCardProps) {
  const { isSourceStarred, toggleSourceStar } = useStarred();
  const starred = isSourceStarred(source.id);
  const sourceLink = getSourcePageLink(
    source.id,
    sourceReferrer ?? { type: "saved-sources", projectId },
  );

  return (
    <div className="relative rounded-xl border border-gray-200 bg-white transition-shadow hover:shadow-md">
      <Link to={sourceLink} className="absolute inset-0 rounded-xl" aria-label={`View ${source.title}`} />

      <div className="relative z-0 p-5 pb-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2 pr-2">
            {source.topics.map((topic) => (
              <Tag key={topic}>{topic}</Tag>
            ))}
            <span className="text-xs text-gray-500">
              {source.source} • Published {source.publishedMonth} {source.publishedYear}
            </span>
          </div>
          <div className="relative z-10 shrink-0">
            <StarButton starred={starred} onToggle={() => toggleSourceStar(source.id)} />
          </div>
        </div>

        <h3 className="mt-2 text-base font-semibold text-gray-900">{source.title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-gray-600">{source.description}</p>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-semibold tracking-wide text-gray-500">KEY FINDINGS</p>
            <div className="mt-2 rounded-lg border border-gray-200 bg-surface-muted p-3">
              <ul className="space-y-2 text-sm text-gray-700">
                {source.keyFindings.map((finding) => (
                  <li key={finding.text} className="list-inside list-disc">
                    {finding.text}{" "}
                    <span className="font-semibold">Found in {finding.section}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold tracking-wide text-gray-500">NOTES</p>
            <div className="mt-2 space-y-2">
              {(source.notes ?? []).length > 0 ? (
                source.notes!.map((note) => (
                  <div key={note.id} className="rounded-lg bg-surface-muted p-3 text-sm">
                    <p className="text-gray-700">{note.text}</p>
                    <p className="mt-1 text-right text-xs text-gray-400">Written on {note.date}</p>
                  </div>
                ))
              ) : (
                <div className="rounded-lg bg-surface-muted p-3 text-sm text-gray-400">
                  No notes yet
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-10 flex items-center justify-between px-5 pb-5 pt-4">
        {source.savedOn && <span className="text-xs text-gray-500">Saved on {source.savedOn}</span>}
        <IconButtonGroup className="ml-auto">
          <IconButton
            size="md"
            onClick={(e) => e.stopPropagation()}
            title="Remove from project"
            aria-label="Remove from project"
          >
            <Trash2 className={getIconSizeClass("md")} />
          </IconButton>
          <SourceActions sourceId={source.id} projectId={projectId} size="md" />
        </IconButtonGroup>
      </div>
    </div>
  );
}
