function requireEnv(key: keyof ImportMetaEnv): string {
  const value = import.meta.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  appName: import.meta.env.VITE_APP_NAME ?? "PaperSearcher",
  devPort: Number(import.meta.env.VITE_DEV_PORT ?? "5173"),
} as const;

export function assertEnvLoaded(): void {
  requireEnv("VITE_API_BASE_URL");
}
