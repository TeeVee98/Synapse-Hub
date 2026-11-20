// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { Page, Locator } from '@playwright/test';

/**
 * BasePage — Foundational Clean POM class for Playwright TypeScript suites.
 * Enforces dynamic random identifiers, resilient smart waits, and zero static sleeps.
 * Follows ISO/IEC/IEEE 29119-5 Keyword-Driven separation.
 */
export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Generates collision-free test data with monotonic timestamp and random entropy.
   */
  static uniqueCode(prefix: string = 'AUTO_'): string {
    return `${prefix}${Date.now()}_${Math.floor(Math.random() * 10000)}`;
  }

  /**
   * Generates unique email address for dynamic test fixtures.
   */
  static uniqueEmail(prefix: string = 'auto_'): string {
    return `${prefix}${Date.now()}_${Math.floor(Math.random() * 10000)}@synapse.test`;
  }

  /**
   * Smart wait for dynamic overlay detaching without static Thread.sleep.
   */
  async waitForSpinnerToDisappear(spinnerLocator?: Locator, timeout: number = 5000): Promise<void> {
    const target = spinnerLocator || this.page.locator('.p-loading-mask, .spinner-overlay, .loading-backdrop, #dt-loader, .dataTables_processing:visible');
    if (await target.count() > 0) {
      await target.first().waitFor({ state: 'detached', timeout });
    }
  }

  /**
   * Fast bounded wait for network idle with safe DOM-loaded fallback.
   * Avoids hanging on continuous polling apps like Perfex CRM timers.
   */
  async waitForNetworkIdle(timeout: number = 2000): Promise<void> {
    try {
      await this.page.waitForLoadState('networkidle', { timeout });
    } catch {
      await this.page.waitForLoadState('domcontentloaded');
    }
  }

  /**
   * Helper to wait for DOM content loaded.
   */
  async waitForDomLoaded(): Promise<void> {
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Dismisses any active bootstrap modal backdrop or dialog.
   */
  async dismissAnyModal(): Promise<void> {
    const backdrop = this.page.locator('.modal-backdrop');
    if (await backdrop.count() > 0) {
      await this.page.keyboard.press('Escape');
      if (await backdrop.count() > 0) {
        await backdrop.first().waitFor({ state: 'detached', timeout: 3000 });
      }
    }
  }

  /**
   * Global alert / notification message text extraction.
   */
  async getGlobalAlertText(): Promise<string> {
    const alert = this.page.locator('.alert, div[role="alert"]').first();
    if (await alert.isVisible()) {
      return (await alert.innerText()).trim();
    }
    return '';
  }
}
