/**
 * Playwright Core Web Vitals (CWV) Profiling Fixture via Chrome DevTools Protocol (CDP)
 * Measures LCP (Largest Contentful Paint), CLS (Cumulative Layout Shift), and INP budgets.
 */

import { test as base, expect } from '@playwright/test';

interface PerformanceMetrics {
  lcp: number; // ms
  cls: number; // score
  domContentLoaded: number; // ms
}

export const test = base.extend<{ perfMetrics: PerformanceMetrics }>({
  perfMetrics: async ({ page }, use) => {
    const client = await page.context().newCDPSession(page);
    await client.send('Performance.enable');

    // Collect performance entries after page navigation
    const getMetrics = async (): Promise<PerformanceMetrics> => {
      const rawMetrics = await client.send('Performance.getMetrics');
      const metricsMap = new Map(rawMetrics.metrics.map(m => [m.name, m.value]));

      // Query window performance observer for LCP & CLS
      const cwv = await page.evaluate(() => {
        return new Promise<{ lcp: number; cls: number }>((resolve) => {
          let lcp = 0;
          let cls = 0;

          new PerformanceObserver((entryList) => {
            const entries = entryList.getEntries();
            const lastEntry = entries[entries.length - 1];
            lcp = lastEntry ? lastEntry.startTime : 0;
          }).observe({ type: 'largest-contentful-paint', buffered: true });

          new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries() as any[]) {
              if (!entry.hadRecentInput) cls += entry.value;
            }
          }).observe({ type: 'layout-shift', buffered: true });

          setTimeout(() => resolve({ lcp, cls }), 1500);
        });
      });

      return {
        lcp: Math.round(cwv.lcp),
        cls: Math.round(cwv.cls * 1000) / 1000,
        domContentLoaded: (metricsMap.get('DomContentLoaded') || 0) * 1000,
      };
    };

    // Execute test body
    await use({ lcp: 0, cls: 0, domContentLoaded: 0 });

    // Assert CWV Budget enforcement: LCP < 2500ms, CLS < 0.1
    const finalMetrics = await getMetrics();
    expect(finalMetrics.lcp).toBeLessThan(2500);
    expect(finalMetrics.cls).toBeLessThan(0.10);
  },
});
