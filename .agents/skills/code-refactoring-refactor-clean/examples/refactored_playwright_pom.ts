/**
 * Clean POM & Flat Architecture Refactoring Demonstration (Playwright TypeScript)
 * 
 * [BEFORE]: Legacy Anti-Pattern
 * Raw locators, static sleeps, and fragile XPaths mixed directly inside test script:
 * 
 *   test('login', async ({ page }) => {
 *     await page.fill('//input[@id="usr"]', 'admin');
 *     await page.waitForTimeout(3000); // Flaky sleep
 *     await page.click('//button[contains(text(), "Log In")]');
 *   });
 * 
 * [AFTER]: Clean POM Flat Architecture
 * 100% of DOM operations and smart waits encapsulated inside Page Class extending BasePage.
 */

import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly welcomeToast: Locator;

  constructor(page: Page) {
    this.page = page;
    // Layer 1: Resilient Accessibility locators (Role > Label > TestId)
    this.usernameInput = page.getByRole('textbox', { name: 'Username' });
    this.passwordInput = page.getByRole('textbox', { name: 'Password' });
    this.submitButton = page.getByRole('button', { name: 'Sign In' });
    this.welcomeToast = page.locator('.toast-success');
  }

  async navigate(): Promise<void> {
    await this.page.goto('/login');
    await this.page.waitForLoadState('domcontentloaded');
  }

  async login(username: string, pass: string): Promise<void> {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(pass);
    await this.submitButton.click();
    // Dynamic smart wait replacing static sleeps
    await this.page.waitForSelector('.loading-spinner', { state: 'detached' });
  }

  async verifyLoginSuccess(): Promise<void> {
    await expect(this.welcomeToast).toBeVisible();
    await expect(this.welcomeToast).toContainText('Welcome back');
  }
}
