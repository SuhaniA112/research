import type { Source } from "@/types";
import { decodeHtmlEntities } from "@/lib/text";

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
  summary_general?: string | null;
  summary_graduate?: string | null;
  summary_expert?: string | null;
  key_findings?: { text: string; section?: string }[];
  created_at?: string;
}

const paperCache = new Map<string, Source>();

export function cacheSource(source: Source): Source {
  paperCache.set(source.id, source);
  if (source.externalId) {
    paperCache.set(source.externalId, source);
  }
  return source;
}

export function cacheSources(sources: Source[]): Source[] {
  for (const source of sources) {
    cacheSource(source);
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
  const keyFindings = (paper.key_findings ?? []).map((finding) => ({
    text: decodeHtmlEntities(finding.text),
    section: decodeHtmlEntities(finding.section ?? "Paper") || "Paper",
  }));
  return cacheSource({
    id: paper.id,
    title: decodeHtmlEntities(paper.title) || "Untitled",
    topics: paper.topics ?? [],
    source: paper.source,
    publishedMonth: "",
    publishedYear: paper.year ?? new Date().getFullYear(),
    description: decodeHtmlEntities(paper.abstract ?? ""),
    authors: paper.authors ?? [],
    // Soft metrics until scoring APIs exist
    relevance: null,
    similarity: null,
    citations: null,
    citesSaved: null,
    citedBySaved: null,
    relevantTo: paper.topics ?? [],
    similarTo: [],
    keyFindings,
    summaries: {
      general: paper.summary_general
        ? decodeHtmlEntities(paper.summary_general)
        : null,
      graduate: paper.summary_graduate
        ? decodeHtmlEntities(paper.summary_graduate)
        : null,
      expert: paper.summary_expert ? decodeHtmlEntities(paper.summary_expert) : null,
    },
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
