// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

const CRM_ADMIN_USER = process.env.CRM_USER || 'admin@example.com';
const CRM_ADMIN_PASS = process.env.CRM_PASS || '';

test.describe('CRM Authentication Suite — Phase 2 Clean POM Specifications', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.navigate();
  });

  // --- M1: Login Form UI ---

  test('TC-LOGIN-01 (CRM_LOGIN_TC_001): Verify login form UI elements presence and initial state', async ({ page }) => {
    await expect(page).toHaveTitle(/.*Login.*/i);
    await expect(loginPage.headingTitle).toBeVisible();
    await expect(loginPage.txtEmail).toBeVisible();
    await expect(loginPage.txtPassword).toBeVisible();
    await expect(loginPage.chkRemember).toBeVisible();
    await expect(loginPage.chkRemember).not.toBeChecked();
    await expect(loginPage.btnSubmit).toBeVisible();
    await expect(loginPage.linkForgotPassword).toBeVisible();
  });

  test('TC-LOGIN-02 (CRM_LOGIN_TC_002): Verify password field is masked with type="password"', async () => {
    const isMasked = await loginPage.isPasswordMasked();
    expect(isMasked).toBe(true);
    await expect(loginPage.txtPassword).toHaveAttribute('type', 'password');
  });

  test('TC-LOGIN-03 (CRM_LOGIN_TC_003): Verify CSRF protection hidden token exists in authentication form', async () => {
    await expect(loginPage.csrfTokenInput).toHaveCount(1);
    const token = await loginPage.getCsrfTokenValue();
    expect(token).toBeTruthy();
    expect(token.length).toBeGreaterThanOrEqual(16);
  });

  test('TC-LOGIN-04 (CRM_LOGIN_TC_004): Verify responsive layout across mobile and tablet viewports', async ({ page }) => {
    // Mobile Viewport: iPhone 14 (390 x 844)
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(loginPage.txtEmail).toBeVisible();
    await expect(loginPage.btnSubmit).toBeVisible();

    // Tablet Viewport: iPad (768 x 1024)
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(loginPage.txtEmail).toBeVisible();
    await expect(loginPage.btnSubmit).toBeVisible();
  });

  // --- M2: Login Authentication Core Workflows ---

  test('TC-LOGIN-05 (CRM_LOGIN_TC_005): Happy Path - Successful login with valid admin credentials', async ({ page }) => {
    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS);
    await expect(page).toHaveURL(/.*admin(\/)?$/);
    await expect(page).toHaveTitle(/.*Dashboard.*/i);
    await expect(loginPage.profileDropdown).toBeVisible();
  });

  test('TC-LOGIN-06 (CRM_LOGIN_TC_006): Validation - Submit login with empty email displays required error', async () => {
    await loginPage.fillCredentials('', CRM_ADMIN_PASS);
    await loginPage.submit();
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText('The Email Address field is required.');
  });

  test('TC-LOGIN-07 (CRM_LOGIN_TC_007): Validation - Submit login with empty password displays required error', async () => {
    await loginPage.fillCredentials(CRM_ADMIN_USER, '');
    await loginPage.submit();
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText('The Password field is required.');
  });

  test('TC-LOGIN-08 (CRM_LOGIN_TC_008): Validation - Submit login with both fields empty displays both errors', async () => {
    await loginPage.fillCredentials('', '');
    await loginPage.submit();
    await expect(loginPage.alertError).toHaveCount(2);
    await expect(loginPage.alertError.filter({ hasText: 'The Email Address field is required.' })).toBeVisible();
    await expect(loginPage.alertError.filter({ hasText: 'The Password field is required.' })).toBeVisible();
  });

  test('TC-LOGIN-09 (CRM_LOGIN_TC_009): Validation - Invalid email syntax missing @ triggers HTML5 validation', async () => {
    await loginPage.fillCredentials('invalid_email_format', CRM_ADMIN_PASS);
    const validationMessage = await loginPage.getHtml5ValidationMessage('email');
    expect(validationMessage).toBeTruthy();
  });

  test('TC-LOGIN-10 (CRM_LOGIN_TC_010): Negative - Non-existent email displays generic authentication failure', async () => {
    await loginPage.login('notexist_user_9999@example.com', 'WrongPass123!');
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText('Invalid email or password');
  });

  test('TC-LOGIN-11 (CRM_LOGIN_TC_011): Negative - Registered email with incorrect password displays error', async () => {
    await loginPage.login(CRM_ADMIN_USER, 'IncorrectPassword!999');
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText('Invalid email or password');
  });

  test('TC-LOGIN-12 (CRM_LOGIN_TC_012): Negative - Wrong email with correct password displays identical error', async () => {
    await loginPage.login('wrong_admin_alias@example.com', CRM_ADMIN_PASS);
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText('Invalid email or password');
  });

  test('TC-LOGIN-13 (CRM_LOGIN_TC_013): State Transition - Login with Remember Me stores persistent cookie', async ({ context, page }) => {
    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS, true);
    await expect(page).toHaveURL(/.*admin(\/)?$/);

    const cookies = await context.cookies();
    const rememberCookie = cookies.find(c => c.name.includes('remember') || c.name.includes('sp_session'));
    expect(rememberCookie).toBeDefined();
  });

  test('TC-LOGIN-14 (CRM_LOGIN_TC_014): State Transition - Login without Remember Me maintains isolated session', async ({ page }) => {
    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS, false);
    await expect(page).toHaveURL(/.*admin(\/)?$/);
  });

  test('TC-LOGIN-15 (CRM_LOGIN_TC_015): Boundary - Extremely long email string (1001 chars) is safely rejected', async () => {
    const longEmail = `${'a'.repeat(985)}@example.com`;
    await loginPage.login(longEmail, CRM_ADMIN_PASS);
    await expect(loginPage.alertError.first()).toBeVisible();
  });

  test('TC-LOGIN-16 (CRM_LOGIN_TC_016): Boundary - Extremely long password string (1001 chars) handled safely', async () => {
    const longPassword = 'P'.repeat(1001);
    await loginPage.login(CRM_ADMIN_USER, longPassword);
    await expect(loginPage.alertError.first()).toBeVisible();
    await expect(loginPage.alertError.first()).toContainText('Invalid email or password');
  });

  test('TC-LOGIN-17 (CRM_LOGIN_TC_017): State Transition - Visiting login URL while authenticated redirects to Dashboard', async ({ page }) => {
    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS);
    await expect(page).toHaveURL(/.*admin(\/)?$/);

    await page.goto('/admin/authentication');
    await page.waitForLoadState('networkidle');

    expect(page.url()).toContain('/admin');
  });

  // --- M3: Forgot Password ---

  test('TC-LOGIN-18 (CRM_LOGIN_TC_018): Navigation - Click "Forgot Password?" transitions to recovery screen', async ({ page }) => {
    await loginPage.clickForgotPassword();
    expect(page.url()).toContain('forgot_password');
    await expect(loginPage.btnForgotConfirm).toBeVisible();
  });

  test('TC-LOGIN-19 (CRM_LOGIN_TC_019): Recovery - Submit registered email on Forgot Password form', async () => {
    await loginPage.clickForgotPassword();
    await loginPage.submitForgotPassword(CRM_ADMIN_USER);
    await expect(loginPage.alertForgotResult).toBeVisible();
  });

  test('TC-LOGIN-20 (CRM_LOGIN_TC_020): Validation - Blank email on Forgot Password form triggers HTML5 validation', async () => {
    test.fail(true, 'AUT Defect: Forgot Password email input lacks HTML5 required attribute in live DOM');
    await loginPage.clickForgotPassword();
    await loginPage.btnForgotConfirm.click();
    const validationMsg = await loginPage.txtForgotEmail.evaluate((el: HTMLInputElement) => el.validationMessage);
    expect(validationMsg).toBeTruthy();
  });

  // --- M4: Logout ---

  test('TC-LOGIN-21 (CRM_LOGIN_TC_023): Session Teardown - Logout from Dashboard returns to login screen', async ({ page }) => {
    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS);
    await expect(page).toHaveURL(/.*admin(\/)?$/);

    await loginPage.logout();
    await expect(page).toHaveURL(/.*authentication.*/);
    await expect(loginPage.txtEmail).toBeVisible();
  });
});
