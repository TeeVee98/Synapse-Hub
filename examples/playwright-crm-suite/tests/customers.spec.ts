import { test, expect } from '@playwright/test';
import { CustomerPage } from '../pages/CustomerPage';
import { BasePage } from '../pages/BasePage';

test.describe('Customer Management — Clean POM & Idempotent Teardown', () => {
  let customerPage: CustomerPage;
  const createdCustomerNames: string[] = [];

  test.beforeEach(async ({ page }) => {
    customerPage = new CustomerPage(page);
    await customerPage.navigate();
  });

  test.afterEach(async () => {
    // Teardown: Clean up created entities to prevent test junk accumulation
    for (const name of createdCustomerNames) {
      await customerPage.deleteCustomerByName(name);
    }
    createdCustomerNames.length = 0;
  });

  test('TC-CUST-01: Create new customer with unique identifier', async () => {
    const customerName = BasePage.uniqueCode('CUST_');
    const customerPhone = '0987654321';
    createdCustomerNames.push(customerName);

    await customerPage.createCustomer(customerName, customerPhone);
    await expect(customerPage.toastSuccess).toBeVisible();

    await customerPage.searchCustomer(customerName);
    await expect(customerPage.tableRows.first()).toContainText(customerName);
  });
});
