import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { apiClient } from "@/lib/axios";
import type { User } from "@/features/users/types";

async function fetchUser(userId: string): Promise<User> {
  const { data } = await apiClient.get<User>(`/api/v1/users/${userId}`);
  return data;
}

export function useUser(userId: string): UseQueryResult<User, Error> {
  return useQuery({
    queryKey: ["users", userId],
    queryFn: () => fetchUser(userId),
    enabled: Boolean(userId),
  });
}
