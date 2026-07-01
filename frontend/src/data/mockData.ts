import type { MindMapEdge, MindMapNode, Project, Source, UserProfile } from "@/types";

export const currentUser: UserProfile = {
  name: "Alex",
  fullName: "Alex Chen",
  occupation: "Graduate Student",
  institution: "Cornell University",
  memberSince: "Jan 2024",
  email: "alex@example.com",
  researchAreas: ["AI/ML", "HCI", "Assistive Tech"],
  keywords: ["LLM", "GenAI"],
  readingLevel: "graduate",
  sourcesSaved: 42,
  projectsCount: 8,
  activeProjectsThisMonth: 3,
  notesWritten: 18,
  lastNoteDaysAgo: 2,
  weeklyDigest: true,
  sourceNotifications: false,
};

export const allResearchAreas = [
  "AI/ML",
  "HCI",
  "Assistive Tech",
  "Cloud Computing",
  "Cybersecurity",
  "Blockchain",
  "Quantum Computing",
  "AR/VR",
];

export const projects: Project[] = [
  {
    id: "1",
    name: "Accessible AI Interfaces",
    description:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    topics: ["HCI", "AI/ML"],
    sourceCount: 24,
    updatedDaysAgo: 2,
    starred: true,
  },
  {
    id: "2",
    name: "LLM Evaluation Methods",
    description:
      "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    topics: ["AI/ML", "NLP"],
    sourceCount: 18,
    updatedDaysAgo: 5,
    starred: false,
  },
  {
    id: "3",
    name: "Assistive Robotics",
    description:
      "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    topics: ["Assistive Tech"],
    sourceCount: 12,
    updatedDaysAgo: 7,
    starred: true,
  },
  {
    id: "4",
    name: "Multimodal Learning",
    description:
      "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
    topics: ["AI/ML", "Vision"],
    sourceCount: 31,
    updatedDaysAgo: 1,
    starred: false,
  },
];

export const recentSearches = [
  "adaptive interfaces for blind users",
  "LLM hallucination detection",
  "assistive robotics survey 2024",
  "multimodal learning benchmarks",
];

export const recentProjectSearches: Record<string, string[]> = {
  "1": ["screen reader AI", "voice UI accessibility", "WCAG compliance tools"],
  "2": ["GPT-4 evaluation", "LLM benchmark datasets"],
  "3": ["robotic arm assistive", "haptic feedback systems"],
  "4": ["CLIP fine-tuning", "vision-language models"],
};

const loremSummary =
  "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.";

const loremSummaryGraduate =
  "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Sed ut perspiciatis unde omnis iste natus error sit voluptatem.";

const loremSummaryExpert =
  "At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident. Similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga.";

export const summaryTexts: Record<string, string> = {
  general: loremSummary,
  graduate: loremSummaryGraduate,
  expert: loremSummaryExpert,
};

export const sources: Source[] = [
  {
    id: "s1",
    title: "Designing Accessible AI-Powered Interfaces for Non-Visual Users",
    topics: ["HCI", "AI/ML"],
    source: "CHI Conference",
    publishedMonth: "Apr",
    publishedYear: 2024,
    description: loremSummary,
    authors: ["Dr. Jane Smith", "Prof. Robert Lee"],
    relevance: 92,
    similarity: 87,
    citations: 156,
    citesSaved: 4,
    citedBySaved: 2,
    relevantTo: ["Accessibility", "AI Interfaces", "Screen Readers"],
    similarTo: ["Voice UI for Blind Users", "Adaptive Haptic Feedback"],
    keyFindings: [
      { text: "Multimodal feedback significantly improves task completion rates", section: "Results" },
      { text: "LLM-generated descriptions require human verification for accuracy", section: "Discussion" },
      { text: "Participants preferred voice-first interaction over touch-based alternatives", section: "User Study" },
    ],
    publicationUrl: "https://dl.acm.org/doi/10.1145/3613904.3642134",
    starred: true,
    savedOn: "Mar 12, 2024",
    notes: [
      { id: "n1", text: "Strong methodology section — compare with our approach.", date: "Mar 13, 2024" },
      { id: "n2", text: "Citation network overlaps with 3 of our saved sources.", date: "Mar 15, 2024" },
    ],
  },
  {
    id: "s2",
    title: "Evaluating Large Language Models for Research Assistance",
    topics: ["AI/ML", "NLP"],
    source: "NeurIPS",
    publishedMonth: "Dec",
    publishedYear: 2023,
    description: loremSummary,
    authors: ["Dr. Maria Garcia", "Dr. James Wilson"],
    relevance: 88,
    similarity: 79,
    citations: 342,
    citesSaved: 6,
    citedBySaved: 3,
    relevantTo: ["LLM Evaluation", "Research Tools"],
    similarTo: ["GPT-4 Benchmark Study"],
    keyFindings: [
      { text: "Retrieval-augmented generation reduces hallucination by 34%", section: "Experiments" },
      { text: "Domain-specific fine-tuning outperforms general models on citation tasks", section: "Results" },
    ],
    publicationUrl: "https://papers.nips.cc/paper_files/paper/2023",
    starred: false,
    savedOn: "Feb 28, 2024",
    notes: [{ id: "n3", text: "Relevant benchmark dataset for our evaluation pipeline.", date: "Mar 1, 2024" }],
  },
  {
    id: "s3",
    title: "Haptic Feedback Systems in Assistive Robotics",
    topics: ["Assistive Tech", "Robotics"],
    source: "IEEE Transactions",
    publishedMonth: "Jun",
    publishedYear: 2024,
    description: loremSummary,
    authors: ["Prof. Elena Vasquez"],
    relevance: 85,
    similarity: 72,
    citations: 89,
    citesSaved: 2,
    citedBySaved: 1,
    relevantTo: ["Haptics", "Robotics", "Accessibility"],
    similarTo: ["Tactile Navigation Systems"],
    keyFindings: [
      { text: "Force-feedback gloves improved precision by 28% in manipulation tasks", section: "Results" },
      { text: "Cost-effective actuator designs enable wider deployment", section: "Hardware" },
    ],
    publicationUrl: "https://ieeexplore.ieee.org/document/10501234",
    starred: true,
    savedOn: "Apr 2, 2024",
    notes: [],
  },
  {
    id: "s4",
    title: "Multimodal Foundation Models: A Comprehensive Survey",
    topics: ["AI/ML", "Vision"],
    source: "arXiv Preprint",
    publishedMonth: "Jan",
    publishedYear: 2024,
    description: loremSummary,
    authors: ["Dr. Wei Zhang", "Dr. Sarah Kim", "Prof. Michael Brown"],
    relevance: 78,
    similarity: 65,
    citations: 521,
    citesSaved: 8,
    citedBySaved: 5,
    relevantTo: ["Multimodal Learning", "Foundation Models"],
    similarTo: ["CLIP Architecture Review"],
    keyFindings: [
      { text: "Cross-modal alignment remains the primary bottleneck", section: "Analysis" },
      { text: "Open-source models are closing the gap with proprietary systems", section: "Benchmarks" },
    ],
    publicationUrl: "https://arxiv.org/abs/2401.14405",
    starred: false,
  },
  {
    id: "s5",
    title: "Voice-Controlled Navigation for Visually Impaired Users",
    topics: ["HCI", "Accessibility"],
    source: "UIST",
    publishedMonth: "Oct",
    publishedYear: 2023,
    description: loremSummary,
    authors: ["Dr. Anna Patel"],
    relevance: 91,
    similarity: 83,
    citations: 67,
    citesSaved: 3,
    citedBySaved: 1,
    relevantTo: ["Voice UI", "Navigation", "Accessibility"],
    similarTo: ["Designing Accessible AI-Powered Interfaces"],
    keyFindings: [
      { text: "Context-aware voice commands reduced navigation errors by 45%", section: "Evaluation" },
    ],
    publicationUrl: "https://dl.acm.org/doi/10.1145/3586183.3606763",
    starred: false,
  },
];

export function getProject(id: string): Project | undefined {
  return projects.find((p) => p.id === id);
}

export function getSource(id: string): Source | undefined {
  return sources.find((s) => s.id === id);
}

export const mindMapNodes: MindMapNode[] = [
  { id: "center", label: "Accessible AI Interfaces", type: "project", x: 50, y: 50 },
  { id: "t1", label: "Voice UI", type: "topic", x: 25, y: 25, sourcesSaved: 8, subTopics: 3 },
  { id: "t2", label: "Screen Readers", type: "topic", x: 75, y: 25, sourcesSaved: 6, subTopics: 2 },
  { id: "t3", label: "Haptic Feedback", type: "topic", x: 25, y: 75, sourcesSaved: 5, subTopics: 4 },
  { id: "t4", label: "LLM Tools", type: "topic", x: 75, y: 75, sourcesSaved: 5, subTopics: 2 },
  { id: "st1", label: "speech synthesis", type: "subtopic", x: 15, y: 15 },
  { id: "st2", label: "command parsing", type: "subtopic", x: 35, y: 10 },
  { id: "st3", label: "ARIA standards", type: "subtopic", x: 65, y: 15 },
  { id: "st4", label: "braille displays", type: "subtopic", x: 85, y: 20 },
  { id: "st5", label: "force feedback", type: "subtopic", x: 15, y: 85 },
  { id: "st6", label: "wearables", type: "subtopic", x: 30, y: 90 },
  { id: "st7", label: "RAG systems", type: "subtopic", x: 70, y: 85 },
  { id: "st8", label: "fine-tuning", type: "subtopic", x: 85, y: 90 },
];

export const mindMapEdges: MindMapEdge[] = [
  { from: "center", to: "t1" },
  { from: "center", to: "t2" },
  { from: "center", to: "t3" },
  { from: "center", to: "t4" },
  { from: "t1", to: "st1" },
  { from: "t1", to: "st2" },
  { from: "t2", to: "st3" },
  { from: "t2", to: "st4" },
  { from: "t3", to: "st5" },
  { from: "t3", to: "st6" },
  { from: "t4", to: "st7" },
  { from: "t4", to: "st8" },
];

export const sourceBreakdown = [
  { name: "Journals", value: 45, color: "#6b7280" },
  { name: "Preprints", value: 35, color: "#9ca3af" },
  { name: "Others", value: 20, color: "#d1d5db" },
];

export const sourceRecency = [
  { year: "2017", count: 2 },
  { year: "2018", count: 3 },
  { year: "2019", count: 4 },
  { year: "2020", count: 5 },
  { year: "2021", count: 8 },
  { year: "2022", count: 12 },
  { year: "2023", count: 18 },
];
