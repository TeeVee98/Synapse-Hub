---
name: auth-session-and-cookie-manager
description: "Manage browser authentication sessions, storageState, JWT tokens, and multi-role state. Use when managing login sessions, storage state, or cookie reuse across tests."
---

# Auth Session & Cookie Manager Skill

> **Target:** Eliminate repetitive, slow UI login forms by saving, refreshing, and injecting browser storage states, cookies, and JWT bearer tokens directly into execution contexts.

---

## 1. Core Principles

1. **Zero-Second Auth Protocol:**
   - Execute UI authentication once to produce a verified `session.json` / `storageState.json`.
   - All subsequent test cases inject this saved state directly at context initialization.
2. **Multi-Role Context Isolation:**
   - Maintain distinct session fixtures for different privilege tiers (e.g. `admin_state.json`, `reviewer_state.json`, `viewer_state.json`).
3. **Session Freshness & Auto-Refresh:**
   - Inspect token expiry timestamp (`exp` in JWT payload); auto-refresh via API endpoint if token lifetime has elapsed.
4. **Security & Credential Hygiene:**
   - **No Plaintext Tokens in Logs:** Avoid logging or storing raw plaintext JWT tokens, session cookies, or credentials in test logs, execution traces, or memory stores. Persist only non-sensitive metadata: SHA-256 hash reference, expiry epoch, and role.
   - **Session Lifecycle & Mandatory Cleanup:**
     1. *Provisioning:* Authenticate once per role in setup fixtures; save ephemeral session files to `.auth/<role>_state.json`.
     2. *In-Flight Validation:* Validate session freshness before execution; trigger token auto-refresh when near expiry.
     3. *Teardown & Purge:* Automatically remove ephemeral session files (`.auth/`) during test teardown or CI post-actions; invalidate tokens post-run to prevent leakage.
   - **Gitignore Protection:** Always add `.auth/` and `*storageState*.json` to `.gitignore` to prevent committing live credentials to version control.

---

## 2. Standard Playwright Implementation Patterns

### Pattern A: Generating and Reusing Storage State
```typescript
// 1. One-time Setup fixture (e.g. auth.setup.ts)
import { test as setup, expect } from '@playwright/test';

const adminFile = '.auth/admin_state.json';

setup('authenticate as admin', async ({ page }) => {
  await page.goto('/login');
  await page.fill('#username', process.env.ADMIN_USER!);
  await page.fill('#password', process.env.ADMIN_PASS!);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard');
  
  await page.context().storageState({ path: adminFile });
});
```

### Pattern B: Injecting Session Directly (Zero-Second Login)
```typescript
// Reusing authenticated session without loading login form
import { test } from '@playwright/test';

test.use({ storageState: '.auth/admin_state.json' });

test('access protected admin table directly', async ({ page }) => {
  await page.goto('/admin/users'); // Opens already logged in
  // Continue immediately with business actions
});
```

### Pattern C: Multi-Context Dual Role Testing (Maker vs Checker)
```typescript
test('dual-role transaction approval', async ({ browser }) => {
  // Context 1: Staff creates proposal
  const staffContext = await browser.newContext({ storageState: '.auth/staff_state.json' });
  const staffPage = await staffContext.newPage();
  await staffPage.goto('/proposals/new');
  // ... submit proposal ...

  // Context 2: Manager reviews and approves
  const managerContext = await browser.newContext({ storageState: '.auth/manager_state.json' });
  const managerPage = await managerContext.newPage();
  await managerPage.goto('/proposals/pending');
  // ... approve proposal ...
});
```

### Pattern D: Automated Session Teardown & Invalidation
```typescript
// auth.teardown.ts / global teardown fixture
import { test as teardown } from '@playwright/test';
import fs from 'fs';
import path from 'path';

teardown('purge ephemeral session states', async () => {
  const authDir = path.resolve('.auth');
  if (fs.existsSync(authDir)) {
    fs.rmSync(authDir, { recursive: true, force: true });
    console.log('[AUTH-CLEANUP] Purged ephemeral auth states from .auth/');
  }
});
```
