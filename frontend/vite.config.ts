import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: Number(env.VITE_DEV_PORT) || 5173,
      proxy: {
        "/api": {
          target: env.VITE_API_BASE_URL ?? "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
