// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import { Page, Locator } from '@playwright/test';
import { BasePage } from './BasePage';
import * as path from 'path';

/**
 * CustomerContractAppPage — Clean POM Page Class for the local contract app (customer_crm_app.html).
 * Provides hermetic verification for UI contracts, drift detection, and concurrency probes.
 * Flat Architecture: Direct 1-level inheritance from BasePage.
 */
export class CustomerContractAppPage extends BasePage {
  readonly txtCompany: Locator;
  readonly txtName: Locator;
  readonly txtEmail: Locator;
  readonly txtPhone: Locator;
  readonly txtVat: Locator;
  readonly txtWebsite: Locator;
  readonly selectStatus: Locator;
  readonly btnSubmit: Locator;
  readonly btnCancel: Locator;
  readonly btnDisabled: Locator;
  readonly alertSuccess: Locator;
  readonly alertError: Locator;
  readonly hiddenBox: Locator;
  readonly ghostElement: Locator;

  constructor(page: Page) {
    super(page);
    this.txtCompany = page.locator('#company');
    this.txtName = page.locator('#name');
    this.txtEmail = page.locator('#email');
    this.txtPhone = page.locator('#phone');
    this.txtVat = page.locator('#vat');
    this.txtWebsite = page.locator('#website');
    this.selectStatus = page.locator('#status');
    this.btnSubmit = page.locator('#btn-submit');
    this.btnCancel = page.locator('#btn-cancel');
    this.btnDisabled = page.locator('#btn-disabled');
    this.alertSuccess = page.locator('#alert-success');
    this.alertError = page.locator('#alert-error');
    this.hiddenBox = page.locator('#hidden-box');
    this.ghostElement = page.locator('#btn-ghost-non-existent');
  }

  /**
   * Navigate to the local customer_crm_app.html file.
   */
  async navigate(): Promise<void> {
    const filePath = path.resolve(__dirname, '../../practices/contracts/customer_crm_app.html');
    const fileUrl = `file:///${filePath.replace(/\\/g, '/')}`;
    await this.page.goto(fileUrl);
    await this.waitForDomLoaded();
  }

  /**
   * Fill and submit customer creation form.
   */
  async createCustomer(company: string, name: string, email: string, phone?: string): Promise<void> {
    await this.txtCompany.fill(company);
    await this.txtName.fill(name);
    await this.txtEmail.fill(email);
    if (phone) {
      await this.txtPhone.fill(phone);
    }
    await this.btnSubmit.click();
  }

  /**
   * Attempt to click the disabled button.
   */
  async clickDisabledButton(): Promise<void> {
    await this.btnDisabled.click({ timeout: 1000, force: false });
  }

  /**
   * Submit the form without filling required fields.
   */
  async submitEmptyForm(): Promise<void> {
    // Remove HTML5 novalidate or trigger submit handler directly to test server-side/JS validation
    await this.page.evaluate(() => {
      const form = document.getElementById('customer-form') as HTMLFormElement;
      if (form) {
        form.noValidate = true;
      }
    });
    await this.btnSubmit.click();
  }

  /**
   * Perform rapid double click (<200ms) on submit button to verify concurrency protection.
   */
  async doubleClickSubmit(): Promise<void> {
    await Promise.all([
      this.btnSubmit.click(),
      this.btnSubmit.click()
    ]);
  }
}
