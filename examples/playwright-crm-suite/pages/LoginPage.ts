// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * LoginPage — Clean POM Page Class encapsulating authentication flows for Perfex CRM.
 * Follows the 6-Tier locator priority (ARIA > TestID > ID/Name > Semantic CSS).
 * Flat Architecture: Direct 1-level inheritance from BasePage.
 */
export class LoginPage extends BasePage {
  // --- Locators (Tier 1 & Tier 3: ARIA / HTML Identifiers) ---
  readonly txtEmail: Locator;
  readonly txtPassword: Locator;
  readonly chkRemember: Locator;
  readonly btnSubmit: Locator;
  readonly linkForgotPassword: Locator;
  readonly alertError: Locator;
  readonly alertSuccess: Locator;
  readonly headingTitle: Locator;
  readonly csrfTokenInput: Locator;
  readonly profileDropdown: Locator;
  readonly menuItemDashboard: Locator;
  readonly linkLogout: Locator;

  // Forgot Password page locators
  readonly txtForgotEmail: Locator;
  readonly btnForgotConfirm: Locator;
  readonly alertForgotResult: Locator;

  constructor(page: Page) {
    super(page);

    // Form inputs & controls
    this.txtEmail = page.locator('input#email');
    this.txtPassword = page.locator('input#password');
    this.chkRemember = page.locator('input#remember');
    this.btnSubmit = page.locator('button[type="submit"]');
    this.linkForgotPassword = page.locator('a[href*="forgot_password"]');

    // Feedback & Alerts
    this.alertError = page.locator('.alert.alert-danger');
    this.alertSuccess = page.locator('.alert.alert-success');
    this.headingTitle = page.locator('h1');
    this.csrfTokenInput = page.locator('input[name="csrf_token_name"]');

    // Dashboard navigation & user session elements
    this.profileDropdown = page.locator('li.header-user-profile a.profile, a.dropdown-toggle.profile').first();
    this.menuItemDashboard = page.locator('li.menu-item-dashboard, a.profile').first();
    this.linkLogout = page.locator('li.header-user-profile li.header-logout a, a:has-text("Logout")').first();

    // Forgot Password form controls
    this.txtForgotEmail = page.locator('input#email');
    this.btnForgotConfirm = page.locator('button[type="submit"]');
    this.alertForgotResult = page.locator('.alert').first();
  }

  /**
   * Navigate to the CRM Authentication screen.
   */
  async navigate(path: string = '/admin/authentication'): Promise<void> {
    await this.page.goto(path);
    await this.waitForDomLoaded();
  }

  /**
   * Perform end-to-end login business action.
   */
  async login(email: string, password: string, remember: boolean = false): Promise<void> {
    await this.fillCredentials(email, password);
    if (remember) {
      await this.toggleRememberMe(true);
    }
    await this.submit();
  }

  /**
   * Fill email and password input fields without submitting.
   */
  async fillCredentials(email: string, password: string): Promise<void> {
    await this.txtEmail.fill(email);
    await this.txtPassword.fill(password);
  }

  /**
   * Toggle the "Remember me" checkbox.
   */
  async toggleRememberMe(check: boolean = true): Promise<void> {
    const isChecked = await this.chkRemember.isChecked();
    if (check !== isChecked) {
      await this.chkRemember.setChecked(check);
    }
  }

  /**
   * Click the Login submit button.
   */
  async submit(): Promise<void> {
    await this.btnSubmit.click();
    await this.waitForDomLoaded();
  }

  /**
   * Navigate to the Forgot Password screen via link.
   */
  async clickForgotPassword(): Promise<void> {
    await this.linkForgotPassword.click();
    await this.waitForDomLoaded();
  }

  /**
   * Submit email in Forgot Password form.
   */
  async submitForgotPassword(email: string): Promise<void> {
    await this.txtForgotEmail.fill(email);
    await this.btnForgotConfirm.click();
    await this.waitForDomLoaded();
  }

  /**
   * Log out from the current authenticated session.
   */
  async logout(): Promise<void> {
    // Open profile dropdown
    if (await this.profileDropdown.isVisible()) {
      await this.profileDropdown.click();
      await this.waitForDomLoaded();
    }
    if (await this.linkLogout.isVisible()) {
      await this.linkLogout.click();
    }

    // Handle timer warning popup if present in demo AUT
    const timerLogoutConfirm = this.page.locator('.modal:visible a[href*="logout"], .modal:visible a:has-text("Logout"), a:has-text("Logout without stopping timers")');
    if (await timerLogoutConfirm.count() > 0) {
      await timerLogoutConfirm.first().click();
    }

    // Direct fallback navigation to ensure session termination
    if (this.page.url().includes('/admin/') && !this.page.url().includes('authentication')) {
      await this.page.goto('/admin/authentication/logout');
    }
    await this.waitForNetworkIdle();
  }

  /**
   * Extracts error message text from the danger alert banner.
   */
  async getErrorMessage(): Promise<string> {
    if (await this.alertError.first().isVisible()) {
      return (await this.alertError.allInnerTexts()).join(' ');
    }
    return '';
  }

  /**
   * Reads CSRF token value from DOM hidden input.
   */
  async getCsrfTokenValue(): Promise<string> {
    return (await this.csrfTokenInput.getAttribute('value')) || '';
  }

  /**
   * Verifies if the password input has type='password' (masked).
   */
  async isPasswordMasked(): Promise<boolean> {
    const inputType = await this.txtPassword.getAttribute('type');
    return inputType === 'password';
  }

  /**
   * Reads HTML5 browser validation message for client-side validation checks.
   */
  async getHtml5ValidationMessage(field: 'email' | 'password'): Promise<string> {
    const locator = field === 'email' ? this.txtEmail : this.txtPassword;
    return await locator.evaluate((el: HTMLInputElement) => el.validationMessage);
  }

  /**
   * Checks whether the current page represents an authenticated state.
   */
  async isLoggedIn(): Promise<boolean> {
    return this.page.url().includes('/admin/') && !this.page.url().includes('authentication');
  }

  /**
   * Disables browser HTML5 form validation to test backend validation rules directly.
   */
  async disableFormValidation(): Promise<void> {
    await this.page.evaluate(() => document.querySelector('form')?.setAttribute('novalidate', 'true'));
  }
}
