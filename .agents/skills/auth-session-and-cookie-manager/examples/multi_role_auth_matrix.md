# Multi-Role Authentication Matrix & Zero-Second Session Management

> **Principle:** Never log in via UI forms repeatedly. Seed authenticated storageState once per role and reuse across test suites for 0-second test startup.

---

## 1. Role State Matrix

| Role | Permissions | Storage State File | Seeding Endpoint |
| :--- | :--- | :--- | :--- |
| **System Admin** | Full write, user management, billing, audits | `.auth/admin.json` | `POST /api/v1/auth/seed-admin` |
| **Branch Manager** | Order approval, invoice reconcile, read reports | `.auth/manager.json` | `POST /api/v1/auth/seed-manager` |
| **Cashier / Viewer** | View catalog, draft cart items, no billing | `.auth/cashier.json` | `POST /api/v1/auth/seed-cashier` |

---

## 2. Playwright Multi-Role Setup (`playwright.config.ts`)

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  projects: [
    // Setup project: runs once before all tests
    {
      name: 'auth-setup',
      testMatch: /.*\.setup\.ts/,
    },
    // Admin Tests
    {
      name: 'admin-tests',
      use: {
        ...devices['Desktop Chrome'],
        storageState: '.auth/admin.json',
      },
      dependencies: ['auth-setup'],
    },
    // Manager Tests
    {
      name: 'manager-tests',
      use: {
        ...devices['Desktop Chrome'],
        storageState: '.auth/manager.json',
      },
      dependencies: ['auth-setup'],
    },
  ],
});
```

---

## 3. Silent Token Refresh Middleware

When API returns HTTP 401 mid-test, invoke direct refresh without re-entering login forms:
```typescript
export async function refreshSessionToken(page: Page, refreshToken: string): Promise<string> {
  const response = await page.request.post('/api/auth/token/refresh', {
    data: { refresh_token: refreshToken },
  });
  const body = await response.json();
  await page.context().addCookies([{
    name: 'session_jwt',
    value: body.access_token,
    domain: 'localhost',
    path: '/',
  }]);
  return body.access_token;
}
```
