/**
 * Backend:
 * GET   /api/v1/users/me
 * PATCH /api/v1/users/me
 *
 * Shared singleton profile until auth exists. No JWT/session yet.
 */
import { mockStore } from "@/api/mocks/store";
import { env } from "@/config/env";
import { allResearchAreas } from "@/data/mockData";
import { apiClient } from "@/lib/axios";
import type { ReadingLevel, UserProfile } from "@/types";

interface BackendProfile {
  name: string;
  full_name: string;
  email: string;
  occupation: string;
  institution: string;
  member_since: string;
  research_areas?: string[];
  keywords?: string[];
  reading_level?: ReadingLevel;
  sources_saved?: number;
  projects_count?: number;
  active_projects_this_month?: number;
  notes_written?: number;
  last_note_days_ago?: number;
  weekly_digest?: boolean;
  source_notifications?: boolean;
}

const SOURCE_NOTES_KEY = "papersearcher_source_notes";

function mapBackendProfile(data: BackendProfile): UserProfile {
  return {
    name: data.name,
    fullName: data.full_name,
    email: data.email,
    occupation: data.occupation,
    institution: data.institution,
    memberSince: data.member_since,
    researchAreas: data.research_areas ?? [],
    keywords: data.keywords ?? [],
    readingLevel: data.reading_level ?? "graduate",
    sourcesSaved: data.sources_saved ?? 0,
    projectsCount: data.projects_count ?? 0,
    activeProjectsThisMonth: data.active_projects_this_month ?? 0,
    notesWritten: data.notes_written ?? 0,
    lastNoteDaysAgo: data.last_note_days_ago ?? 0,
    weeklyDigest: data.weekly_digest ?? true,
    sourceNotifications: data.source_notifications ?? false,
  };
}

/** Notes are still localStorage-only — overlay counts onto API profile. */
function enrichWithLocalNotes(profile: UserProfile): UserProfile {
  try {
    const raw = localStorage.getItem(SOURCE_NOTES_KEY);
    if (!raw) return profile;
    const store = JSON.parse(raw) as Record<string, { date: string }[]>;
    const notes = Object.values(store).flat();
    if (notes.length === 0) return profile;

    let newestMs = 0;
    for (const note of notes) {
      const ms = Date.parse(note.date);
      if (!Number.isNaN(ms) && ms > newestMs) newestMs = ms;
    }
    const lastNoteDaysAgo =
      newestMs > 0
        ? Math.max(
            0,
            Math.floor((Date.now() - newestMs) / (24 * 60 * 60 * 1000)),
          )
        : profile.lastNoteDaysAgo;

    return {
      ...profile,
      notesWritten: notes.length,
      lastNoteDaysAgo,
    };
  } catch {
    return profile;
  }
}

function toBackendPatch(patch: Partial<UserProfile>): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  if (patch.name !== undefined) body.name = patch.name;
  if (patch.fullName !== undefined) body.full_name = patch.fullName;
  if (patch.email !== undefined) body.email = patch.email;
  if (patch.occupation !== undefined) body.occupation = patch.occupation;
  if (patch.institution !== undefined) body.institution = patch.institution;
  if (patch.researchAreas !== undefined) body.research_areas = patch.researchAreas;
  if (patch.keywords !== undefined) body.keywords = patch.keywords;
  if (patch.readingLevel !== undefined) body.reading_level = patch.readingLevel;
  if (patch.weeklyDigest !== undefined) body.weekly_digest = patch.weeklyDigest;
  if (patch.sourceNotifications !== undefined) {
    body.source_notifications = patch.sourceNotifications;
  }
  return body;
}

export async function getProfile(): Promise<UserProfile> {
  if (env.useMocks) {
    return mockStore.profile;
  }
  const { data } = await apiClient.get<BackendProfile>("/api/v1/users/me");
  return enrichWithLocalNotes(mapBackendProfile(data));
}

export async function updateProfile(
  patch: Partial<UserProfile>,
): Promise<UserProfile> {
  if (env.useMocks) {
    const next = { ...mockStore.profile, ...patch };
    mockStore.profile = next;
    return next;
  }
  const { data } = await apiClient.patch<BackendProfile>(
    "/api/v1/users/me",
    toBackendPatch(patch),
  );
  return enrichWithLocalNotes(mapBackendProfile(data));
}

export async function getResearchAreaOptions(): Promise<string[]> {
  return allResearchAreas;
}
