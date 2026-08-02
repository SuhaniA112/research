import { apiClient } from "@/lib/axios";
import type {
  DiscoverySearchRequest,
  DiscoverySearchResponse,
} from "@/features/research/types";

/**
 * Database-first research discovery.
 * Wire the Find Sources page to this when replacing mock search results.
 */
export async function searchResearch(
  body: DiscoverySearchRequest
): Promise<DiscoverySearchResponse> {
  const { data } = await apiClient.post<DiscoverySearchResponse>(
    "/api/v1/research/search",
    body
  );
  return data;
}
