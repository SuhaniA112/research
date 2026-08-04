import { mockStore } from "@/api/mocks/store";
import { env } from "@/config/env";
import type { Source } from "@/types";

export interface HubDigest {
  topPick: Source | null;
  items: Source[];
}

export async function getHubDigest(): Promise<HubDigest> {
  if (env.useMocks) {
    const [topPick, ...rest] = mockStore.sources;
    if (!topPick) {
      throw new Error("No sources available for digest");
    }
    return { topPick, items: rest.slice(0, 4) };
  }
  // Soft empty — no digest endpoint yet
  return { topPick: null, items: [] };
}
