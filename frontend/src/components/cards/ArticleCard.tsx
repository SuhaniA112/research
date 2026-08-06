import { Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listSourceNotes, type SourceNote } from "@/api/notes";
import { SourceActions } from "@/components/source/SourceActions";
import {
  getIconSizeClass,
  IconButton,
  IconButtonGroup,
} from "@/components/ui/IconButton";
import { StarButton } from "@/components/ui/StarButton";
import { Tag } from "@/components/ui/Tag";
import { getSourcePageLink, type SourceReferrer } from "@/lib/sourcePaths";
import { truncateWords } from "@/lib/text";
import { useStarred } from "@/providers/StarredProvider";
import type { Source } from "@/types";

interface SavedSourceCardProps {
  source: Source;
  projectId: string;
  sourceReferrer?: SourceReferrer;
  onRemove?: (sourceId: string) => void;
}

export function SavedSourceCard({
  source,
  projectId,
  sourceReferrer,
  onRemove,
}: SavedSourceCardProps) {
  const { isSourceStarred, toggleSourceStar } = useStarred();
  const starred = isSourceStarred(source.id);
  const sourceLink = getSourcePageLink(
    source.id,
    sourceReferrer ?? { type: "saved-sources", projectId },
    source,
  );
  const cardSummary = truncateWords(source.description, 50);
  const [notes, setNotes] = useState<SourceNote[]>([]);

  useEffect(() => {
    let cancelled = false;
    void listSourceNotes(source.id).then((next) => {
      if (!cancelled) setNotes(next);
    });
    return () => {
      cancelled = true;
    };
  }, [source.id]);

  return (
    <div className="flex flex-col rounded-xl border border-gray-200 bg-white transition-shadow hover:shadow-md">
      <div className="relative flex flex-1 flex-col p-5 pb-0">
        <div className="absolute right-5 top-5 z-10">
          <StarButton starred={starred} onToggle={() => toggleSourceStar(source.id)} />
        </div>

        <Link to={sourceLink.to} state={sourceLink.state} className="flex flex-1 flex-col pr-10">
          <div className="flex flex-wrap items-center gap-2">
            {source.topics.map((topic) => (
              <Tag key={topic}>{topic}</Tag>
            ))}
            <span className="text-xs text-gray-500">
              {source.source} • Published {source.publishedMonth} {source.publishedYear}
            </span>
          </div>

          <h3 className="mt-2 text-base font-semibold text-gray-900">{source.title}</h3>
          {cardSummary ? (
            <p className="mt-2 text-sm leading-relaxed text-gray-600">{cardSummary}</p>
          ) : null}

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
                {notes.length > 0 ? (
                  notes.slice(0, 3).map((note) => (
                    <div key={note.id} className="rounded-lg bg-surface-muted p-3 text-sm">
                      <p className="text-gray-700">{truncateWords(note.text, 30)}</p>
                      <p className="mt-1 text-left text-xs text-gray-400">
                        Written on {note.date}
                      </p>
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
        </Link>
      </div>

      <div className="flex items-center justify-between px-5 pb-5 pt-4">
        {source.savedOn && <span className="text-xs text-gray-500">Saved on {source.savedOn}</span>}
        <IconButtonGroup className="ml-auto">
          <IconButton
            size="md"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onRemove?.(source.id);
            }}
            title="Remove from project"
            aria-label="Remove from project"
            className="text-gray-400 hover:bg-red-50 hover:text-red-600"
          >
            <Trash2 className={getIconSizeClass("md")} />
          </IconButton>
          <SourceActions sourceId={source.id} projectId={projectId} size="md" />
        </IconButtonGroup>
      </div>
    </div>
  );
}
