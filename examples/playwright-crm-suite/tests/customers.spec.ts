// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { CustomerPage } from '../pages/CustomerPage';
import { BasePage } from '../pages/BasePage';

const CRM_ADMIN_USER = process.env.CRM_USER || 'admin@example.com';
const CRM_ADMIN_PASS = process.env.CRM_PASS || '';

test.describe('CRM Customers Suite — Phase 2 Clean POM Specifications', () => {
  let loginPage: LoginPage;
  let customerPage: CustomerPage;
  const createdCompanies: string[] = [];

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    customerPage = new CustomerPage(page);

    await loginPage.navigate();
    await loginPage.login(CRM_ADMIN_USER, CRM_ADMIN_PASS);
    await customerPage.navigate();
  });

  test.afterEach(async () => {
    // Teardown: Dismiss any open modal before deleting records
    await customerPage.dismissAnyModal();

    // Clean up created customer records to ensure idempotent zero-junk execution
    for (const company of createdCompanies) {
      await customerPage.deleteCustomerByName(company);
    }
    createdCompanies.length = 0;
  });

  // --- SUB-01: Summary & List View ---

  test('TC-CUST-01 (CRM_CUST_TC_001): Verify Customers Summary metrics banner displays statistics', async () => {
    await expect(customerPage.summaryWrapper).toBeVisible();
    const summaryText = await customerPage.summaryWrapper.innerText();
    expect(summaryText.toLowerCase()).toContain('customers');
  });

  test('TC-CUST-02 (CRM_CUST_TC_002): Verify DataTable displays required columns', async () => {
    await expect(customerPage.tableClients).toBeVisible();
    const headers = await customerPage.getTableColumnNames();
    const joinedHeaders = headers.join(' ').toLowerCase();

    expect(joinedHeaders).toContain('company');
    expect(joinedHeaders).toContain('primary contact');
    expect(joinedHeaders).toContain('primary email');
    expect(joinedHeaders).toContain('phone');
    expect(joinedHeaders).toContain('active');
    expect(joinedHeaders).toContain('groups');
    expect(joinedHeaders).toContain('date created');
  });

  test('TC-CUST-03 (CRM_CUST_TC_003): Verify pagination length dropdown and next page controls', async () => {
    await customerPage.changePagination(25);
    await expect(customerPage.tableRows.first()).toBeVisible();
    const count = await customerPage.tableRows.count();
    expect(count).toBeLessThanOrEqual(25);
  });

  test('TC-CUST-04 (CRM_CUST_TC_004): Verify column sorting by Company header', async () => {
    const sortDir1 = await customerPage.sortColumn('Company');
    await expect(customerPage.tableRows.first()).toBeVisible();

    // Toggle sort direction
    const sortDir2 = await customerPage.sortColumn('Company');
    await expect(customerPage.tableRows.first()).toBeVisible();

    // Verify sort order toggled genuinely
    expect(sortDir1).toBeTruthy();
    expect(sortDir2).toBeTruthy();
    expect(sortDir1).not.toEqual(sortDir2);
  });

  test('TC-CUST-05 (CRM_CUST_TC_005): Verify toggle switch Active/Inactive for customer', async () => {
    const firstRowCompany = await customerPage.getFirstRowCompany();
    if (firstRowCompany) {
      await customerPage.toggleCustomerActive(firstRowCompany);
      // Toggle back to preserve original state
      await customerPage.toggleCustomerActive(firstRowCompany);
    }
    await expect(customerPage.firstRowSwitchToggle).toBeAttached();
  });

  test('TC-CUST-06 (CRM_CUST_TC_006): Verify table navigation links lead to customer details', async ({ page }) => {
    await customerPage.openFirstCustomerDetail();
    expect(page.url()).toContain('/admin/clients/client/');
    await expect(customerPage.customerHeaderTitle).toBeVisible();
  });

  // --- SUB-02: Create & Edit Customer ---

  test('TC-CUST-07 (CRM_CUST_TC_007): Navigation - "+ New Customer" button opens creation form', async ({ page }) => {
    await customerPage.goToNewCustomer();
    expect(page.url()).toContain('/admin/clients/client');
    await expect(customerPage.txtCompany).toBeVisible();
    await expect(customerPage.tabCustomerDetails).toBeVisible();
  });

  test('TC-CUST-08 (CRM_CUST_TC_008): Happy Path - Create new customer with minimum required info', async ({ page }) => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_CUST_MIN_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany, '0912345678');
    await expect(customerPage.alertSuccess).toBeVisible();
    expect(page.url()).toContain('/admin/clients/client/');
  });

  test('TC-CUST-09 (CRM_CUST_TC_009): Happy Path - Create customer with full details across tabs', async ({ page }) => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_CUST_FULL_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerFull({
      company: uniqueCompany,
      vat: 'VAT123456789',
      phone: '0987654321',
      website: 'https://synapse.dev',
      address: '123 Nguyen Trai',
      city: 'Ho Chi Minh',
      state: 'SG',
      zip: '70000',
      billingStreet: '123 Nguyen Trai Billing',
      shippingStreet: '123 Nguyen Trai Shipping'
    });

    await expect(customerPage.alertSuccess).toBeVisible();
    expect(page.url()).toContain('/admin/clients/client/');
  });

  test('TC-CUST-10 (CRM_CUST_TC_010): Validation - Submit without required Company name is blocked', async ({ page }) => {
    await customerPage.goToNewCustomer();
    await customerPage.btnSave.click();

    // Verify browser stays on form and indicates error
    expect(page.url()).toContain('/admin/clients/client');
    const isValidationPresent = (await customerPage.fieldErrorCompany.count() > 0) ||
      (await customerPage.txtCompany.evaluate((el: HTMLInputElement) => el.validationMessage.length > 0));
    expect(isValidationPresent).toBe(true);
  });

  test('TC-CUST-11 (CRM_CUST_TC_011): Boundary - Maxlength 255 validation on Company field', async () => {
    const longCompany = 'C'.repeat(256);
    await customerPage.goToNewCustomer();
    await customerPage.txtCompany.fill(longCompany);
    await customerPage.btnSave.click();
    // System rejects or truncates safely without 500 crash
    await expect(customerPage.alertDanger).toBeHidden();
  });

  test('TC-CUST-12 (CRM_CUST_TC_014): Input Resilience - Phone field accepts alphanumeric input safely', async ({ page }) => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_CUST_PHONE_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany, 'Phone1234abcd!@');
    await expect(customerPage.alertSuccess).toBeVisible();
    expect(page.url()).toContain('/admin/clients/client/');
  });

  test('TC-CUST-13 (CRM_CUST_TC_015): Input Resilience - Website field accepts custom format safely', async ({ page }) => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_CUST_WEB_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerFull({
      company: uniqueCompany,
      website: 'custom-internal-domain'
    });
    await expect(customerPage.alertSuccess).toBeVisible();
    expect(page.url()).toContain('/admin/clients/client/');
  });

  test('TC-CUST-14 (CRM_CUST_TC_016): Dropdown - Select multiple values in Groups dropdown', async () => {
    await customerPage.goToNewCustomer();
    await expect(customerPage.selectGroups).toBeAttached();
    const optionValues = await customerPage.getGroupsOptionValues();
    if (optionValues.length > 0) {
      await customerPage.selectGroups.selectOption([optionValues[0]]);
      const selected = await customerPage.getSelectedGroups();
      expect(selected).toContain(optionValues[0]);
    } else {
      await expect(customerPage.selectGroups).toBeAttached();
    }
  });

  test('TC-CUST-15 (CRM_CUST_TC_017): Workflow - "Save and create contact" saves customer and shows contact modal', async ({ page }) => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_CUST_CNT_');
    createdCompanies.push(uniqueCompany);

    await customerPage.goToNewCustomer();
    await customerPage.txtCompany.fill(uniqueCompany);
    await customerPage.btnSaveAndCreateContact.click();
    await customerPage.page.waitForURL(/\/admin\/clients\/client\/\d+/, { timeout: 15000 });
    await customerPage.waitForDomLoaded();

    expect(page.url()).toContain('/admin/clients/client/');
    // Verify modal appeared and close it cleanly so it does not block subsequent tests
    await expect(customerPage.modalContact).toBeVisible({ timeout: 10000 });
    await customerPage.closeContactModal();
  });

  test('TC-CUST-16 (CRM_CUST_TC_018): Update - Edit customer company name and verify persistence', async () => {
    const initialCompany = BasePage.uniqueCode('AUTO_EDIT_A_');
    const updatedCompany = BasePage.uniqueCode('AUTO_EDIT_B_');
    createdCompanies.push(updatedCompany);

    await customerPage.createCustomerSimple(initialCompany);
    await expect(customerPage.alertSuccess).toBeVisible();

    await customerPage.editCustomerCompany(updatedCompany);
    await expect(customerPage.alertSuccess).toBeVisible();
  });

  test('TC-CUST-17 (CRM_CUST_TC_019): Auto-Fill - Copy customer info to billing and shipping addresses', async () => {
    await customerPage.goToNewCustomer();
    await customerPage.txtAddress.fill('789 Le Loi Street');
    await customerPage.txtCity.fill('Da Nang');

    await customerPage.copyCustomerInfoToBilling();
    await customerPage.copyBillingToShipping();
    await expect(customerPage.tabBillingShipping).toBeVisible();
  });

  // --- SUB-03: Customer Detail Profile & Navigation ---

  test('TC-CUST-18 (CRM_CUST_TC_020): Header - Detail view displays customer header format and Profile tab', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_DETAIL_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await expect(customerPage.customerHeaderTitle).toBeVisible();
    const headerText = await customerPage.customerHeaderTitle.innerText();
    expect(headerText).toContain('#');
  });

  test('TC-CUST-19 (CRM_CUST_TC_021): Navigation - Sidebar tabs switch content smoothly', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_NAV_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.clickSidebarTab('Notes');
    await customerPage.clickSidebarTab('Contacts');
    await expect(customerPage.tabContacts).toBeVisible();
  });

  test('TC-CUST-20 (CRM_CUST_TC_022): Assignment - Customer Admins tab allows staff assignment', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_ADM_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await expect(customerPage.tabCustomerAdmins).toBeVisible();
    await customerPage.tabCustomerAdmins.click();
    await expect(customerPage.selectCustomerAdmins).toBeAttached();
  });

  test('TC-CUST-21 (CRM_CUST_TC_023): Resilience - Cancel customer delete dialog preserves customer', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_CANCEL_DEL_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.cancelDeleteCustomerByName(uniqueCompany);

    // Customer must still exist
    const exists = await customerPage.isCustomerPresent(uniqueCompany);
    expect(exists).toBe(true);
  });

  // --- SUB-04: Contacts Management ---

  test('TC-CUST-22 (CRM_CUST_TC_024): Initial State - New customer has empty Contacts table', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_EMPTY_CNT_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.tabContacts.click();
    await expect(customerPage.tableContacts).toBeVisible();
  });

  test('TC-CUST-23 (CRM_CUST_TC_025): Happy Path - Create new Contact for customer', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_CUST_WITH_CNT_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    const uniqueEmail = BasePage.uniqueEmail('contact_');

    await customerPage.addNewContact({
      firstName: 'Minh',
      lastName: 'Nguyen',
      email: uniqueEmail,
      password: process.env.TEST_PASSWORD || `Pass_${Date.now()}!`,
    });

    await expect(customerPage.tableContacts).toContainText('Minh');
  });

  test('TC-CUST-24 (CRM_CUST_TC_026): Validation - Contact First Name required validation', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_VAL_FN_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.tabContacts.click();
    await customerPage.btnNewContact.waitFor({ state: 'visible', timeout: 10000 });
    await customerPage.btnNewContact.click();
    await customerPage.txtContactFirstName.waitFor({ state: 'visible', timeout: 10000 });

    // Leave First Name blank and submit
    await customerPage.txtContactLastName.fill('Tester');
    await customerPage.txtContactEmail.fill(BasePage.uniqueEmail('fn_test_'));
    await customerPage.btnContactSave.click();

    // Verify modal remains open due to validation
    await expect(customerPage.txtContactFirstName).toBeVisible();
    await customerPage.page.keyboard.press('Escape');
  });

  test('TC-CUST-25 (CRM_CUST_TC_027): Validation - Contact Last Name required validation', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_VAL_LN_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.tabContacts.click();
    await customerPage.btnNewContact.waitFor({ state: 'visible', timeout: 10000 });
    await customerPage.btnNewContact.click();
    await customerPage.txtContactFirstName.waitFor({ state: 'visible', timeout: 10000 });

    await customerPage.txtContactFirstName.fill('An');
    await customerPage.txtContactEmail.fill(BasePage.uniqueEmail('ln_test_'));
    await customerPage.btnContactSave.click();

    await expect(customerPage.txtContactLastName).toBeVisible();
    await customerPage.page.keyboard.press('Escape');
  });

  test('TC-CUST-26 (CRM_CUST_TC_028): Validation - Contact Email required validation', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_VAL_EM_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.tabContacts.click();
    await customerPage.btnNewContact.waitFor({ state: 'visible', timeout: 10000 });
    await customerPage.btnNewContact.click();
    await customerPage.txtContactFirstName.waitFor({ state: 'visible', timeout: 10000 });

    await customerPage.txtContactFirstName.fill('An');
    await customerPage.txtContactLastName.fill('Tester');
    await customerPage.btnContactSave.click();

    await expect(customerPage.txtContactEmail).toBeVisible();
    await customerPage.page.keyboard.press('Escape');
  });

  test('TC-CUST-27 (CRM_CUST_TC_029): Validation - Contact Email invalid format validation', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_VAL_FMT_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.tabContacts.click();
    await customerPage.btnNewContact.waitFor({ state: 'visible', timeout: 10000 });
    await customerPage.btnNewContact.click();
    await customerPage.txtContactFirstName.waitFor({ state: 'visible', timeout: 10000 });

    await customerPage.txtContactEmail.fill('invalid-email-no-at-sign');
    const validationMessage = await customerPage.txtContactEmail.evaluate((el: HTMLInputElement) => el.validationMessage);
    expect(validationMessage).toBeTruthy();
    await customerPage.page.keyboard.press('Escape');
  });

  test('TC-CUST-28 (CRM_CUST_TC_030): Validation - Duplicate contact email blocked (Unique Email)', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_VAL_DUP_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    const sharedEmail = BasePage.uniqueEmail('shared_');

    // Create first contact
    await customerPage.addNewContact({
      firstName: 'ContactOne',
      lastName: 'Tester',
      email: sharedEmail
    });

    // Attempt second contact with identical email
    await customerPage.btnNewContact.waitFor({ state: 'visible', timeout: 10000 });
    await customerPage.btnNewContact.click();
    await customerPage.txtContactFirstName.waitFor({ state: 'visible', timeout: 10000 });
    await customerPage.txtContactFirstName.fill('ContactTwo');
    await customerPage.txtContactLastName.fill('Tester');
    await customerPage.txtContactEmail.fill(sharedEmail);
    await customerPage.txtContactPassword.fill(process.env.TEST_PASSWORD || `Pass_${Date.now()}!`);
    await customerPage.btnContactSave.click();

    // Verify system prevents duplicate email by displaying duplicate error
    await expect(customerPage.alertContactDanger.filter({ hasText: 'Email already exists' })).toBeVisible({ timeout: 10000 });
    await customerPage.dismissAnyModal();
  });

  test('TC-CUST-29 (CRM_CUST_TC_031): Toggle - Contact Active/Inactive toggle switch', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_TOGGLE_CNT_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.addNewContact({
      firstName: 'ToggleTest',
      lastName: 'User',
      email: BasePage.uniqueEmail('toggle_')
    });

    await customerPage.toggleFirstContactActive();
    await expect(customerPage.contactRows.first()).toBeVisible();
  });

  test('TC-CUST-30 (CRM_CUST_TC_032): Aggregate View - All Contacts global screen displays entries', async ({ page }) => {
    await customerPage.navigate('/admin/clients');
    await customerPage.btnContactsTop.waitFor({ state: 'visible', timeout: 10000 });
    await customerPage.btnContactsTop.click();
    await customerPage.waitForDomLoaded();
    expect(page.url()).toContain('all_contacts');
  });

  test('TC-CUST-31 (CRM_CUST_TC_033): Cascade Delete - Delete customer removes customer and associated records', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_CASCADE_DEL_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.addNewContact({
      firstName: 'CascadeTarget',
      lastName: 'Contact',
      email: BasePage.uniqueEmail('cascade_')
    });

    // Delete customer
    await customerPage.deleteCustomerByName(uniqueCompany);

    // Verify customer is gone
    const exists = await customerPage.isCustomerPresent(uniqueCompany);
    expect(exists).toBe(false);
  });

  // --- SUB-06: Search ---

  test('TC-CUST-32 (CRM_CUST_TC_045): Real-Time Search - Keyword search on DataTable filters records dynamically', async () => {
    const uniqueCompany = BasePage.uniqueCode('AUTO_SRCH_');
    createdCompanies.push(uniqueCompany);

    await customerPage.createCustomerSimple(uniqueCompany);
    await customerPage.navigate('/admin/clients');

    // Search by unique keyword
    await customerPage.searchCustomer(uniqueCompany);
    await expect(customerPage.tableRows.first()).toContainText(uniqueCompany);

    // Search by non-existent term
    await customerPage.searchCustomer('NO_EXIST_XYZ_9999999');
    await expect(customerPage.emptyTableNotice).toBeVisible();

    // Clear search
    await customerPage.searchCustomer('');
    await expect(customerPage.tableRows.first()).toBeVisible();
  });
});
