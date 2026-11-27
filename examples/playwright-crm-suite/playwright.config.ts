// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { defineConfig, devices } from '@playwright/test';

const webMode = (process.env.SYNAPSE_WEB_MODE || 'offline').toLowerCase();
const stagingBaseUrl = (process.env.BASE_URL || '').trim();
if (webMode === 'staging' && !stagingBaseUrl) {
  throw new Error('SYNAPSE_WEB_MODE=staging requires an explicit BASE_URL staging target');
}

export default defineConfig({
  testDir: './tests',
  fullyParallel: false, // Run sequentially to prevent race conditions on shared demo CRM
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1, // Single worker to preserve clean state transition and avoid CRM rate limits
  timeout: 30000,
  expect: {
    timeout: 10000
  },
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
    ['junit', { outputFile: 'reports/junit.xml' }]
  ],
  use: {
    baseURL: process.env.BASE_URL || 'https://crm.anhtester.com',
    storageState: process.env.SYNAPSE_AUTH_STATE || undefined,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: process.env.CI ? 'off' : 'retain-on-failure',
    headless: true,
    viewport: { width: 1920, height: 1080 }
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] }
    }
  ]
});
