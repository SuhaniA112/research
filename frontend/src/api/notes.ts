/**
 * Client-persisted notes (no notes API yet).
 * Source notes: keyed by source id.
 * Mind-map notes: keyed by `${projectId}:${nodeId}`.
 */
export interface SourceNote {
  id: string;
  text: string;
  date: string;
}

const SOURCE_NOTES_KEY = "papersearcher_source_notes";
const MIND_MAP_NOTES_KEY = "papersearcher_mindmap_notes";

type SourceNotesStore = Record<string, SourceNote[]>;
type MindMapNotesStore = Record<string, string>;

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  localStorage.setItem(key, JSON.stringify(value));
}

function formatNoteDate(date = new Date()): string {
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function mindMapKey(projectId: string, nodeId: string): string {
  return `${projectId}:${nodeId}`;
}

export async function listSourceNotes(sourceId: string): Promise<SourceNote[]> {
  const store = readJson<SourceNotesStore>(SOURCE_NOTES_KEY, {});
  return [...(store[sourceId] ?? [])];
}

export async function addSourceNote(
  sourceId: string,
  text: string,
): Promise<SourceNote> {
  const trimmed = text.trim();
  if (!trimmed) {
    throw new Error("Note text is required");
  }
  const store = readJson<SourceNotesStore>(SOURCE_NOTES_KEY, {});
  const note: SourceNote = {
    id: `note-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    text: trimmed,
    date: formatNoteDate(),
  };
  store[sourceId] = [note, ...(store[sourceId] ?? [])];
  writeJson(SOURCE_NOTES_KEY, store);
  return note;
}

export async function updateSourceNote(
  sourceId: string,
  noteId: string,
  text: string,
): Promise<SourceNote | undefined> {
  const trimmed = text.trim();
  const store = readJson<SourceNotesStore>(SOURCE_NOTES_KEY, {});
  const list = store[sourceId] ?? [];
  const index = list.findIndex((note) => note.id === noteId);
  if (index < 0) return undefined;
  if (!trimmed) {
    store[sourceId] = list.filter((note) => note.id !== noteId);
    writeJson(SOURCE_NOTES_KEY, store);
    return undefined;
  }
  const updated: SourceNote = {
    ...list[index]!,
    text: trimmed,
    date: formatNoteDate(),
  };
  store[sourceId] = list.map((note, i) => (i === index ? updated : note));
  writeJson(SOURCE_NOTES_KEY, store);
  return updated;
}

export async function deleteSourceNote(
  sourceId: string,
  noteId: string,
): Promise<void> {
  const store = readJson<SourceNotesStore>(SOURCE_NOTES_KEY, {});
  store[sourceId] = (store[sourceId] ?? []).filter((note) => note.id !== noteId);
  writeJson(SOURCE_NOTES_KEY, store);
}

export async function getMindMapNote(
  projectId: string,
  nodeId: string,
): Promise<string> {
  const store = readJson<MindMapNotesStore>(MIND_MAP_NOTES_KEY, {});
  return store[mindMapKey(projectId, nodeId)] ?? "";
}

export async function setMindMapNote(
  projectId: string,
  nodeId: string,
  text: string,
): Promise<void> {
  const store = readJson<MindMapNotesStore>(MIND_MAP_NOTES_KEY, {});
  const key = mindMapKey(projectId, nodeId);
  const trimmed = text.trim();
  if (!trimmed) {
    delete store[key];
  } else {
    store[key] = text;
  }
  writeJson(MIND_MAP_NOTES_KEY, store);
}
