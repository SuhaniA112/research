import { Bookmark, Check, ExternalLink } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  getIconSizeClass,
  IconButton,
  IconButtonGroup,
  IconLink,
  type IconControlSize,
} from "@/components/ui/IconButton";
import { projects } from "@/data/mockData";
import { getPublicationUrl } from "@/lib/sourcePaths";

interface SaveToProjectButtonProps {
  sourceId: string;
  size?: IconControlSize;
  className?: string;
}

export function SaveToProjectButton({
  sourceId: _sourceId,
  size = "md",
  className = "",
}: SaveToProjectButtonProps) {
  const [open, setOpen] = useState(false);
  const [savedProjectId, setSavedProjectId] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const iconClass = getIconSizeClass(size);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  return (
    <div ref={ref} className={`relative inline-flex ${className}`}>
      <IconButton
        size={size}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        title="Save to project"
        aria-label="Save to project"
      >
        <Bookmark className={`${iconClass} ${savedProjectId ? "fill-brand-700" : ""}`} />
      </IconButton>
      {open && (
        <div className="absolute right-0 top-full z-20 mt-1 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
          <p className="px-3 py-2 text-xs font-semibold text-gray-500">Save to project</p>
          {projects.map((project) => {
            const isSaved = savedProjectId === project.id;
            return (
              <button
                key={project.id}
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setSavedProjectId(project.id);
                  setOpen(false);
                }}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
              >
                <span className="truncate">{project.name}</span>
                {isSaved && <Check className="h-4 w-4 shrink-0 text-metric-green" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

interface PublicationLinkProps {
  sourceId: string;
  size?: IconControlSize;
  className?: string;
}

export function PublicationLink({ sourceId, size = "md", className = "" }: PublicationLinkProps) {
  return (
    <IconLink
      href={getPublicationUrl(sourceId)}
      target="_blank"
      rel="noopener noreferrer"
      size={size}
      onClick={(e) => e.stopPropagation()}
      className={className}
      title="Open publication"
      aria-label="Open publication website"
    >
      <ExternalLink className={getIconSizeClass(size)} />
    </IconLink>
  );
}

interface SourceActionsProps {
  sourceId: string;
  projectId?: string;
  size?: IconControlSize;
  className?: string;
}

export function SourceActions({
  sourceId,
  size = "md",
  className = "",
}: SourceActionsProps) {
  return (
    <IconButtonGroup
      className={className}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <SaveToProjectButton sourceId={sourceId} size={size} />
      <PublicationLink sourceId={sourceId} size={size} />
    </IconButtonGroup>
  );
}
