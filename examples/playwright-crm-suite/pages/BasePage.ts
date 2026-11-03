import { Page, Locator } from '@playwright/test';

/**
 * BasePage — Foundational Clean POM class for Playwright TypeScript suites.
 * Enforces dynamic random identifiers, resilient smart waits, and zero static sleeps.
 */
export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Generates collision-free test data with timestamps.
   */
  static uniqueCode(prefix: string = 'AUTO_'): string {
    return `${prefix}${Date.now()}_${Math.floor(Math.random() * 1000)}`;
  }

  /**
   * Smart wait for dynamic overlay detaching without static Thread.sleep.
   * Throws if spinner remains attached after timeout to surface hanging UI spinners early.
   */
  async waitForSpinnerToDisappear(spinnerLocator?: Locator, timeout: number = 10000): Promise<void> {
    const target = spinnerLocator || this.page.locator('.p-loading-mask, .spinner-overlay, .loading-backdrop');
    if (await target.count() > 0) {
      await target.first().waitFor({ state: 'detached', timeout });
    }
  }

  /**
   * Wait for network idle state.
   */
  async waitForNetworkIdle(timeout?: number): Promise<void> {
    await this.page.waitForLoadState('networkidle', timeout !== undefined ? { timeout } : undefined);
  }
}
