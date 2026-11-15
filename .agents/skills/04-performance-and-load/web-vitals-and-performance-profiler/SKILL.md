---
name: web-vitals-and-performance-profiler
description: "Measure Core Web Vitals (LCP, CLS, INP) and network waterfalls via CDP. Use when the user asks why a page is slow or needs CWV budgets enforced in CI."
category: architecture_and_analysis
version: "2.0.0"
policies:
  network: localhost-only
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Web Vitals & Performance Profiler Skill

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Measure Core Web Vitals (LCP, CLS, INP) and network waterfalls via CDP. Use when the user asks why a page is slow or needs CWV budgets enforced in CI.
- **Activation Scope:** Domain workflows for `04-performance-and-load` involving `web-vitals-and-performance-profiler`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT measure performance with browser DevTools open or under unconstrained CPU/network conditions.
- Do NOT report Web Vitals metrics from a single test execution; collect median values over multiple runs.
- Do NOT focus exclusively on page load; track runtime responsiveness and visual stability.
- **Sibling Skill Boundaries:**
  - backend-load-and-stress-patterns tests server saturation; web-vitals-and-performance-profiler measures client browser Core Web Vitals (LCP, FID/INP, CLS).

---

## 3. Ordered Execution Workflow

> **Target:** Detect user-experience bottlenecks, layout shifts, sluggish API responses, and render-blocking assets automatically during headless test execution.

---

### Core Principles

1. **Performance as an Assertion:**
   - Functional tests must double as non-functional guardrails. If a critical workflow takes > 10 seconds to load, it should fail performance budgets.
2. **Google Core Web Vitals Metrics:**
   - **LCP (Largest Contentful Paint):** Target $\le 2.5\text{s}$ (Good).
   - **CLS (Cumulative Layout Shift):** Target $\le 0.1$ (Good).
   - **TTFB (Time to First Byte):** Target $\le 800\text{ms}$ (Good).
3. **Observation-Masked Telemetry:**
   - Never dump thousands of CDP trace lines into context. Only output calculated metric scores and flagged slow endpoints (> 1500ms).

---

### Standard Playwright Performance Measurement

### Pattern A: Extracting Core Web Vitals via JavaScript Evaluation
<!-- classification: illustrative -->
```typescript
import { test, expect } from '@playwright/test';

test('audit core web vitals on dashboard', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');

  const performanceTiming = JSON.parse(
    await page.evaluate(() => JSON.stringify(window.performance.timing))
  );

  const ttfb = performanceTiming.responseStart - performanceTiming.navigationStart;
  const domLoadTime = performanceTiming.domContentLoadedEventEnd - performanceTiming.navigationStart;

  console.log(`[PERF] TTFB: ${ttfb}ms | DOM Load: ${domLoadTime}ms`);
  expect(ttfb).toBeLessThan(1500); // 1.5s threshold
});
```

### Pattern B: Tracking Slow Network Endpoints
<!-- classification: illustrative -->
```typescript
test('detect slow backend microservices', async ({ page }) => {
  const slowRequests: { url: string; duration: number }[] = [];

  page.on('response', (response) => {
    const timing = response.timing();
    const duration = timing.responseEnd;
    if (duration > 2000) {
      slowRequests.push({ url: response.url(), duration });
    }
  });

  await page.goto('/reports');
  await page.waitForLoadState('networkidle');

  expect(slowRequests).toHaveLength(0); // Fail if any endpoint took > 2s
});
```

---

## 4. Verification Points & DoD

1. Performance measurements capture LCP, CLS, and INP against standard thresholds (Good, Needs Work, Poor).
2. Network and CPU throttling profiles simulate realistic target user conditions.
3. Performance telemetry logs specific DOM element culprits for LCP and CLS.

---

## 5. Handoff Protocol

- **Deliverables:** Core Web Vitals telemetry reports, CDP trace profiles, and performance remediation recommendations.
- **Next Subagent:** perf-engineer
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
