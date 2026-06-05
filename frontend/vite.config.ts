import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev: Vite serves on :5173 and proxies /api → the FastAPI backend on :8000,
// so the SPA talks to the same-origin paths it will use in production (where
// FastAPI serves the built `dist/`). Build output is a pinned, dependency-free
// static bundle — no runtime CDN — preserving the project's reliability goal.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  base: "/",
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
