import { Pencil, Plus, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";

import {
  addSourceNote,
  deleteSourceNote,
  listSourceNotes,
  updateSourceNote,
  type SourceNote,
} from "@/api/notes";
import { getProject } from "@/api/projects";
import {
  getSource,
  getSummary,
  listCitingSources,
  listRelatedSources,
} from "@/api/sources";
import { SourceListItem } from "@/components/cards/SourceListItem";
import { Breadcrumbs } from "@/components/layout/Breadcrumbs";
import { SaveToProjectButton, PublicationLink } from "@/components/source/SourceActions";
import { getIconSizeClass, IconButton, IconButtonGroup } from "@/components/ui/IconButton";
import { SourceMetricsPanel } from "@/components/source/SourceMetricsPanel";
import { PillButton } from "@/components/ui/PillButton";
import { Tag } from "@/components/ui/Tag";
import {
  getDefaultSourceBreadcrumbs,
  type SourceNavigationState,
} from "@/lib/sourcePaths";
import type { Project, Source, SummaryLevel } from "@/types";

export function SourceDetailPage() {
  const { projectId, sourceId } = useParams<{ projectId: string; sourceId: string }>();
  const location = useLocation();
  const [project, setProject] = useState<Project | null | undefined>(undefined);
  const [source, setSource] = useState<Source | null | undefined>(undefined);
  const [summaryLevel, setSummaryLevel] = useState<SummaryLevel>("general");
  const [summaryText, setSummaryText] = useState("");
  const [relatedPapers, setRelatedPapers] = useState<Source[]>([]);
  const [citedSources, setCitedSources] = useState<Source[]>([]);
  const [notes, setNotes] = useState<SourceNote[]>([]);
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  useEffect(() => {
    if (!projectId || !sourceId) {
      setProject(null);
      setSource(null);
      return;
    }
    void getProject(projectId).then((p) => setProject(p ?? null));
    void getSource(sourceId).then((s) => setSource(s ?? null));
    void listRelatedSources(sourceId).then(setRelatedPapers);
    void listCitingSources(sourceId).then(setCitedSources);
    void listSourceNotes(sourceId).then(setNotes);
    setDraft("");
    setEditingId(null);
  }, [projectId, sourceId]);

  useEffect(() => {
    if (!sourceId) return;
    void getSummary(sourceId, summaryLevel).then(setSummaryText);
  }, [sourceId, summaryLevel]);

  async function handleAddNote() {
    if (!sourceId || !draft.trim()) return;
    const note = await addSourceNote(sourceId, draft);
    setNotes((prev) => [note, ...prev]);
    setDraft("");
  }

  async function handleSaveEdit(noteId: string) {
    if (!sourceId) return;
    const updated = await updateSourceNote(sourceId, noteId, editText);
    if (updated) {
      setNotes((prev) => prev.map((n) => (n.id === noteId ? updated : n)));
    } else {
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    }
    setEditingId(null);
    setEditText("");
  }

  async function handleDeleteNote(noteId: string) {
    if (!sourceId) return;
    await deleteSourceNote(sourceId, noteId);
    setNotes((prev) => prev.filter((n) => n.id !== noteId));
    if (editingId === noteId) {
      setEditingId(null);
      setEditText("");
    }
  }

  if (project === undefined || source === undefined) {
    return <p className="text-sm text-gray-500">Loading…</p>;
  }

  if (!project || !source) {
    return <p className="text-gray-500">Source not found.</p>;
  }

  const navigationState = location.state as SourceNavigationState | null;
  const parentBreadcrumbs = (
    navigationState?.breadcrumbs ?? getDefaultSourceBreadcrumbs(project.id)
  ).map((item) =>
    item.to === `/projects/${project.id}` ? { ...item, label: project.name } : item,
  );
  const breadcrumbItems = [...parentBreadcrumbs, { label: source.title }];
  const relatedSourceReferrer = {
    type: "continue" as const,
    projectId: project.id,
    breadcrumbs: [
      ...parentBreadcrumbs,
      {
        label: source.title,
        to: `/projects/${project.id}/sources/${source.id}`,
      },
    ],
  };

  return (
    <div>
      <Breadcrumbs items={breadcrumbItems} />

      <div className="mt-4 border-b border-gray-200 pb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{source.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {source.topics.map((t) => (
                <Tag key={t}>{t}</Tag>
              ))}
              <span className="text-sm text-gray-500">
                {source.source} • Published {source.publishedMonth} {source.publishedYear}
              </span>
            </div>
            <p className="mt-2 text-sm text-gray-600">
              Author(s): {source.authors.join(", ")}
            </p>
          </div>
          <IconButtonGroup>
            <SaveToProjectButton sourceId={source.id} size="lg" />
            <PublicationLink sourceId={source.id} size="lg" />
          </IconButtonGroup>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-3 gap-8">
        <div className="col-span-2 space-y-6">
          <div>
            <p className="text-xs font-semibold tracking-wide text-gray-500">SUMMARY LEVEL:</p>
            <div className="mt-2 flex gap-2">
              <PillButton
                active={summaryLevel === "general"}
                onClick={() => setSummaryLevel("general")}
              >
                General
              </PillButton>
              <PillButton
                active={summaryLevel === "graduate"}
                onClick={() => setSummaryLevel("graduate")}
              >
                Graduate
              </PillButton>
              <PillButton
                active={summaryLevel === "expert"}
                onClick={() => setSummaryLevel("expert")}
              >
                Expert
              </PillButton>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-gray-700">
              {summaryText || source.description || "No summary available yet."}
            </p>
            {summaryText || source.description ? (
              <span className="mt-3 flex items-center gap-1 text-xs text-brand-600">
                <Sparkles className="h-3.5 w-3.5" />
                AI Generated Description
              </span>
            ) : null}
          </div>

          <div className="rounded-xl border border-gray-200 p-4">
            <p className="text-xs font-semibold tracking-wide text-gray-500">KEY FINDINGS</p>
            {source.keyFindings.length > 0 ? (
              <ul className="mt-3 space-y-2 text-sm text-gray-700">
                {source.keyFindings.map((f) => (
                  <li key={f.text} className="list-inside list-disc">
                    {f.text} <span className="font-semibold">Found in {f.section}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-gray-500">No key findings extracted yet.</p>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold tracking-wide text-gray-500">NOTES</p>
              <IconButton
                size="md"
                title="Add note"
                aria-label="Add note"
                onClick={() => void handleAddNote()}
                disabled={!draft.trim()}
              >
                <Plus className={getIconSizeClass("md")} />
              </IconButton>
            </div>
            <div className="mt-3 space-y-3">
              <div className="relative rounded-lg bg-surface-muted p-4">
                <textarea
                  placeholder="Write your notes here"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                      e.preventDefault();
                      void handleAddNote();
                    }
                  }}
                  className="w-full resize-none border-0 bg-transparent text-sm outline-none"
                  rows={2}
                />
              </div>
              {notes.length === 0 ? (
                <p className="text-sm text-gray-500">No notes yet. Add one above.</p>
              ) : (
                notes.map((note) => (
                  <div key={note.id} className="relative rounded-lg bg-surface-muted p-4">
                    {editingId === note.id ? (
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        className="w-full resize-none border-0 bg-transparent text-sm outline-none"
                        rows={3}
                        autoFocus
                      />
                    ) : (
                      <>
                        <p className="pr-16 text-sm text-gray-700">{note.text}</p>
                        <p className="mt-2 text-left text-xs text-gray-400">
                          Written on {note.date}
                        </p>
                      </>
                    )}
                    <div className="absolute bottom-1 right-1 flex items-center gap-0.5">
                      {editingId === note.id ? (
                        <button
                          type="button"
                          onClick={() => void handleSaveEdit(note.id)}
                          className="rounded px-2 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50"
                        >
                          Save
                        </button>
                      ) : (
                        <IconButton
                          size="sm"
                          className="text-gray-400 hover:bg-transparent hover:text-gray-600"
                          title="Edit note"
                          aria-label="Edit note"
                          onClick={() => {
                            setEditingId(note.id);
                            setEditText(note.text);
                          }}
                        >
                          <Pencil className={getIconSizeClass("sm")} />
                        </IconButton>
                      )}
                      <IconButton
                        size="sm"
                        className="text-gray-400 hover:bg-red-50 hover:text-red-600"
                        title="Delete note"
                        aria-label="Delete note"
                        onClick={() => void handleDeleteNote(note.id)}
                      >
                        <Trash2 className={getIconSizeClass("sm")} />
                      </IconButton>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="overflow-hidden rounded-xl border border-gray-200">
            <SourceMetricsPanel source={source} className="w-full border-l-0" />
          </div>

          <section>
            <p className="text-xs font-semibold tracking-wide text-gray-500">RELATED PAPERS</p>
            <div className="mt-2 space-y-2">
              {relatedPapers.length > 0 ? (
                relatedPapers.map((s) => (
                  <SourceListItem
                    key={s.id}
                    title={s.title}
                    relevance={s.relevance}
                    projectId={projectId}
                    sourceId={s.id}
                    sourceReferrer={relatedSourceReferrer}
                  />
                ))
              ) : (
                <p className="text-sm text-gray-500">No related papers yet.</p>
              )}
            </div>
          </section>

          <section>
            <p className="text-xs font-semibold tracking-wide text-gray-500">CITES</p>
            <p className="text-xs text-gray-500">List of sources cited by this one.</p>
            <div className="mt-2 space-y-2">
              {citedSources.length > 0 ? (
                citedSources.map((s) => (
                  <SourceListItem
                    key={s.id}
                    title={s.title}
                    projectId={projectId}
                    sourceId={s.id}
                    sourceReferrer={relatedSourceReferrer}
                  />
                ))
              ) : (
                <p className="text-sm text-gray-500">No citation data yet.</p>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
