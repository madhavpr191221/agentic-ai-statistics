import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command:
        'uv --cache-dir ../.uv-cache run --project .. python -m mcp_traffic_analysis.demo --artifact-root ../artifacts/e2e --api-only --port 8000',
      url: 'http://127.0.0.1:8000/api/health',
      name: 'FastAPI',
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5173',
      name: 'Vite',
      timeout: 120_000,
      reuseExistingServer: false,
    },
  ],
})
