// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { test, expect } from '@playwright/test';
import { CustomerContractAppPage } from '../pages/CustomerContractAppPage';
import { BasePage } from '../pages/BasePage';

test.describe('Customer Contract UI Suite — Hermetic Contract Verification', () => {
  let contractPage: CustomerContractAppPage;

  test.beforeEach(async ({ page }) => {
    contractPage = new CustomerContractAppPage(page);
    await contractPage.navigate();
  });

  test('TC-CONTRACT-01 (CUST_UI_001): Happy Path - Create customer with full valid details', async () => {
    const company = BasePage.uniqueCode('SYNAPSE_TECH_');
    const name = 'Nguyễn Văn A';
    const email = BasePage.uniqueEmail('contact_');
    const phone = '0912345678';

    await contractPage.createCustomer(company, name, email, phone);
    await expect(contractPage.alertSuccess).toBeVisible();
    await expect(contractPage.alertSuccess).toContainText('Khách hàng đã được tạo thành công');
    await expect(contractPage.alertError).toBeHidden();
  });

  test('TC-CONTRACT-02 (CUST_UI_002): Negative - Submit empty required fields triggers validation error', async () => {
    await contractPage.submitEmptyForm();
    await expect(contractPage.alertError).toBeVisible();
    await expect(contractPage.alertError).toContainText('Có lỗi xảy ra');
    await expect(contractPage.alertSuccess).toBeHidden();
  });

  test('TC-CONTRACT-03 (CUST_UI_003): Resilience - Disabled element cannot be clicked', async () => {
    await expect(contractPage.btnDisabled).toBeDisabled();
    // Attempting to click disabled button without force should throw timeout
    await expect(contractPage.clickDisabledButton()).rejects.toThrow();
  });

  test('TC-CONTRACT-04 (CUST_UI_004): Drift Detection - Non-existent locator is safely rejected', async () => {
    await expect(contractPage.ghostElement).toBeHidden();
    await expect(contractPage.ghostElement).toHaveCount(0);
  });

  test('TC-CONTRACT-05 (CUST_UI_005): Concurrency - Rapid double-click submit executes safely without crash', async () => {
    const company = BasePage.uniqueCode('CONCURRENCY_');
    const name = 'Trần Văn B';
    const email = BasePage.uniqueEmail('concur_');

    await contractPage.txtCompany.fill(company);
    await contractPage.txtName.fill(name);
    await contractPage.txtEmail.fill(email);

    await contractPage.doubleClickSubmit();
    await expect(contractPage.alertSuccess).toBeVisible();
  });
});
