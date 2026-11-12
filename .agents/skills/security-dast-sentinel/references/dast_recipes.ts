/**
 * DAST Automated Security Test Recipes (Playwright TypeScript)
 * Includes HTTP Security Headers auditing and BOLA / IDOR cross-tenant defense checks.
 */

import { test, expect } from '@playwright/test';

// 1. Automated Security Headers Audit
test('DAST: Verify mandatory HTTP security headers', async ({ page }) => {
  const response = await page.goto('/dashboard');
  expect(response).not.toBeNull();
  const headers = response!.headers();

  // Clickjacking & MIME Sniffing protection
  expect(['DENY', 'SAMEORIGIN']).toContain(headers['x-frame-options']?.toUpperCase());
  expect(headers['x-content-type-options']).toBe('nosniff');

  // Strict Transport Security & CSP
  if (page.url().startsWith('https://')) {
    expect(headers['strict-transport-security']).toContain('max-age=');
  }
  expect(headers['content-security-policy']).toBeTruthy();
});

// 2. BOLA / IDOR Defense Check (Multi-Tenant Authorization)
test('DAST: Tenant B cannot access Tenant A entity', async ({ request }) => {
  const tokenTenantB = process.env.TEST_TENANT_B_TOKEN || 'tenant_b_bearer_token';
  // Tenant B attempts to read Tenant A resource
  const readAttempt = await request.get('/api/v1/invoices/10042', {
    headers: { 'Authorization': `Bearer ${tokenTenantB}` }
  });
  expect([403, 404], 'Cross-tenant resource access must be forbidden').toContain(readAttempt.status());
});
