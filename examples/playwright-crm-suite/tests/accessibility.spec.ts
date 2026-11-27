// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
// SPDX-License-Identifier: MIT

import * as fs from 'fs';
import * as http from 'http';
import * as path from 'path';
import { test, expect, Page } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { CustomerPage } from '../pages/CustomerPage';

const LOGIN_HTML = `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>CRM Login</title></head>
<body>
  <main>
    <h1>Sign In</h1>
    <div id="error-banner" class="alert alert-danger" role="alert" aria-live="assertive" style="display:none;"></div>
    <form id="login-form" action="/admin/" method="post">
      <input type="hidden" name="csrf_token_name" value="csrf_hermetic_token_123456" />
      <label for="email">Email Address</label>
      <input id="email" name="email" type="email" required />
      <label for="password">Password</label>
      <input id="password" name="password" type="password" required />
      <label for="remember"><input id="remember" type="checkbox" /> Remember me</label>
      <button id="btn-submit" type="submit">Login</button>
      <a href="/admin/authentication/forgot_password">Forgot Password?</a>
    </form>
  </main>
  <script>
    const form = document.getElementById('login-form');
    const err = document.getElementById('error-banner');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const email = document.getElementById('email').value.trim();
      const pw = document.getElementById('password').value.trim();
      if (!email || !pw) {
        err.textContent = !email ? 'The Email Address field is required.' : 'The Password field is required.';
        err.style.display = 'block';
        return;
      }
      window.location.href = '/admin/';
    });
  </script>
</body>
</html>`;

const DASHBOARD_HTML = `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Dashboard</title></head>
<body>
  <header>
    <ul><li class="header-user-profile"><a href="#profile" class="profile">Admin Profile</a></li></ul>
  </header>
  <main><h1>Dashboard</h1><a href="/admin/clients">Customers</a></main>
</body>
</html>`;

const CLIENTS_HTML = `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Customers</title></head>
<body>
  <main>
    <h1>Customers</h1>
    <div class="panel-body">Customers Summary: 1 Active</div>
    <a id="open-contact-modal" href="#contact" class="btn new-contact" role="button">New Contact</a>
    <table id="clients"><thead><tr><th>Company</th></tr></thead><tbody><tr><td>Synapse QA</td></tr></tbody></table>
    <div id="contact" class="modal" role="dialog" aria-modal="true" aria-labelledby="contact-title" hidden>
      <h2 id="contact-title">Add New Contact</h2>
      <label for="firstname">First Name</label>
      <input id="firstname" name="firstname" type="text" />
      <button id="save-contact" type="submit" class="btn-primary">Save</button>
      <button id="close-contact" type="button" data-dismiss="modal">Close</button>
    </div>
  </main>
  <script>
    const trapped = new URLSearchParams(window.location.search).get('trap') === '1';
    const trigger = document.getElementById('open-contact-modal');
    const modal = document.getElementById('contact');
    const firstInput = document.getElementById('firstname');
    const closeBtn = document.getElementById('close-contact');
    if (trapped) {
      closeBtn.setAttribute('tabindex', '-1');
      firstInput.addEventListener('keydown', (e) => {
        if (e.key === 'Tab' || e.key === 'Escape') {
          e.preventDefault();
          e.stopPropagation();
          firstInput.focus();
        }
      });
    }
    function openModal(e) {
      e.preventDefault();
      modal.hidden = false;
      firstInput.focus();
    }
    function closeModal() {
      modal.hidden = true;
      trigger.focus();
    }
    trigger.addEventListener('click', openModal);
    closeBtn.addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
      if (!trapped && e.key === 'Escape' && !modal.hidden) closeModal();
    });
  </script>
</body>
</html>`;

async function probeKeyboardEscapeOrFocusAdvance(page: Page, activeId: string): Promise<boolean> {
  await page.keyboard.press('Tab');
  const nextId = await page.evaluate(() => document.activeElement?.id || '');
  return nextId !== activeId;
}

test.describe('CRM Accessibility Pilot — Keyboard, Announcements & Dialog Focus', () => {
  let server: http.Server | null = null;
  let localBaseUrl = '';

  test.beforeAll(async () => {
    const useLive = (process.env.SYNAPSE_WEB_MODE || 'offline').toLowerCase() === 'staging' && !!process.env.BASE_URL;
    if (useLive) {
      localBaseUrl = (process.env.BASE_URL || '').replace(/\/$/, '');
      return;
    }
    server = http.createServer((req, res) => {
      const urlPath = (req.url || '/').split('?')[0];
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      if (urlPath === '/admin/' || urlPath === '/admin') {
        res.end(DASHBOARD_HTML);
      } else if (urlPath.startsWith('/admin/clients')) {
        res.end(CLIENTS_HTML);
      } else {
        res.end(LOGIN_HTML);
      }
    });
    await new Promise<void>((resolve) => {
      server!.listen(0, '127.0.0.1', () => resolve());
    });
    const addr = server.address();
    if (addr && typeof addr !== 'string') {
      localBaseUrl = `http://127.0.0.1:${addr.port}`;
    }
  });

  test.afterAll(async ({}, testInfo) => {
    if (server) {
      await new Promise<void>((resolve) => server!.close(() => resolve()));
      server = null;
    }
    const receiptPath = path.resolve(__dirname, '../reports/a11y_receipt.json');
    fs.mkdirSync(path.dirname(receiptPath), { recursive: true });
    const reviewer = process.env.SYNAPSE_A11Y_REVIEWER || null;
    const readerVersion = process.env.SYNAPSE_READER_VERSION || null;
    const humanSigned = Boolean(reviewer && readerVersion);
    const receipt = {
      build_id: process.env.GITHUB_SHA || 'local',
      browser: testInfo.project.name || 'chromium',
      journeys: ['keyboard-sign-in-and-validation', 'customer-dialog-focus-restore'],
      reader_version: readerVersion || 'pending-human-observation',
      human_reviewer: reviewer,
      human_evidence_status: humanSigned ? 'verified' : 'pending',
      status: testInfo.status === 'passed' ? 'automated_passed' : 'failed',
    };
    fs.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2), 'utf-8');
  });

  test('A11Y-01: Keyboard-only sign-in and validation error live-region announcement via LoginPage POM', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.navigate(`${localBaseUrl}/admin/authentication`);
    await loginPage.disableFormValidation();

    // Negative keyboard submission: submit empty email and verify live alert announcement
    await loginPage.txtEmail.focus();
    await expect(loginPage.txtEmail).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(loginPage.txtPassword).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(loginPage.chkRemember).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(loginPage.btnSubmit).toBeFocused();
    await page.keyboard.press('Enter');

    await expect(loginPage.alertError).toBeVisible();
    await expect(loginPage.alertError).toHaveAttribute('role', 'alert');
    await expect(loginPage.alertError).toHaveAttribute('aria-live', 'assertive');
    await expect(loginPage.alertError).toContainText('Email Address field is required');

    // Positive keyboard-only sign-in completion
    await loginPage.txtEmail.focus();
    await page.keyboard.type('qa_pilot@synapse.test');
    await page.keyboard.press('Tab');
    await expect(loginPage.txtPassword).toBeFocused();
    await page.keyboard.type('StrongPass!2026');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await expect(loginPage.btnSubmit).toBeFocused();
    await page.keyboard.press('Enter');

    await expect(page).toHaveURL(/\/admin\/$/);
    await expect(loginPage.profileDropdown).toBeVisible();
  });

  test('A11Y-02: Customer contact dialog keyboard open, focus entry, Escape close & focus restore via CustomerPage POM', async ({ page }) => {
    const customerPage = new CustomerPage(page);
    await customerPage.navigate(`${localBaseUrl}/admin/clients`);

    await expect(customerPage.btnNewContact).toBeVisible();
    await customerPage.btnNewContact.focus();
    await expect(customerPage.btnNewContact).toBeFocused();
    await page.keyboard.press('Enter');

    await expect(customerPage.modalContact).toBeVisible();
    await expect(customerPage.modalContact).toHaveAttribute('role', 'dialog');
    await expect(customerPage.modalContact).toHaveAttribute('aria-modal', 'true');
    await expect(customerPage.txtContactFirstName).toBeFocused();

    // Tab forward inside dialog reaches Save and Close controls cleanly
    await page.keyboard.press('Tab');
    await expect(customerPage.btnContactSave).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(customerPage.btnCloseContactModal).toBeFocused();

    // Escape closes dialog and restores focus back to triggering control
    await page.keyboard.press('Escape');
    await expect(customerPage.modalContact).toBeHidden();
    await expect(customerPage.btnNewContact).toBeFocused();
  });

  test('A11Y-03: Negative guard fails when focus is trapped or close button is unreachable by keyboard', async ({ page }) => {
    const customerPage = new CustomerPage(page);
    await customerPage.navigate(`${localBaseUrl}/admin/clients?trap=1`);

    await customerPage.btnNewContact.focus();
    await page.keyboard.press('Enter');
    await expect(customerPage.txtContactFirstName).toBeFocused();

    const advanced = await probeKeyboardEscapeOrFocusAdvance(page, 'firstname');
    expect(advanced).toBe(false);
    await page.keyboard.press('Escape');
    await expect(customerPage.modalContact).toBeVisible();
    await expect(customerPage.btnCloseContactModal).toHaveAttribute('tabindex', '-1');
  });
});
