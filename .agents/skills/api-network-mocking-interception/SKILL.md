---
name: api-network-mocking-interception
description: Runtime HTTP/GraphQL request interception and route stubbing (page.route) to mock live API backends and inject 4xx/5xx network fault conditions during UI execution.
---

# API Network Mocking & Interception Skill

> **Target:** Eliminate flaky tests caused by backend dependencies, slow microservices, or inconsistent staging data by intercepting browser-level network requests.

---

## 1. Core Principles

1. **Deterministic State over Staging Data:**
   - UI tests should verify front-end state rendering and user interactions, not whether the backend DB is seeded.
   - Use route interception (`page.route()`) to return predictable JSON contracts (success, 400 Bad Request, 500 Server Error).

2. **Zero Network Latency:**
   - Mock external telemetry, 3rd party analytics, fonts, and heavy media assets to speed up execution by 3x-5x.

3. **Fault Injection & Chaos Verification:**
   - Test UI resiliency against network timeouts, dropped connections, and malformed schemas without altering real server code.

---

## 2. Playwright Route Interception Standard Patterns

### Pattern A: Static JSON Response Stubbing
```typescript
// Stub user profile API
await page.route('**/api/v1/user/profile', async (route) => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      id: 'USR_AUTO_99',
      username: 'qa_sentinel',
      roles: ['ADMIN_OPERATOR'],
      permissions: ['READ', 'WRITE', 'EXECUTE']
    })
  });
});
```

### Pattern B: Modifying Live Responses (HAR / Passthrough Mutation)
```typescript
// Intercept real response and inject edge-case field
await page.route('**/api/v1/reports', async (route) => {
  const response = await route.fetch();
  const json = await response.json();
  json.totalItems = 999999; // Test UI overflow / pagination edge case
  await route.fulfill({ response, json });
});
```

### Pattern C: Simulating Network Failures & Delays
```typescript
// Simulate 500 Internal Server Error
await page.route('**/api/v1/checkout', async (route) => {
  await route.fulfill({
    status: 500,
    contentType: 'application/json',
    body: JSON.stringify({ errorCode: 'ERR_PAYMENT_DOWN', message: 'Gateway unreachable' })
  });
});

// Simulate High Latency (Slow 3G)
await page.route('**/api/v1/heavy-list', async (route) => {
  await new Promise(res => setTimeout(res, 3000));
  await route.continue();
});
```

---

## 3. Best Practices Checklist
- [ ] Always declare routes **before** calling `page.goto()`.
- [ ] Use regex or glob pattern with caution; avoid intercepting Vite/Webpack bundling scripts.
- [ ] For teardown, unroute specific patterns or reset context per test.
