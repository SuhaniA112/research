export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  appName: import.meta.env.VITE_APP_NAME ?? "PaperSearcher",
  devPort: Number(import.meta.env.VITE_DEV_PORT ?? "5173"),
  useMocks: (import.meta.env.VITE_USE_MOCKS ?? "true") !== "false",
} as const;
