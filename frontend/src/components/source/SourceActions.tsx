import { Bookmark, Check, ExternalLink } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";

import { listProjects } from "@/api/projects";
import { listSavedSources, saveSource, unsaveSource } from "@/api/sources";
import {
  getIconSizeClass,
  IconButton,
  IconButtonGroup,
  IconLink,
  type IconControlSize,
} from "@/components/ui/IconButton";
import { getPublicationUrl } from "@/lib/sourcePaths";
import type { Project } from "@/types";

interface SaveToProjectButtonProps {
  sourceId: string;
  size?: IconControlSize;
  className?: string;
}

export function SaveToProjectButton({
  sourceId,
  size = "md",
  className = "",
}: SaveToProjectButtonProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [savedProjectIds, setSavedProjectIds] = useState<Set<string>>(() => new Set());
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const ref = useRef<HTMLDivElement>(null);
  const iconClass = getIconSizeClass(size);
  const hasSavedProjects = savedProjectIds.size > 0;

  useEffect(() => {
    void listProjects().then(async (nextProjects) => {
      setProjects(nextProjects);
      const savedIds = new Set<string>();
      await Promise.all(
        nextProjects.map(async (project) => {
          const saved = await listSavedSources(project.id);
          if (saved.some((s) => s.id === sourceId)) {
            savedIds.add(project.id);
          }
        }),
      );
      setSavedProjectIds(savedIds);
    });
  }, [sourceId]);

  function updateMenuPosition() {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    setMenuPosition({
      top: rect.bottom + 4,
      left: rect.right - 224,
    });
  }

  async function toggleProject(projectId: string) {
    const isSaved = savedProjectIds.has(projectId);
    if (isSaved) {
      await unsaveSource(projectId, sourceId);
      setSavedProjectIds((prev) => {
        const next = new Set(prev);
        next.delete(projectId);
        return next;
      });
    } else {
      await saveSource(projectId, sourceId);
      setSavedProjectIds((prev) => new Set(prev).add(projectId));
    }
    await queryClient.invalidateQueries({ queryKey: ["projects"] });
    const refreshed = await listProjects();
    setProjects(refreshed);
  }

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        const target = e.target as HTMLElement;
        if (!target.closest("[data-save-to-project-menu]")) {
          setOpen(false);
        }
      }
    }
    if (open) {
      updateMenuPosition();
      document.addEventListener("mousedown", handleClickOutside);
      window.addEventListener("resize", updateMenuPosition);
      window.addEventListener("scroll", updateMenuPosition, true);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("resize", updateMenuPosition);
      window.removeEventListener("scroll", updateMenuPosition, true);
    };
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
        <Bookmark className={`${iconClass} ${hasSavedProjects ? "fill-brand-700" : ""}`} />
      </IconButton>
      {open &&
        createPortal(
          <div
            data-save-to-project-menu
            className="fixed z-50 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
            style={{ top: menuPosition.top, left: menuPosition.left }}
          >
            <p className="px-3 py-2 text-xs font-semibold text-gray-500">Save to project</p>
            {projects.map((project) => {
              const isSaved = savedProjectIds.has(project.id);
              return (
                <button
                  key={project.id}
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    void toggleProject(project.id);
                  }}
                  className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50 ${
                    isSaved ? "text-gray-900" : "text-gray-700"
                  }`}
                >
                  <span className="truncate">{project.name}</span>
                  {isSaved && <Check className="h-4 w-4 shrink-0 text-metrics" />}
                </button>
              );
            })}
          </div>,
          document.body,
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
