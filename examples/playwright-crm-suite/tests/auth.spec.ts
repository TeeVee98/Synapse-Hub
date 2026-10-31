import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

test.describe('Authentication Flow — Clean POM Reference', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.navigate();
  });

  test('TC-AUTH-01: Successful login with valid credentials', async ({ page }) => {
    await loginPage.login('admin@enterprise.local', 'SecurePass123!');
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('TC-AUTH-02: Show error message when password is invalid', async () => {
    await loginPage.login('admin@enterprise.local', 'WrongPassword');
    await expect(loginPage.alertError).toBeVisible();
    await expect(loginPage.alertError).toContainText('Tài khoản hoặc mật khẩu không chính xác');
  });
});
