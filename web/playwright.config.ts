import { defineConfig } from "@playwright/test";

const PORT = 3100;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: "list",
  use: { baseURL: `http://localhost:${PORT}`, viewport: { width: 1440, height: 900 } },
  webServer: {
    // Mock mode: CLAIMCHECK_API_URL is cleared so the tests always replay fixtures/expected/.
    command: `npm run build && npm run start -- -p ${PORT}`,
    url: `http://localhost:${PORT}`,
    env: { CLAIMCHECK_API_URL: "", CLAIMCHECK_MOCK_DELAY_MS: "40" },
    reuseExistingServer: false,
    timeout: 180_000,
  },
});
