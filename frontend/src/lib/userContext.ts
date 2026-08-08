/**
 * Temporary user context until real authentication exists.
 *
 * The backend scopes projects via ``X-User-ID``. We persist a demo user id in
 * localStorage and ensure a matching User row exists on the API.
 */
import { env } from "@/config/env";

export const USER_ID_STORAGE_KEY = "papersearcher_user_id";
export const USER_ID_HEADER = "X-User-ID";

interface BackendUser {
  id: string;
  email: string;
  full_name: string;
}

export function getStoredUserId(): string | null {
  return localStorage.getItem(USER_ID_STORAGE_KEY);
}

export function setStoredUserId(userId: string): void {
  localStorage.setItem(USER_ID_STORAGE_KEY, userId);
}

export function clearStoredUserId(): void {
  localStorage.removeItem(USER_ID_STORAGE_KEY);
}

/**
 * Ensure a backend user exists for temporary project ownership.
 * Safe to call repeatedly; reuses localStorage id when still valid.
 */
export async function ensureCurrentUserId(): Promise<string> {
  if (env.useMocks) {
    const mockId = getStoredUserId() ?? "00000000-0000-4000-8000-000000000099";
    setStoredUserId(mockId);
    return mockId;
  }

  // Lazy import avoids a circular dependency with axios interceptors.
  const { apiClient } = await import("@/lib/axios");

  const existing = getStoredUserId();
  if (existing) {
    try {
      await apiClient.get<BackendUser>(`/api/v1/users/${existing}`);
      return existing;
    } catch {
      clearStoredUserId();
    }
  }

  const suffix = crypto.randomUUID().replace(/-/g, "").slice(0, 12);
  const { data } = await apiClient.post<BackendUser>("/api/v1/users", {
    email: `demo-${suffix}@example.com`,
    full_name: "Demo User",
    password: "temporary-password-123",
  });
  setStoredUserId(data.id);
  return data.id;
}
