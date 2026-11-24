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
2. **Google Core Web Vitals & W3C Metrics:**
   - **LCP (Largest Contentful Paint):** Target $\le 2.5\text{s}$ (Good), $> 4.0\text{s}$ (Poor).
   - **CLS (Cumulative Layout Shift):** Target $\le 0.1$ (Good), $> 0.25$ (Poor).
   - **INP (Interaction to Next Paint):** Target $\le 200\text{ms}$ (Good), $> 500\text{ms}$ (Poor) — Official W3C/Google replacement for legacy FID.
   - **TTFB (Time to First Byte):** Target $\le 800\text{ms}$ (Good) via W3C Navigation Timing Level 2.
3. **Observation-Masked Telemetry:**
   - Never dump thousands of CDP trace lines into context. Only output calculated metric scores and flagged slow endpoints (> 1500ms).

---

### Standard Playwright Performance Measurement

### Pattern A: W3C Navigation Timing Level 2 (Modern Performance Audit)
<!-- classification: illustrative -->
```typescript
import { test, expect } from '@playwright/test';

test('audit navigation timing level 2 and ttfb on dashboard', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');

  // W3C Navigation Timing Level 2 Standard
  const navTiming = await page.evaluate(() => {
    const navEntries = performance.getEntriesByType('navigation') as PerformanceNavigationTiming[];
    if (!navEntries || navEntries.length === 0) return null;
    const nav = navEntries[0];
    return {
      ttfb: Math.round(nav.responseStart - nav.requestStart),
      domContentLoaded: Math.round(nav.domContentLoadedEventEnd - nav.startTime),
      loadComplete: Math.round(nav.loadEventEnd - nav.startTime),
      transferSize: nav.transferSize,
    };
  });

  expect(navTiming).not.toBeNull();
  console.log(`[W3C NAV2] TTFB: ${navTiming?.ttfb}ms | DOM Loaded: ${navTiming?.domContentLoaded}ms`);
  expect(navTiming!.ttfb).toBeLessThan(800); // W3C Good TTFB threshold
});
```

### Pattern B: Measuring Interaction to Next Paint (INP) via PerformanceObserver
<!-- classification: illustrative -->
```typescript
test('audit interaction to next paint (INP) on button click', async ({ page }) => {
  await page.goto('/checkout');
  await page.waitForLoadState('networkidle');

  // Inject W3C PerformanceObserver tracking event durations
  await page.evaluate(() => {
    (window as any).__maxEventDuration = 0;
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const duration = (entry as any).duration;
        if (duration > (window as any).__maxEventDuration) {
          (window as any).__maxEventDuration = duration;
        }
      }
    });
    observer.observe({ type: 'event', buffered: true, durationThreshold: 16 } as any);
  });

  // Perform realistic user interaction
  await page.locator('#submit-order-button').click();
  await page.waitForTimeout(500); // Allow interaction cycle to complete

  const maxInp = await page.evaluate(() => (window as any).__maxEventDuration || 0);
  console.log(`[CORE WEB VITALS] Measured INP: ${maxInp}ms`);
  expect(maxInp).toBeLessThan(200); // Google/W3C INP budget <= 200ms
});
```

### Pattern C: CDP Network Throttling & Fast 3G Simulation
<!-- classification: illustrative -->
```typescript
test('simulate fast 3g conditions and 4x cpu slowdown', async ({ page }) => {
  const client = await page.context().newCDPSession(page);

  // Emulate mobile network conditions (Fast 3G: 1.6 Mbps download, 750 kbps upload, 150ms latency)
  await client.send('Network.emulateNetworkConditions', {
    offline: false,
    latency: 150,
    downloadThroughput: (1.6 * 1024 * 1024) / 8,
    uploadThroughput: (750 * 1024) / 8,
  });

  // Emulate 4x CPU slowdown (budget mobile CPU emulation)
  await client.send('Emulation.setCPUThrottlingRate', { rate: 4 });

  await page.goto('/catalog');
  await page.waitForLoadState('networkidle');
});
```

### Pattern D: Tracking Slow Network Endpoints
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
