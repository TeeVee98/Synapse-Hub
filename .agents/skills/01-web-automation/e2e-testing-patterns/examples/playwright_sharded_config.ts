// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: 2,
  workers: process.env.CI ? 4 : undefined,
  use: {
    headless: true,
    trace: 'on-first-retry',
  },
});
