import { mockStore } from "@/api/mocks/store";
import { env } from "@/config/env";
import { allResearchAreas } from "@/data/mockData";
import { apiClient } from "@/lib/axios";
import type { UserProfile } from "@/types";

const PROFILE_STORAGE_KEY = "papersearcher_profile";

function readLocalProfile(): UserProfile {
  const raw = localStorage.getItem(PROFILE_STORAGE_KEY);
  if (!raw) return mockStore.profile;
  return { ...mockStore.profile, ...JSON.parse(raw) } as UserProfile;
}

function writeLocalProfile(profile: UserProfile): void {
  mockStore.profile = profile;
  localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
}

export async function getProfile(): Promise<UserProfile> {
  if (env.useMocks) {
    return readLocalProfile();
  }
  // Soft empty — /users/me does not exist yet; keep local prefs
  try {
    const { data } = await apiClient.get<UserProfile>("/api/v1/users/me");
    return data;
  } catch {
    return readLocalProfile();
  }
}

export async function updateProfile(
  patch: Partial<UserProfile>,
): Promise<UserProfile> {
  if (env.useMocks) {
    const next = { ...readLocalProfile(), ...patch };
    writeLocalProfile(next);
    return next;
  }
  try {
    const { data } = await apiClient.patch<UserProfile>("/api/v1/users/me", patch);
    return data;
  } catch {
    const next = { ...readLocalProfile(), ...patch };
    writeLocalProfile(next);
    return next;
  }
}

export async function getResearchAreaOptions(): Promise<string[]> {
  return allResearchAreas;
}
