import { defineConfig } from '@playwright/test';

const baseURL = process.env.PRINTREADY_URL || 'http://127.0.0.1:8012';

export default defineConfig({
  testDir: './tests',
  timeout: 90_000,
  workers: 1,
  reporter: 'list',
  outputDir: '../_data/qa/playwright',
  use: { baseURL, viewport: { width: 1536, height: 1024 }, trace: 'retain-on-failure' },
  webServer: {
    command: 'uv run --directory .. printready-api',
    url: `${baseURL}/api/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
