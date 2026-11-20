// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { CustomerPage } from '../pages/CustomerPage';
import { BasePage } from '../pages/BasePage';

const CRM_ADMIN_USER = process.env.CRM_USER || 'admin@example.com';
const CRM_ADMIN_PASS = process.env.CRM_PASS || '';
const BASE_URL = process.env.CRM_BASE_URL || 'https://crm.anhtester.com';

test.describe('CRM Security, Concurrency & DAST Probes Suite — Phase 3 Specifications', () => {
  let loginPage: LoginPage;
  let customerPage: CustomerPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    customerPage = new CustomerPage(page);
    await loginPage.navigate();
  });

  test.afterEach(async () => {
    // Teardown: Dismiss any open modal cleanly via Clean POM method
    await loginPage.dismissAnyModal();
  });

  // =========================================================================
  // 1. AUTHENTICATION SECURITY PROBES (OWASP A03: Injection & A07: Auth Failures)
  // =========================================================================

  test('TC-SEC-01 (CRM_LOGIN_TC_025): DAST Injection - SQL Injection into Email field is safely neutralized', async ({ page }) => {
    const sqliPayload = "' OR 1=1 --";
    await loginPage.fillCredentials(sqliPayload, 'anything');

    // 1. Verify client-side HTML5 validation catches malformed email format
    const validationMessage = await loginPage.getHtml5ValidationMessage('email');
    expect(validationMessage).toBeTruthy();

    // 2. Bypass HTML5 client constraint to test backend SQLi defense
    await loginPage.disableFormValidation();
    await loginPage.submit();

    // Verify backend safe handling: no SQL syntax dump, backend validation error displayed
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText(/The Email Address field must contain a valid email address|Invalid email or password/);
    expect(page.url()).toContain('authentication');

    // Assert absence of SQL exception disclosure in DOM
    const bodyContent = await page.content();
    expect(bodyContent).not.toMatch(/SQL syntax|mysql_fetch|ORA-\d+|syntax error in query/i);
  });

  test('TC-SEC-02 (CRM_LOGIN_TC_026): DAST Injection - XSS Script Injection into Email field is neutralized', async ({ page }) => {
    let alertTriggered = false;
    page.once('dialog', async dialog => {
      alertTriggered = true;
      await dialog.dismiss();
    });

    const xssPayload = "<script>alert('XSS')</script>";
    await loginPage.fillCredentials(xssPayload, CRM_ADMIN_PASS);

    // 1. Verify client-side HTML5 validation catches invalid email syntax
    const validationMessage = await loginPage.getHtml5ValidationMessage('email');
    expect(validationMessage).toBeTruthy();

    // 2. Bypass client validation to verify server-side XSS defense
    await loginPage.disableFormValidation();
    await loginPage.submit();

    // Verify XSS dialog did not execute
    expect(alertTriggered).toBe(false);

    // Assert server-side rejection without 500 error
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText(/The Email Address field must contain a valid email address|Invalid email or password/);
  });

  test('TC-SEC-03 (CRM_LOGIN_TC_027): DAST Injection - SQL Injection into Password field is safely neutralized', async ({ page }) => {
    const sqliPassword = "' OR '1'='1";
    await loginPage.fillCredentials(CRM_ADMIN_USER, sqliPassword);
    await loginPage.submit();

    // Assert authentication failure without administrative bypass
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText('Invalid email or password');
    expect(page.url()).toContain('authentication');
    expect(page.url()).not.toContain('/admin/dashboard');

    const bodyContent = await page.content();
    expect(bodyContent).not.toMatch(/SQL syntax|mysql_fetch|ORA-\d+|syntax error in query/i);
  });

  test('TC-SEC-04 (CRM_LOGIN_TC_028): CSRF Defense - Request with tampered CSRF token is rejected with HTTP 403 or 419', async ({ request }) => {
    // Attempt direct POST with tampered CSRF token
    const response = await request.post(`${BASE_URL}/admin/authentication`, {
      form: {
        csrf_token_name: 'tampered_malicious_csrf_token_value_99999',
        email: CRM_ADMIN_USER,
        password: process.env.TEST_PASSWORD || `WrongPass_${Date.now()}!`,
      },
      headers: {
        'Referer': `${BASE_URL}/admin/authentication`,
      },
    });

    // Server must reject request with HTTP 403 Forbidden or HTTP 419 Page Expired
    expect([403, 419]).toContain(response.status());
    const bodyText = await response.text();
    expect(bodyText).toMatch(/419 Page Expired|The action you have requested is not allowed/i);
    expect(bodyText).not.toContain('menu-item-dashboard');
  });

  test('TC-SEC-05 (CRM_LOGIN_TC_029): Resilience - Rapid sequential authentication attempts execute without server crash', async ({ page }) => {
    // Execute 4 rapid negative attempts in succession
    for (let i = 0; i < 4; i++) {
      await loginPage.fillCredentials(`stress_user_${i}@example.com`, 'WrongPass123!');
      await loginPage.btnSubmit.click();
      await page.waitForLoadState('domcontentloaded');
      await expect(loginPage.alertError.first()).toBeVisible();
      await expect(loginPage.alertError.first()).toContainText('Invalid email or password');
    }
    // Verify system stability remains 100% operational
    expect(page.url()).toContain('authentication');
    await expect(loginPage.btnSubmit).toBeVisible();
  });

  test('TC-SEC-06 (CRM_LOGIN_TC_030): User Enumeration Defense - Error messages are identical for existing vs non-existing users', async () => {
    // 1. Submit existing email with wrong password
    await loginPage.fillCredentials(CRM_ADMIN_USER, 'IncorrectPass#2026');
    await loginPage.submit();
    const existingUserError = await loginPage.getErrorMessage();

    // 2. Submit non-existing email with wrong password
    await loginPage.fillCredentials('definitely_non_existent_user_999@synapse.io', 'IncorrectPass#2026');
    await loginPage.submit();
    const nonExistingUserError = await loginPage.getErrorMessage();

    // Verify messages are identical to prevent username enumeration attacks
    expect(existingUserError).toBeTruthy();
    expect(nonExistingUserError).toBeTruthy();
    expect(existingUserError.trim()).toBe(nonExistingUserError.trim());
  });

  // =========================================================================
  // 2. CONCURRENCY & UNICODE NORMALIZATION (OWASP A04: Insecure Design)
  // =========================================================================

  test('TC-SEC-07 (CRM_LOGIN_TC_031): Concurrency - Rapid Double-Click on Login button executes safely without session clash', async ({ page }) => {
    await loginPage.fillCredentials(CRM_ADMIN_USER, CRM_ADMIN_PASS);

    // Rapid double-click in <300ms window using native dblclick
    await loginPage.btnSubmit.dblclick();

    // System must navigate to Dashboard smoothly without error 500 or duplicate session crash
    await page.waitForURL(/.*admin(\/)?$/, { timeout: 15000 });
    expect(page.url()).toContain('/admin');
    await expect(loginPage.menuItemDashboard).toBeVisible();
    await expect(page).toHaveTitle(/.*Dashboard.*/i);
  });

  test('TC-SEC-08 (CRM_LOGIN_TC_032): Unicode Normalization - Login handles Vietnamese NFD vs NFC safely', async ({ page }) => {
    // Vietnamese NFD (composed) string: h-o-\u0300-a = hoà
    const nfdEmail = 'ho\u0300a_bi\u0300nh@example.com';
    await loginPage.fillCredentials(nfdEmail, CRM_ADMIN_PASS);

    // 1. Check HTML5 client constraint
    const validationMessage = await loginPage.getHtml5ValidationMessage('email');
    expect(typeof validationMessage).toBe('string');

    // 2. Test server-side defense with novalidate to ensure backend processes safely
    await loginPage.disableFormValidation();
    await loginPage.submit();

    // Verify system processes Unicode cleanly without 500 server crash or encoding fault
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText(/The Email Address field must contain a valid email address|Invalid email or password/);
    const content = await page.content();
    expect(content).not.toMatch(/Malformed UTF-8|Character set error|Internal Server Error/i);
  });

  test('TC-SEC-09 (CRM_LOGIN_TC_024): Session Cache Defense - Browser Back button after logout does not restore active session', async ({ page }) => {
    // 1. Authenticate to Dashboard
    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS);
    await expect(page).toHaveURL(/.*admin(\/)?$/);

    // 2. Perform logout
    await loginPage.logout();
    await expect(page).toHaveURL(/.*authentication.*/);

    // 3. Trigger browser Back button
    await page.goBack();
    await page.waitForLoadState('domcontentloaded');

    // 4. Verify user cannot access private administrative features
    const isLoggedIn = await loginPage.isLoggedIn();
    if (isLoggedIn) {
      // If cached page renders, performing an action must redirect back to authentication
      await page.goto('/admin/clients');
      await page.waitForLoadState('domcontentloaded');
      expect(page.url()).toContain('authentication');
    } else {
      expect(page.url()).toContain('authentication');
    }
  });

  // =========================================================================
  // 3. BUSINESS DOMAIN SECURITY & CRUD INJECTION DEFENSE (CRM Customer)
  // =========================================================================

  test('TC-SEC-10 (CRM_CUST_TC_012): Stored XSS Defense - Script injection into Company name is safely sanitized and neutralized', async ({ page }) => {
    let alertFired = false;
    const xssListener = async (dialog: any) => {
      if (dialog.type() === 'alert') {
        alertFired = true;
        await dialog.dismiss();
      }
    };
    page.on('dialog', xssListener);

    const uniqueTag = `XSS_${Date.now().toString().slice(-6)}`;
    const xssPayload = `<script>alert('${uniqueTag}')</script>`;

    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS);
    await customerPage.navigate('/admin/clients');
    await customerPage.createCustomerSimple(xssPayload);

    // Verify alert dialog was NEVER triggered
    expect(alertFired).toBe(false);

    // Unregister XSS listener before teardown so delete dialog is handled exclusively
    page.off('dialog', xssListener);

    // Verify company name is sanitized in the form and rendered safely (tags stripped or neutralized)
    const companyInputVal = await customerPage.txtCompany.inputValue();
    expect(companyInputVal).toContain(uniqueTag);
    expect(companyInputVal).not.toContain('<script>');

    // Clean up created record
    await customerPage.deleteCustomerByName(uniqueTag);
  });

  test('TC-SEC-11 (CRM_CUST_TC_013): SQL Injection Defense - Malicious SQL payload in Company field is parameterized', async ({ page }) => {
    const uniqueTag = `SQLI_${Date.now().toString().slice(-6)}`;
    const sqliCompany = `Probe_${uniqueTag}' OR 1=1 --`;

    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS);
    await customerPage.navigate('/admin/clients');
    await customerPage.createCustomerSimple(sqliCompany);

    // Verify record was handled as literal string and stored safely without DB error
    const isPresent = await customerPage.isCustomerPresent(uniqueTag);
    expect(isPresent).toBe(true);

    const bodyContent = await page.content();
    expect(bodyContent).not.toMatch(/SQL syntax|mysql_fetch|ORA-\d+/i);

    // Clean up created record
    await customerPage.deleteCustomerByName(uniqueTag);
  });

  test('TC-SEC-12 (CRM_CUST_TC_044): Concurrency & Mass Action - Bulk actions modal safely dismisses without state corruption', async () => {
    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS);
    await customerPage.navigate('/admin/clients');

    // 1. Open Bulk Actions modal via Clean POM method
    await customerPage.openBulkActionsModal();
    await expect(customerPage.chkMassDelete).toBeAttached();

    // 2. Dismiss modal without executing actions via Clean POM method
    await customerPage.closeBulkActionsModal();

    // 3. Verify DataTable remains healthy and interactable
    await expect(customerPage.tableClients).toBeVisible();
  });

  // =========================================================================
  // 4. DAST SENTINEL, HEADERS & SESSION ATTRIBUTES (OWASP Top 10 Passive Scans)
  // =========================================================================

  test('TC-SEC-13 (DAST A05): Security Headers Audit - Inspect response headers for protective configurations', async ({ page }) => {
    const response = await page.goto('/admin/authentication');
    expect(response).not.toBeNull();
    const headers = response!.headers();

    // 1. Verify Content-Type is text/html with charset utf-8
    expect(headers['content-type']).toContain('text/html');
    expect(headers['content-type']).toContain('charset=utf-8');

    // 2. Sensitive auth cache defense: verify no-store / no-cache
    expect(headers['cache-control']).toMatch(/no-store|no-cache/);
    expect(headers['pragma']).toBe('no-cache');

    // 3. Passive audit: verify absence of leaking application frameworks in headers
    expect(headers['x-powered-by']).toBeUndefined();
    expect(headers['x-aspnet-version']).toBeUndefined();
  });

  test('TC-SEC-14 (DAST A01): Session Cookie Attributes - Verify session cookie flags and security scope', async ({ page, context }) => {
    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS);
    await expect(page).toHaveURL(/.*admin(\/)?$/);

    const cookies = await context.cookies();
    const sessionCookie = cookies.find(c => c.name.includes('session') || c.name.includes('sp_session'));

    expect(sessionCookie).toBeDefined();
    // Assert proper path scoping and security attributes
    expect(sessionCookie!.path).toBe('/');
    expect(sessionCookie!.httpOnly).toBe(true);
    expect(sessionCookie!.secure).toBe(true);
    expect(sessionCookie!.sameSite.toLowerCase()).toBe('lax');
  });

  test('TC-SEC-15 (DAST A04): ReDoS & Buffer Boundary - Extremely large input string (10,000 chars) handled safely', async ({ page }) => {
    const hugePayload = 'A'.repeat(10000);
    const startTime = Date.now();

    await loginPage.fillCredentials(hugePayload + '@example.com', CRM_ADMIN_PASS);
    await loginPage.submit();

    const elapsedTime = Date.now() - startTime;
    // Execution must complete within reasonable bounds (preventing catastrophic backtracking ReDoS)
    expect(elapsedTime).toBeLessThan(15000);

    // Verify page handled input safely without server crash
    expect(page.url()).toContain('authentication');
    await expect(loginPage.btnSubmit).toBeVisible();
    await expect(loginPage.alertError.first()).toBeVisible();

    const content = await page.content();
    expect(content).not.toMatch(/Fatal error|Allowed memory size of \d+ bytes exhausted|500 Internal Server Error/i);
  });

  test('TC-SEC-16 (DAST A01): Parameter Tampering Probe - Elevated privilege injection is rejected', async ({ page }) => {
    // Obtain valid CSRF token from active login session page
    const csrfToken = await loginPage.getCsrfTokenValue();

    // Attempt privilege tampering via direct POST parameter injection with wrong password
    const response = await page.request.post(`${BASE_URL}/admin/authentication`, {
      form: {
        csrf_token_name: csrfToken,
        email: CRM_ADMIN_USER,
        password: process.env.TEST_PASSWORD || `WrongPass_${Date.now()}!`,
        is_admin: '1',
        role_id: '1',
        super_admin: 'true',
      },
      headers: {
        'Referer': `${BASE_URL}/admin/authentication`,
      },
    });

    // Verify tampering with wrong password fails cleanly (cannot bypass authentication via role tampering)
    expect([200, 302, 401]).toContain(response.status());
    const bodyText = await response.text();
    expect(bodyText).not.toContain('menu-item-dashboard');
  });
});
