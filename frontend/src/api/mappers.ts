import type { Source } from "@/types";

/** Backend paper shape shared by discovery + project-paper list/save. */
export interface BackendPaper {
  id: string;
  source: string;
  external_id: string;
  title: string;
  abstract?: string | null;
  authors?: string[];
  year?: number | null;
  url?: string | null;
  pdf_url?: string | null;
  topics?: string[];
  created_at?: string;
}

const paperCache = new Map<string, Source>();

export function cacheSource(source: Source): Source {
  paperCache.set(source.id, source);
  return source;
}

export function cacheSources(sources: Source[]): Source[] {
  for (const source of sources) {
    paperCache.set(source.id, source);
  }
  return sources;
}

export function getCachedSource(sourceId: string): Source | undefined {
  return paperCache.get(sourceId);
}

export function mapBackendPaperToSource(
  paper: BackendPaper,
  extras?: Partial<Source>,
): Source {
  const savedOn = extras?.savedOn;
  return cacheSource({
    id: paper.id,
    title: paper.title,
    topics: paper.topics ?? [],
    source: paper.source,
    publishedMonth: "",
    publishedYear: paper.year ?? new Date().getFullYear(),
    description: paper.abstract ?? "",
    authors: paper.authors ?? [],
    // Soft metrics until scoring endpoints exist
    relevance: null,
    similarity: null,
    citations: null,
    citesSaved: null,
    citedBySaved: null,
    relevantTo: paper.topics ?? [],
    similarTo: [],
    keyFindings: [],
    publicationUrl: paper.url ?? paper.pdf_url ?? "#",
    externalId: paper.external_id,
    pdfUrl: paper.pdf_url ?? null,
    savedOn,
    ...extras,
  });
}

export function sourceToIndPaper(source: Source) {
  return {
    title: source.title,
    abstract: source.description || null,
    authors: source.authors,
    year: source.publishedYear,
    url: source.publicationUrl === "#" ? null : source.publicationUrl,
    pdf_url: source.pdfUrl ?? null,
    source: source.source,
    external_id: source.externalId ?? source.id,
    topics: source.topics,
  };
}
