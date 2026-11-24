// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';

export interface CustomerData {
  company: string;
  vat?: string;
  phone?: string;
  website?: string;
  groups?: string[];
  currency?: string;
  language?: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  billingStreet?: string;
  billingCity?: string;
  billingState?: string;
  billingZip?: string;
  billingCountry?: string;
  shippingStreet?: string;
  shippingCity?: string;
  shippingState?: string;
  shippingZip?: string;
  shippingCountry?: string;
}

export interface ContactData {
  firstName: string;
  lastName: string;
  email: string;
  password?: string;
  phone?: string;
  title?: string;
}

/**
 * CustomerPage — Clean POM Page Class encapsulating customer CRUD, contacts, and table operations.
 * Strictly adheres to ISO/IEC/IEEE 29119-5 Keyword-Driven separation.
 * Flat Architecture: Direct 1-level inheritance from BasePage.
 */
export class CustomerPage extends BasePage {
  // --- List View & Header Elements ---
  readonly btnNewCustomer: Locator;
  readonly btnContactsTop: Locator;
  readonly tableClients: Locator;
  readonly tableHeaders: Locator;
  readonly searchInput: Locator;
  readonly tableRows: Locator;
  readonly paginationDropdown: Locator;
  readonly paginationNext: Locator;
  readonly summaryWrapper: Locator;

  // --- Customer Form Fields (Customer Details tab) ---
  readonly tabCustomerDetails: Locator;
  readonly txtCompany: Locator;
  readonly txtVat: Locator;
  readonly txtPhone: Locator;
  readonly txtWebsite: Locator;
  readonly selectGroups: Locator;
  readonly selectCurrency: Locator;
  readonly selectLanguage: Locator;
  readonly txtAddress: Locator;
  readonly txtCity: Locator;
  readonly txtState: Locator;
  readonly txtZip: Locator;
  readonly selectCountry: Locator;

  // --- Customer Form Fields (Billing & Shipping tab) ---
  readonly tabBillingShipping: Locator;
  readonly txtBillingStreet: Locator;
  readonly txtBillingCity: Locator;
  readonly txtBillingState: Locator;
  readonly txtBillingZip: Locator;
  readonly selectBillingCountry: Locator;
  readonly linkSameAsCustomer: Locator;
  readonly linkCopyBilling: Locator;
  readonly txtShippingStreet: Locator;
  readonly txtShippingCity: Locator;
  readonly txtShippingState: Locator;
  readonly txtShippingZip: Locator;
  readonly selectShippingCountry: Locator;

  // --- Form Action Buttons & Alerts ---
  readonly btnSave: Locator;
  readonly btnSaveAndCreateContact: Locator;
  readonly alertSuccess: Locator;
  readonly alertDanger: Locator;
  readonly fieldErrorCompany: Locator;

  // --- Detail View & Sidebar Navigation ---
  readonly customerHeaderTitle: Locator;
  readonly tabContacts: Locator;
  readonly tabCustomerAdmins: Locator;
  readonly selectCustomerAdmins: Locator;
  readonly btnSaveAdmins: Locator;
  readonly btnActionDelete: Locator;

  // --- Contacts Management Modal Elements ---
  readonly btnNewContact: Locator;
  readonly txtContactFirstName: Locator;
  readonly txtContactLastName: Locator;
  readonly txtContactEmail: Locator;
  readonly txtContactPassword: Locator;
  readonly btnContactSave: Locator;
  readonly tableContacts: Locator;
  readonly contactRows: Locator;
  readonly alertContactDanger: Locator;
  readonly btnBulkActions: Locator;
  readonly modalBulkAction: Locator;
  readonly chkMassDelete: Locator;
  readonly modalContact: Locator;
  readonly btnCloseContactModal: Locator;
  readonly firstRowSwitchToggle: Locator;
  readonly emptyTableNotice: Locator;

  constructor(page: Page) {
    super(page);

    // List View controls
    this.btnNewCustomer = page.locator('a[href$="/clients/client"], a[href*="/clients/client"]:not([href*="import"])')
      .or(page.getByRole('link', { name: /New Customer|Khách hàng mới/i }))
      .first();
    this.btnContactsTop = page.locator('a.btn:has-text("Contacts")').first();
    this.tableClients = page.locator('table#clients');
    this.tableHeaders = page.locator('table#clients th');
    this.searchInput = page.locator('#clients_filter input[type="search"]');
    this.tableRows = page.locator('table#clients tbody tr');
    this.paginationDropdown = page.locator('select[name="clients_length"]');
    this.paginationNext = page.locator('#clients_next a');
    this.summaryWrapper = page.locator('.panel-body').filter({ hasText: 'Customers Summary' }).first();

    // Customer Form: Details tab
    this.tabCustomerDetails = page.locator('.customer-tabs a[data-group="profile"], a[data-group="profile"], a[href="#contact_info"]').first();
    this.txtCompany = page.locator('input#company');
    this.txtVat = page.locator('input#vat');
    this.txtPhone = page.locator('input#phonenumber');
    this.txtWebsite = page.locator('input#website');
    this.selectGroups = page.locator('select[name="groups_in[]"]');
    this.selectCurrency = page.locator('select#default_currency');
    this.selectLanguage = page.locator('select#default_language');
    this.txtAddress = page.locator('textarea#address');
    this.txtCity = page.locator('input#city');
    this.txtState = page.locator('input#state');
    this.txtZip = page.locator('input#zip');
    this.selectCountry = page.locator('select#country');

    // Customer Form: Billing & Shipping tab
    this.tabBillingShipping = page.locator('a[href="#billing_and_shipping"]');
    this.txtBillingStreet = page.locator('textarea#billing_street');
    this.txtBillingCity = page.locator('input#billing_city');
    this.txtBillingState = page.locator('input#billing_state');
    this.txtBillingZip = page.locator('input#billing_zip');
    this.selectBillingCountry = page.locator('select#billing_country');
    this.linkSameAsCustomer = page.locator('.billing-same-as-customer, a:has-text("Same as Customer Info")').first();
    this.linkCopyBilling = page.locator('.customer-copy-billing-address, a:has-text("Copy Billing Address")').first();
    this.txtShippingStreet = page.locator('textarea#shipping_street');
    this.txtShippingCity = page.locator('input#shipping_city');
    this.txtShippingState = page.locator('input#shipping_state');
    this.txtShippingZip = page.locator('input#shipping_zip');
    this.selectShippingCountry = page.locator('select#shipping_country');

    // Action buttons & alerts — scoped strictly to visible elements
    this.btnSave = page.locator('button.only-save:visible').first();
    this.btnSaveAndCreateContact = page.locator('button.save-and-add-contact:visible').first();
    this.alertSuccess = page.locator('.float-alert.alert-success, .alert.alert-success, .alert-success').first();
    this.alertDanger = page.locator('.alert.alert-danger, .alert-danger').first();
    this.fieldErrorCompany = page.locator('#company-error, label#company-error, #company ~ p.text-danger, span.text-danger').first();

    // Customer Detail header & tabs
    this.customerHeaderTitle = page.locator('h4:has-text("#"), .client-heading, h4.tw-text-lg').first();
    this.tabContacts = page.locator('.customer-tabs a[data-group="contacts"], a[data-group="contacts"]').first();
    this.tabCustomerAdmins = page.locator('a[href="#customer_admins"], a[data-group="customer_admins"]').first();
    this.selectCustomerAdmins = page.locator('select[name="customer_admins[]"]');
    this.btnSaveAdmins = page.locator('form#customer_admins_form button[type="submit"], form[action*="assign_admins"] button[type="submit"]').first();
    this.btnActionDelete = page.locator('a.text-danger._delete, a[href*="/clients/delete"]').first();

    // Contacts Management modal elements
    this.btnNewContact = page.locator('a:has-text("New Contact"):not(.disabled), button:has-text("New Contact"):not(.disabled)').first();
    this.txtContactFirstName = page.locator('#contact input#firstname, #contact input[name="firstname"]').first();
    this.txtContactLastName = page.locator('#contact input#lastname, #contact input[name="lastname"]').first();
    this.txtContactEmail = page.locator('#contact input#email, #contact input[name="email"]').first();
    this.txtContactPassword = page.locator('#contact input[name="password"]').first();
    this.btnContactSave = page.locator('#contact button[type="submit"]:has-text("Save"), .modal:visible button[type="submit"]:has-text("Save")').first();
    this.tableContacts = page.locator('table.table-contacts, table#contacts').first();
    this.contactRows = page.locator('table.table-contacts tbody tr, table#contacts tbody tr');
    this.alertContactDanger = page.locator('#contact .alert-danger, #contact .text-danger, .modal:visible .text-danger, .modal:visible .alert-danger');

    // Bulk actions controls
    this.btnBulkActions = page.locator('a[data-target="#customers_bulk_action"], .bulk-actions-btn').first();
    this.modalBulkAction = page.locator('#customers_bulk_action').first();
    this.chkMassDelete = page.locator('#customers_bulk_action input#mass_delete, input[name="mass_delete"]').first();

    // Contact modal & additional table controls
    this.modalContact = page.locator('#contact');
    this.btnCloseContactModal = page.locator('#contact button:has-text("Close"), #contact .close').first();
    this.firstRowSwitchToggle = this.tableRows.first().locator('.onoffswitch-label, input.onoffswitch-checkbox').first();
    this.emptyTableNotice = this.tableClients.locator('.dataTables_empty, td:has-text("No matching records found")').first();
  }

  /**
   * Navigate to the CRM Customers list screen.
   */
  async navigate(path: string = '/admin/clients'): Promise<void> {
    await this.page.goto(path);
    await this.waitForDomLoaded();
  }

  /**
   * Navigate to the Add New Customer screen.
   */
  async goToNewCustomer(): Promise<void> {
    if (!this.page.url().includes('/admin/clients')) {
      await this.navigate('/admin/clients');
    }
    await this.btnNewCustomer.click();
    await this.waitForDomLoaded();
  }

  /**
   * Creates a customer with minimal required fields (Happy Path).
   */
  async createCustomerSimple(company: string, phone?: string): Promise<void> {
    await this.goToNewCustomer();
    await this.txtCompany.fill(company);
    if (phone) {
      await this.txtPhone.fill(phone);
    }
    await this.btnSave.click();
    await this.page.waitForURL(/\/admin\/clients\/client\/\d+/, { timeout: 15000 });
    await this.waitForDomLoaded();
  }

  /**
   * Creates a customer with comprehensive multi-tab data.
   */
  async createCustomerFull(data: CustomerData): Promise<void> {
    await this.goToNewCustomer();
    await this.txtCompany.fill(data.company);
    if (data.vat) await this.txtVat.fill(data.vat);
    if (data.phone) await this.txtPhone.fill(data.phone);
    if (data.website) await this.txtWebsite.fill(data.website);
    if (data.address) await this.txtAddress.fill(data.address);
    if (data.city) await this.txtCity.fill(data.city);
    if (data.state) await this.txtState.fill(data.state);
    if (data.zip) await this.txtZip.fill(data.zip);

    if (data.billingStreet || data.shippingStreet) {
      await this.tabBillingShipping.click();
      if (data.billingStreet) await this.txtBillingStreet.fill(data.billingStreet);
      if (data.shippingStreet) await this.txtShippingStreet.fill(data.shippingStreet);
    }

    await this.btnSave.click();
    await this.page.waitForURL(/\/admin\/clients\/client\/\d+/, { timeout: 15000 });
    await this.waitForDomLoaded();
  }

  /**
   * Auto-fill address using "Same as Customer Info" link.
   */
  async copyCustomerInfoToBilling(): Promise<void> {
    await this.tabBillingShipping.click();
    if (await this.linkSameAsCustomer.isVisible()) {
      await this.linkSameAsCustomer.click();
    }
  }

  /**
   * Auto-fill shipping address using "Copy Billing Address" link.
   */
  async copyBillingToShipping(): Promise<void> {
    await this.tabBillingShipping.click();
    if (await this.linkCopyBilling.isVisible()) {
      await this.linkCopyBilling.click();
    }
  }

  /**
   * Search customer in the DataTable using real-time search box.
   */
  async searchCustomer(keyword: string): Promise<void> {
    await this.searchInput.fill(keyword);
    await this.waitForNetworkIdle();
  }

  /**
   * Edit existing customer's company name.
   */
  async editCustomerCompany(newName: string): Promise<void> {
    await this.txtCompany.waitFor({ state: 'visible', timeout: 10000 });
    await this.txtCompany.fill(newName);
    await this.btnSave.click();
    await this.waitForDomLoaded();
  }

  /**
   * Delete customer by company name from DataTable with confirmation dialog acceptance.
   */
  async deleteCustomerByName(name: string): Promise<void> {
    await this.navigate('/admin/clients');
    await this.searchCustomer(name);

    const targetRow = this.tableRows.filter({ hasText: name }).first();
    if (await targetRow.count() > 0) {
      await targetRow.scrollIntoViewIfNeeded();
      await targetRow.hover();
      const deleteLink = targetRow.locator('a.text-danger._delete, a[href*="delete"]').first();

      if (await deleteLink.count() > 0) {
        this.page.once('dialog', async dialog => {
          await dialog.accept();
        });
        await deleteLink.click({ force: true });
        await this.waitForNetworkIdle();
        await this.waitForDomLoaded();
      }
    }
  }

  /**
   * Attempt to delete customer but cancel via dialog dismissal.
   */
  async cancelDeleteCustomerByName(name: string): Promise<void> {
    await this.navigate('/admin/clients');
    await this.searchCustomer(name);

    const targetRow = this.tableRows.filter({ hasText: name }).first();
    if (await targetRow.count() > 0) {
      await targetRow.scrollIntoViewIfNeeded();
      await targetRow.hover();
      const deleteLink = targetRow.locator('a.text-danger._delete, a[href*="delete"]').first();

      if (await deleteLink.count() > 0) {
        this.page.once('dialog', async dialog => {
          await dialog.dismiss();
        });
        await deleteLink.click({ force: true });
        await this.waitForNetworkIdle();
        await this.waitForDomLoaded();
      }
    }
  }

  /**
   * Open the Contact modal and add a new contact.
   */
  async addNewContact(contact: ContactData): Promise<void> {
    await this.tabContacts.click();
    await this.btnNewContact.waitFor({ state: 'visible', timeout: 10000 });
    await this.btnNewContact.click();
    await this.txtContactFirstName.waitFor({ state: 'visible', timeout: 10000 });

    await this.txtContactFirstName.fill(contact.firstName);
    await this.txtContactLastName.fill(contact.lastName);
    await this.txtContactEmail.fill(contact.email);
    const pwd = contact.password || `Contact_${Date.now()}!`;
    await this.txtContactPassword.fill(pwd);

    await this.btnContactSave.click();
    await this.tableContacts.filter({ hasText: contact.firstName }).first().waitFor({ state: 'visible', timeout: 15000 });
    await this.waitForDomLoaded();
  }

  /**
   * Navigate to the first customer in the table.
   */
  async openFirstCustomerDetail(): Promise<void> {
    await this.navigate('/admin/clients');
    const link = this.page.locator('table#clients tbody tr td a[href*="/clients/client/"]').first();
    await link.waitFor({ state: 'visible', timeout: 15000 });
    await link.click();
    await this.page.waitForURL(/\/admin\/clients\/client\/\d+/, { timeout: 15000 });
    await this.waitForDomLoaded();
  }

  /**
   * Click a specific sidebar tab on the customer detail screen.
   */
  async clickSidebarTab(tabName: string): Promise<void> {
    const groupKey = tabName.toLowerCase().replace(/\s+/g, '_');
    const tab = this.page.locator(`.customer-tabs a[data-group="${groupKey}"], a[data-group="${groupKey}"], a[href*="group=${groupKey}"]`).first();
    await tab.waitFor({ state: 'visible', timeout: 10000 });
    await tab.click();
    await this.waitForDomLoaded();
    await this.waitForNetworkIdle();
  }

  /**
   * Toggle the Active/Inactive switch for a customer in the DataTable.
   */
  async toggleCustomerActive(company: string): Promise<void> {
    await this.searchCustomer(company);
    const targetRow = this.tableRows.filter({ hasText: company }).first();
    const toggleSwitch = targetRow.locator('.onoffswitch-label, input[type="checkbox"]').first();
    if (await toggleSwitch.count() > 0) {
      await toggleSwitch.click();
      await this.waitForNetworkIdle();
    }
  }

  /**
   * Toggle the Active/Inactive switch for the first contact in the Contacts table.
   */
  async toggleFirstContactActive(): Promise<void> {
    const toggleLabel = this.contactRows.first().locator('label.onoffswitch-label').first();
    if (await toggleLabel.isVisible()) {
      await toggleLabel.click();
      await this.waitForNetworkIdle();
    }
  }

  /**
   * Change pagination length dropdown.
   */
  async changePagination(length: number): Promise<void> {
    if (await this.paginationDropdown.isVisible()) {
      await this.paginationDropdown.selectOption(String(length));
      await this.waitForNetworkIdle();
    }
  }

  /**
   * Sort table by clicking a specific column header and return updated sort state.
   */
  async sortColumn(columnName: string): Promise<string> {
    const header = this.tableHeaders.filter({ hasText: columnName }).first();
    const responsePromise = this.page.waitForResponse(
      res => res.url().includes('clients') && res.status() === 200,
      { timeout: 8000 }
    ).catch(() => null);
    await header.click();
    await responsePromise;
    await this.waitForDomLoaded();
    return (await header.getAttribute('aria-sort')) || (await header.getAttribute('class')) || '';
  }

  /**
   * Returns current sort direction or class for a column header.
   */
  async getColumnSortDirection(columnName: string): Promise<string> {
    const header = this.tableHeaders.filter({ hasText: columnName }).first();
    return (await header.getAttribute('aria-sort')) || (await header.getAttribute('class')) || '';
  }

  /**
   * Checks if customer company is visible in the DataTable.
   */
  async isCustomerPresent(company: string): Promise<boolean> {
    if (!this.page.url().endsWith('/admin/clients')) {
      await this.navigate('/admin/clients');
    }
    await this.searchCustomer(company);
    const count = await this.tableRows.filter({ hasText: company }).count();
    return count > 0;
  }

  /**
   * Gets the company name from the first row of DataTable.
   */
  async getFirstRowCompany(): Promise<string> {
    const firstRowCell = this.tableRows.first().locator('td:nth-child(3)');
    if (await firstRowCell.count() > 0) {
      return (await firstRowCell.innerText()).trim();
    }
    return '';
  }

  /**
   * Reads all table header column names.
   */
  async getTableColumnNames(): Promise<string[]> {
    return await this.tableHeaders.allInnerTexts();
  }

  /**
   * Opens the Bulk Actions modal.
   */
  async openBulkActionsModal(): Promise<void> {
    await this.btnBulkActions.dispatchEvent('click');
    await this.modalBulkAction.waitFor({ state: 'visible', timeout: 5000 });
  }

  /**
   * Closes the Bulk Actions modal cleanly.
   */
  async closeBulkActionsModal(): Promise<void> {
    const btnClose = this.modalBulkAction.locator('button:has-text("Close"), button.close').first();
    await btnClose.click();
    await this.modalBulkAction.waitFor({ state: 'hidden', timeout: 5000 });
  }

  /**
   * Closes the Contact creation/edit modal cleanly.
   */
  async closeContactModal(): Promise<void> {
    if (await this.btnCloseContactModal.isVisible()) {
      await this.btnCloseContactModal.click();
      await this.modalContact.waitFor({ state: 'hidden', timeout: 5000 });
    }
  }

  /**
   * Retrieves non-empty option values from Groups dropdown.
   */
  async getGroupsOptionValues(): Promise<string[]> {
    return await this.selectGroups.locator('option').evaluateAll(
      (opts: HTMLOptionElement[]) => opts.map(o => o.value).filter(v => v !== '')
    );
  }

  /**
   * Retrieves currently selected option values from Groups dropdown.
   */
  async getSelectedGroups(): Promise<string[]> {
    return await this.selectGroups.evaluate((el: HTMLSelectElement) =>
      Array.from(el.selectedOptions).map(o => o.value)
    );
  }
}
