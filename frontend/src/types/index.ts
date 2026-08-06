export type SummaryLevel = "general" | "graduate" | "expert";
export type ReadingLevel = "casual" | "graduate" | "expert";

export interface Source {
  id: string;
  title: string;
  topics: string[];
  source: string;
  publishedMonth: string;
  publishedYear: number;
  description: string;
  authors: string[];
  /** null = soft placeholder until scoring APIs exist */
  relevance: number | null;
  similarity: number | null;
  citations: number | null;
  citesSaved: number | null;
  citedBySaved: number | null;
  relevantTo: string[];
  similarTo: string[];
  keyFindings: { text: string; section: string }[];
  publicationUrl: string;
  externalId?: string;
  pdfUrl?: string | null;
  starred?: boolean;
  savedOn?: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  topics: string[];
  keywords: string[];
  readingLevel: ReadingLevel;
  sourceCount: number;
  /** ISO timestamp of last project update. */
  updatedAt: string;
  starred: boolean;
}

export interface UserProfile {
  name: string;
  fullName: string;
  occupation: string;
  institution: string;
  memberSince: string;
  email: string;
  researchAreas: string[];
  keywords: string[];
  readingLevel: ReadingLevel;
  sourcesSaved: number;
  projectsCount: number;
  activeProjectsThisMonth: number;
  notesWritten: number;
  lastNoteDaysAgo: number;
  weeklyDigest: boolean;
  sourceNotifications: boolean;
}

export interface MindMapNode {
  id: string;
  label: string;
  type: "project" | "topic" | "subtopic";
  x: number;
  y: number;
  sourcesSaved?: number;
  subTopics?: number;
}

export interface MindMapEdge {
  from: string;
  to: string;
}
