/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Test config kept separate from vite.config.ts so the production build stays
// untouched. jsdom gives the markdown/Pager component tests a DOM; the @/ alias
// mirrors the app. Dev-only — none of this ships in the bundle (no-CDN posture
// preserved). Run with `npm run test`.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
