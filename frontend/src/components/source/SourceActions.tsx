import { Bookmark, Check, ExternalLink, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";

import { listProjects } from "@/api/projects";
import {
  getSourceSync,
  listSavedSources,
  saveSource,
  sourcesMatch,
  unsaveSource,
} from "@/api/sources";
import {
  getIconSizeClass,
  IconButton,
  IconButtonGroup,
  IconLink,
  type IconControlSize,
} from "@/components/ui/IconButton";
import { getPublicationUrl } from "@/lib/sourcePaths";
import type { Project, Source } from "@/types";

interface SaveToProjectButtonProps {
  sourceId: string;
  source?: Source;
  /** When set, the bookmark fills only if saved to this project. */
  projectId?: string;
  size?: IconControlSize;
  className?: string;
}

export function SaveToProjectButton({
  sourceId,
  source: sourceProp,
  projectId: contextProjectId,
  size = "md",
  className = "",
}: SaveToProjectButtonProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [savedProjectIds, setSavedProjectIds] = useState<Set<string>>(() => new Set());
  const [pendingProjectIds, setPendingProjectIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [error, setError] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<Source | undefined>(
    () => sourceProp ?? getSourceSync(sourceId),
  );
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const ref = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const iconClass = getIconSizeClass(size);
  const bookmarkFilled = contextProjectId
    ? savedProjectIds.has(contextProjectId)
    : savedProjectIds.size > 0;
  const sourceKey = sourceProp?.externalId || sourceProp?.id || sourceId;
  const MENU_WIDTH = 224;

  useEffect(() => {
    setActiveSource(sourceProp ?? getSourceSync(sourceId));
  }, [sourceId, sourceKey]);

  useEffect(() => {
    let cancelled = false;
    void listProjects().then(async (nextProjects) => {
      if (cancelled) return;
      setProjects(nextProjects);
      const probe =
        activeSource ??
        sourceProp ??
        getSourceSync(sourceId) ??
        ({ id: sourceId } as Source);
      const savedIds = new Set<string>();
      await Promise.all(
        nextProjects.map(async (project) => {
          const saved = await listSavedSources(project.id);
          if (saved.some((s) => sourcesMatch(s, probe))) {
            savedIds.add(project.id);
          }
        }),
      );
      if (!cancelled) setSavedProjectIds(savedIds);
    });
    return () => {
      cancelled = true;
    };
  }, [sourceId, sourceKey, open]);

  function updateMenuPosition() {
    if (!ref.current) return;
    const trigger = ref.current.getBoundingClientRect();
    const estimatedHeight = Math.min(
      320,
      44 + (error ? 28 : 0) + Math.max(projects.length, 1) * 36,
    );
    const menuHeight = menuRef.current?.offsetHeight || estimatedHeight;
    const gap = 4;
    const padding = 8;
    const spaceBelow = window.innerHeight - trigger.bottom - padding;
    const spaceAbove = trigger.top - padding;
    const openUpward = spaceBelow < menuHeight && spaceAbove > spaceBelow;

    let top = openUpward
      ? trigger.top - menuHeight - gap
      : trigger.bottom + gap;
    top = Math.max(
      padding,
      Math.min(top, window.innerHeight - menuHeight - padding),
    );

    let left = trigger.right - MENU_WIDTH;
    left = Math.max(
      padding,
      Math.min(left, window.innerWidth - MENU_WIDTH - padding),
    );

    setMenuPosition({ top, left });
  }

  async function toggleProject(projectId: string) {
    if (pendingProjectIds.has(projectId)) return;

    const isSaved = savedProjectIds.has(projectId);
    const current = activeSource ?? sourceProp ?? getSourceSync(sourceId);
    if (!current && !isSaved) {
      setError("Source is not available to save yet.");
      return;
    }

    setError(null);
    setPendingProjectIds((prev) => new Set(prev).add(projectId));
    setSavedProjectIds((prev) => {
      const next = new Set(prev);
      if (isSaved) next.delete(projectId);
      else next.add(projectId);
      return next;
    });

    try {
      if (isSaved) {
        await unsaveSource(projectId, current?.id ?? sourceId);
      } else {
        const saved = await saveSource(projectId, sourceId, current);
        setActiveSource(saved);
      }
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      const refreshed = await listProjects();
      setProjects(refreshed);
    } catch (err) {
      setSavedProjectIds((prev) => {
        const next = new Set(prev);
        if (isSaved) next.add(projectId);
        else next.delete(projectId);
        return next;
      });
      const message =
        err instanceof Error ? err.message : "Could not update project save.";
      setError(message);
      console.error("Save to project failed", err);
    } finally {
      setPendingProjectIds((prev) => {
        const next = new Set(prev);
        next.delete(projectId);
        return next;
      });
    }
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
      // Re-measure after paint once the menu has real height.
      const raf = window.requestAnimationFrame(() => updateMenuPosition());
      document.addEventListener("mousedown", handleClickOutside);
      window.addEventListener("resize", updateMenuPosition);
      window.addEventListener("scroll", updateMenuPosition, true);
      return () => {
        window.cancelAnimationFrame(raf);
        document.removeEventListener("mousedown", handleClickOutside);
        window.removeEventListener("resize", updateMenuPosition);
        window.removeEventListener("scroll", updateMenuPosition, true);
      };
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("resize", updateMenuPosition);
      window.removeEventListener("scroll", updateMenuPosition, true);
    };
  }, [open, projects.length, error]);

  return (
    <div ref={ref} className={`relative inline-flex ${className}`}>
      <IconButton
        size={size}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setError(null);
          setOpen((v) => !v);
        }}
        title="Save to projects"
        aria-label="Save to projects"
      >
        <Bookmark className={`${iconClass} ${bookmarkFilled ? "fill-brand-700" : ""}`} />
      </IconButton>
      {open &&
        createPortal(
          <div
            ref={menuRef}
            data-save-to-project-menu
            className="fixed z-50 max-h-[min(320px,calc(100vh-16px))] w-56 overflow-y-auto rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
            style={{ top: menuPosition.top, left: menuPosition.left }}
          >
            <p className="px-3 py-2 text-xs font-semibold text-gray-500">
              Save to projects
            </p>
            {error ? (
              <p className="px-3 pb-2 text-[11px] leading-snug text-red-600">{error}</p>
            ) : null}
            {projects.length === 0 ? (
              <p className="px-3 py-2 text-sm text-gray-500">No projects yet.</p>
            ) : (
              projects.map((project) => {
                const isSaved = savedProjectIds.has(project.id);
                const isPending = pendingProjectIds.has(project.id);
                return (
                  <button
                    key={project.id}
                    type="button"
                    disabled={isPending}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      void toggleProject(project.id);
                    }}
                    className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-gray-50 disabled:opacity-60 ${
                      isSaved ? "text-gray-900" : "text-gray-700"
                    }`}
                  >
                    <span className="truncate">{project.name}</span>
                    {isPending ? (
                      <Loader2 className="h-4 w-4 shrink-0 animate-spin text-gray-400" />
                    ) : isSaved ? (
                      <Check className="h-4 w-4 shrink-0 text-metrics" />
                    ) : null}
                  </button>
                );
              })
            )}
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
  sourceId?: string;
  source?: Source;
  projectId?: string;
  size?: IconControlSize;
  className?: string;
}

export function SourceActions({
  sourceId,
  source,
  projectId,
  size = "md",
  className = "",
}: SourceActionsProps) {
  const id = source?.id ?? sourceId;
  if (!id) return null;
  return (
    <IconButtonGroup
      className={className}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <SaveToProjectButton
        sourceId={id}
        source={source}
        projectId={projectId}
        size={size}
      />
      <PublicationLink sourceId={id} size={size} />
    </IconButtonGroup>
  );
}
