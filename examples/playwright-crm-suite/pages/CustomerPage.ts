// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

/**
 * CustomerPage — Encapsulates customer management workflows and table verification.
 */
export class CustomerPage extends BasePage {
  readonly btnCreate: Locator;
  readonly txtCustomerName: Locator;
  readonly txtCustomerPhone: Locator;
  readonly btnSave: Locator;
  readonly toastSuccess: Locator;
  readonly searchInput: Locator;
  readonly tableRows: Locator;

  constructor(page: Page) {
    super(page);
    this.btnCreate = page.getByRole('button', { name: 'Thêm mới' });
    this.txtCustomerName = page.getByLabel('Tên khách hàng', { exact: false });
    this.txtCustomerPhone = page.getByLabel('Số điện thoại', { exact: false });
    this.btnSave = page.getByRole('button', { name: 'Lưu' });
    this.toastSuccess = page.locator('.p-toast-message-success, .toast-success');
    this.searchInput = page.getByPlaceholder('Tìm kiếm khách hàng...');
    this.tableRows = page.locator('table tbody tr');
  }

  async navigate(): Promise<void> {
    await this.page.goto('/customers');
    await this.waitForNetworkIdle();
  }

  async createCustomer(name: string, phone: string): Promise<void> {
    await this.btnCreate.click();
    await this.txtCustomerName.fill(name);
    await this.txtCustomerPhone.fill(phone);
    await this.btnSave.click();
    await this.waitForSpinnerToDisappear();
  }

  async searchCustomer(keyword: string): Promise<void> {
    await this.searchInput.fill(keyword);
    await this.page.keyboard.press('Enter');
    await this.waitForNetworkIdle();
  }

  async deleteCustomerByName(name: string): Promise<void> {
    const row = this.page.locator(`tr:has-text("${name}")`);
    if (await row.count() > 0) {
      await row.getByRole('button', { name: 'Xóa' }).click();
      const confirmBtn = this.page.getByRole('button', { name: 'Xác nhận' });
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
      }
      await this.waitForSpinnerToDisappear();
    }
  }
}
