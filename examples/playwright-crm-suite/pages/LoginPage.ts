import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * LoginPage — Encapsulates login elements using Tier 1 ARIA accessible roles and names.
 */
export class LoginPage extends BasePage {
  readonly txtUsername: Locator;
  readonly txtPassword: Locator;
  readonly btnSubmit: Locator;
  readonly alertError: Locator;

  constructor(page: Page) {
    super(page);
    this.txtUsername = page.getByLabel('Tên đăng nhập', { exact: false });
    this.txtPassword = page.getByLabel('Mật khẩu', { exact: false });
    this.btnSubmit = page.getByRole('button', { name: 'Đăng nhập' });
    this.alertError = page.getByRole('alert');
  }

  async navigate(): Promise<void> {
    await this.page.goto('/login');
    await this.waitForNetworkIdle();
  }

  async login(username: string, password: string): Promise<void> {
    await this.txtUsername.fill(username);
    await this.txtPassword.fill(password);
    await this.btnSubmit.click();
    await this.waitForSpinnerToDisappear();
  }
}
