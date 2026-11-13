/**
 * Playwright Core Web Vitals (CWV) Profiling Fixture via Chrome DevTools Protocol (CDP)
 * Measures LCP (Largest Contentful Paint), CLS (Cumulative Layout Shift),
 * INP (Interaction to Next Paint), and TTFB (Time to First Byte) budgets with network/CPU throttling.
 */

import { test as base, expect } from '@playwright/test';

export interface PerformanceMetrics {
  lcp: number; // ms (< 2500ms)
  cls: number; // score (< 0.1)
  inp: number; // ms (< 200ms)
  ttfb: number; // ms (< 800ms)
  domContentLoaded: number; // ms
}

export interface CWVProfilerContext {
  getMetrics: () => Promise<PerformanceMetrics>;
}

export const test = base.extend<{ perfMetrics: CWVProfilerContext }>({
  perfMetrics: async ({ page }, use) => {
    const client = await page.context().newCDPSession(page);
    await client.send('Performance.enable');

    // Emulate realistic mobile/desktop network profile (Fast 3G profile)
    await client.send('Network.emulateNetworkConditions', {
      offline: false,
      latency: 150, // 150ms RTT
      downloadThroughput: (1.6 * 1024 * 1024) / 8, // 1.6 Mbps
      uploadThroughput: (750 * 1024) / 8, // 750 kbps
    });

    // Emulate mid-tier CPU throttling (4x CPU slowdown)
    await client.send('Emulation.setCPUThrottlingRate', { rate: 4 });

    // Initialize in-browser observers before navigation/interaction
    await page.addInitScript(() => {
      (window as any).__cwv_lcp = 0;
      (window as any).__cwv_cls = 0;
      (window as any).__cwv_inp = 0;

      // Observe LCP
      try {
        new PerformanceObserver((entryList) => {
          const entries = entryList.getEntries();
          const lastEntry = entries[entries.length - 1];
          if (lastEntry) (window as any).__cwv_lcp = lastEntry.startTime;
        }).observe({ type: 'largest-contentful-paint', buffered: true });
      } catch (e) {
        // unsupported in some headless modes
      }

      // Observe CLS
      try {
        new PerformanceObserver((entryList) => {
          for (const entry of entryList.getEntries() as any[]) {
            if (!entry.hadRecentInput) (window as any).__cwv_cls += entry.value;
          }
        }).observe({ type: 'layout-shift', buffered: true });
      } catch (e) {
        // unsupported in some headless modes
      }

      // Observe INP (Interaction to Next Paint via Event Timing API)
      try {
        new PerformanceObserver((entryList) => {
          for (const entry of entryList.getEntries() as any[]) {
            if (entry.duration > (window as any).__cwv_inp) {
              (window as any).__cwv_inp = entry.duration;
            }
          }
        }).observe({ type: 'event', durationThreshold: 40, buffered: true } as any);
      } catch (e) {
        // unsupported in some headless modes
      }
    });

    const getMetrics = async (): Promise<PerformanceMetrics> => {
      // Modern Navigation Timing Level 2 API
      const navTiming = await page.evaluate(() => {
        const navEntries = performance.getEntriesByType('navigation') as PerformanceNavigationTiming[];
        const nav = navEntries.length > 0 ? navEntries[0] : null;
        const ttfb = nav ? nav.responseStart - nav.requestStart : 0;
        const dcl = nav ? nav.domContentLoadedEventEnd - nav.startTime : 0;

        return {
          lcp: (window as any).__cwv_lcp || 0,
          cls: (window as any).__cwv_cls || 0,
          inp: (window as any).__cwv_inp || 0,
          ttfb: Math.max(0, ttfb),
          domContentLoaded: Math.max(0, dcl),
        };
      });

      return {
        lcp: Math.round(navTiming.lcp),
        cls: Math.round(navTiming.cls * 1000) / 1000,
        inp: Math.round(navTiming.inp),
        ttfb: Math.round(navTiming.ttfb),
        domContentLoaded: Math.round(navTiming.domContentLoaded),
      };
    };

    // Provide fixture context to test body
    await use({ getMetrics });

    // Final assertion against Google Core Web Vitals recommended budgets
    const finalMetrics = await getMetrics();
    if (finalMetrics.lcp > 0) {
      expect(finalMetrics.lcp).toBeLessThan(2500); // Good LCP < 2.5s
    }
    expect(finalMetrics.cls).toBeLessThan(0.10); // Good CLS < 0.1
    if (finalMetrics.inp > 0) {
      expect(finalMetrics.inp).toBeLessThan(200); // Good INP < 200ms
    }
  },
});
