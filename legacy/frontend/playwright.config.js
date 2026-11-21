import { defineConfig } from "@playwright/test";

// E2E config. The dev server is started automatically; tests mock the backend API
// (page.route), so no Python backend or network access to Wikimedia is required.
export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  use: { baseURL: "http://localhost:5173" },
  webServer: {
    command: "npm run dev -- --port 5173 --strictPort",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
});
