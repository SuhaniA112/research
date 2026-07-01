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
  relevance: number;
  similarity: number;
  citations: number;
  citesSaved: number;
  citedBySaved: number;
  relevantTo: string[];
  similarTo: string[];
  keyFindings: { text: string; section: string }[];
  publicationUrl: string;
  starred?: boolean;
  savedOn?: string;
  notes?: { id: string; text: string; date: string }[];
}

export interface Project {
  id: string;
  name: string;
  description: string;
  topics: string[];
  sourceCount: number;
  updatedDaysAgo: number;
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
