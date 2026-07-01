import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import type { ReactNode } from "react";

import { StarredProvider } from "@/providers/StarredProvider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <StarredProvider>{children}</StarredProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
