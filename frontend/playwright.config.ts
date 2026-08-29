import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:5174',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command:
        'uv --cache-dir ../.uv-cache run --project .. python -m agentic_ai_statistics.demo --agent-root ../artifacts/e2e-agent --behavior-root ../artifacts/e2e-behavior --trace-study-root ../artifacts/e2e-trace-study --api-only --port 8001',
      url: 'http://127.0.0.1:8001/api/health',
      name: 'FastAPI',
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --port 5174',
      url: 'http://127.0.0.1:5174',
      name: 'Vite',
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        VITE_API_PROXY_TARGET: 'http://127.0.0.1:8001',
      },
    },
  ],
})
