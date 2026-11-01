#!/usr/bin/env python3
"""
Corpus Evaluator for Enterprise Fake-Pass Sentinel (Meta-Infer Style)
---------------------------------------------------------------------
Evaluates tools/infer_linter.py against a comprehensive benchmark corpus
of 50 realistic test scripts (clean vs flawed).
Computes empirical Precision, Recall, and F1-Score (Threshold >= 0.90).
"""

import os
import sys
import json
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import infer_linter

CORPUS_FILE = os.path.join(SCRIPT_DIR, "corpus_fake_pass.json")


def generate_benchmark_corpus():
    """Generates an authentic multi-framework benchmark corpus across Playwright TS, Pytest, Cypress, and Katalon Groovy."""
    snippets = []

    clean_samples = [
        # Playwright TS
        ("tests/auth_login.spec.ts", "import { test, expect } from '@playwright/test';\ntest('valid login', async ({ page }) => {\n  await page.goto('/login');\n  await page.fill('#user', 'admin');\n  await page.click('#submit');\n  await expect(page.locator('#dashboard')).toBeVisible();\n});", False),
        ("tests/table_pagination.spec.ts", "import { test, expect } from '@playwright/test';\ntest('pagination', async ({ page }) => {\n  await page.goto('/items');\n  await page.click('#next-page');\n  await expect(page.locator('.table-row')).toHaveCount(10);\n});", False),
        ("tests/cart_checkout.spec.ts", "import { test, expect } from '@playwright/test';\ntest('checkout flow', async ({ page }) => {\n  await page.goto('/cart');\n  await page.click('#checkout');\n  await expect(page.locator('#order-id')).toContainText('ORD-');\n});", False),
        ("tests/user_profile.spec.ts", "import { test, expect } from '@playwright/test';\ntest('edit profile', async ({ page }) => {\n  await page.goto('/profile');\n  await page.fill('#bio', 'QA Engineer');\n  await page.click('#save');\n  await expect(page.locator('#status-msg')).toHaveText('Profile Updated');\n});", False),
        ("tests/search_filter.spec.ts", "import { test, expect } from '@playwright/test';\ntest('filter products', async ({ page }) => {\n  await page.goto('/products');\n  await page.selectOption('#category', 'Electronics');\n  await expect(page.locator('.product-card')).not.toHaveCount(0);\n});", False),
        ("tests/dialog_handling.spec.ts", "import { test, expect } from '@playwright/test';\ntest('alert dialog', async ({ page }) => {\n  page.on('dialog', d => d.accept());\n  await page.click('#trigger-alert');\n  await expect(page.locator('#log')).toHaveText('Accepted');\n});", False),
        ("tests/drag_and_drop.spec.ts", "import { test, expect } from '@playwright/test';\ntest('dnd item', async ({ page }) => {\n  await page.goto('/board');\n  await page.dragAndDrop('#item-1', '#column-done');\n  await expect(page.locator('#column-done .card')).toHaveCount(1);\n});", False),

        # Pytest Python
        ("tests/test_api_client.py", "def test_get_users(client):\n    res = client.get('/api/v1/users')\n    assert res.status_code == 200\n    assert len(res.json()) > 0", False),
        ("tests/test_auth_tokens.py", "def test_refresh_token(auth_service):\n    token = auth_service.refresh('old_tok')\n    assert token is not None\n    assert token.startswith('eyJ')", False),
        ("tests/test_calculator.py", "def test_sum():\n    total = sum([10, 20, 30])\n    assert total == 60", False),
        ("tests/test_db_fixtures.py", "def test_user_creation(db_conn):\n    user_id = db_conn.insert('test@example.com')\n    assert user_id > 0\n    assert db_conn.find(user_id)['email'] == 'test@example.com'", False),
        ("tests/test_validation_schema.py", "def test_payload_validation(validator):\n    is_valid = validator.validate({'id': 1, 'name': 'QA'})\n    assert is_valid is True\n    assert validator.errors == []", False),
        ("tests/test_async_fetch.py", "async def test_fetch_status(http_client):\n    res = await http_client.get('/health')\n    assert res.status == 200\n    assert res.data['uptime'] > 0", False),
        ("tests/test_rate_limiter.py", "def test_rate_limit(limiter):\n    allowed = limiter.check_limit('user_10')\n    assert allowed is True\n    assert limiter.remaining('user_10') >= 0", False),

        # Cypress JS
        ("cypress/e2e/login.cy.js", "describe('Login', () => {\n  it('logs in user', () => {\n    cy.visit('/login');\n    cy.get('#username').type('admin');\n    cy.get('#submit').click();\n    cy.get('#dashboard').should('be.visible');\n  });\n});", False),
        ("cypress/e2e/orders.cy.js", "describe('Orders', () => {\n  it('lists orders', () => {\n    cy.visit('/orders');\n    cy.wait('@getOrders');\n    cy.get('.order-row').should('have.length.at.least', 1);\n  });\n});", False),
        ("cypress/e2e/navigation.cy.js", "describe('Nav', () => {\n  it('navigates to settings', () => {\n    cy.visit('/');\n    cy.get('#nav-settings').click();\n    cy.url().should('include', '/settings');\n  });\n});", False),
        ("cypress/e2e/form_validation.cy.js", "describe('Form', () => {\n  it('shows errors on empty submit', () => {\n    cy.visit('/register');\n    cy.get('#submit').click();\n    cy.get('.error-feedback').should('contain', 'Required');\n  });\n});", False),

        # Katalon Groovy
        ("Scripts/TC01_VerifyLogin.groovy", "WebUI.openBrowser('https://example.com/login')\nWebUI.setText(findTestObject('input_user'), 'admin')\nWebUI.click(findTestObject('btn_login'))\nassert WebUI.verifyElementPresent(findTestObject('txt_welcome'), 10)", False),
        ("Scripts/TC02_CreateOrder.groovy", "WebUI.click(findTestObject('btn_new_order'))\nWebUI.setText(findTestObject('input_code'), 'AUTO_100')\nWebUI.click(findTestObject('btn_save'))\nassert WebUI.verifyMatch(WebUI.getText(findTestObject('toast_msg')), '.*Success.*', true)", False),
        ("Scripts/TC03_DeleteProduct.groovy", "WebUI.click(findTestObject('btn_delete_first'))\nWebUI.click(findTestObject('btn_confirm'))\nassert WebUI.verifyElementNotPresent(findTestObject('row_first'), 5)", False),
        ("Scripts/TC04_ExportReport.groovy", "WebUI.click(findTestObject('btn_export_csv'))\nboolean downloaded = BasePage.waitForDownload('report.csv', 10)\nassert downloaded == true", False),

        # Clean Page Classes / Configs
        ("pages/LoginPage.ts", "export class LoginPage {\n  constructor(private page: any) {}\n  async login(u: string, p: string) {\n    await this.page.fill('#user', u);\n    await this.page.fill('#pass', p);\n    await this.page.click('#submit');\n  }\n}", False),
        ("pages/OrderPage.groovy", "class OrderPage extends BasePage {\n  static void createOrder(String id) {\n    WebUI.setText(findTestObject('code'), id)\n    WebUI.click(findTestObject('save'))\n  }\n}", False),
        ("playwright.config.ts", "import { defineConfig } from '@playwright/test';\nexport default defineConfig({ timeout: 30000, use: { baseURL: 'https://example.com' } });", False),
        ("conftest.py", "import pytest\n@pytest.fixture\ndef db_session():\n    session = create_session()\n    yield session\n    session.close()", False),
        ("helpers/data_generator.py", "import time\ndef unique_id():\n    return f'AUTO_{int(time.time())}'", False),
        ("pages/NavigationComponent.js", "class NavigationComponent {\n  gotoSettings() { cy.get('#settings').click(); }\n}\nmodule.exports = NavigationComponent;", False),
    ]

    defect_samples = [
        # Swallowed exceptions
        ("tests/defect_swallow_ts.spec.ts", "test('swallowed ts', async ({ page }) => {\n  try {\n    await page.click('#btn');\n  } catch (err) {}\n});", True),
        ("tests/test_defect_swallow_py_pass.py", "def test_swallow_pass():\n    try:\n        do_work()\n    except Exception:\n        pass", True),
        ("tests/test_defect_swallow_py_ellipsis.py", "def test_swallow_ellipsis():\n    try:\n        do_work()\n    except Exception:\n        ...", True),
        ("Scripts/defect_swallow_gr.groovy", "try {\n    WebUI.click(findTestObject('btn'))\n} catch (Exception e) {\n    // do nothing\n}", True),

        # Tautological assertions
        ("tests/defect_tautology_ts.spec.ts", "test('tautology ts', async () => {\n  expect(true).toBe(true);\n});", True),
        ("tests/test_defect_tautology_py.py", "def test_tautology_py():\n    x = 42\n    assert True", True),
        ("tests/test_defect_tautology_math.py", "def test_tautology_num():\n    val = 100\n    assert 1 == 1", True),
        ("Scripts/defect_tautology_gr.groovy", "WebUI.click(findTestObject('btn'))\nassert true", True),
        ("tests/defect_tautology_null.spec.ts", "test('null tautology', async () => {\n  expect(null).toBe(null);\n});", True),

        # Unawaited async assertions
        ("tests/defect_unawaited_visible.spec.ts", "test('unawaited 1', async ({ page }) => {\n  expect(page.locator('#msg')).toBeVisible();\n});", True),
        ("tests/defect_unawaited_text.spec.ts", "test('unawaited 2', async ({ page }) => {\n  expect(page.locator('h1')).toHaveText('Welcome');\n});", True),
        ("tests/defect_unawaited_count.spec.ts", "test('unawaited 3', async ({ page }) => {\n  expect(page.locator('.item')).toHaveCount(5);\n});", True),

        # Missing assertions in test scripts
        ("tests/defect_no_assert.spec.ts", "test('no assertion in ts test', async ({ page }) => {\n  await page.goto('/profile');\n  await page.click('#save');\n});", True),
        ("tests/test_defect_no_assert.py", "def test_missing_assertion(client):\n    client.post('/api/orders', json={'id': 10})\n    client.get('/api/orders')", True),
        ("Scripts/defect_no_assert_gr.groovy", "WebUI.openBrowser('https://example.com')\nWebUI.click(findTestObject('btn_pay'))\nWebUI.closeBrowser()", True),
        ("cypress/e2e/defect_no_assert.cy.js", "describe('Cypress defective', () => {\n  it('clicks without asserting', () => {\n    cy.visit('/page');\n    cy.get('#action').click();\n  });\n});", True),

        # Hard delay sleeps
        ("tests/defect_sleep_ts_5000.spec.ts", "test('excessive sleep 5s', async ({ page }) => {\n  await page.waitForTimeout(5000);\n  await expect(page.locator('#done')).toBeVisible();\n});", True),
        ("tests/test_defect_sleep_py.py", "import time\ndef test_hard_sleep():\n    time.sleep(4.5)\n    assert True is not False", True),
        ("Scripts/defect_sleep_gr.groovy", "WebUI.click(findTestObject('btn'))\nThread.sleep(4000)\nassert WebUI.verifyElementPresent(findTestObject('txt'), 5)", True),
        ("cypress/e2e/defect_wait_5000.cy.js", "describe('wait', () => {\n  it('waits 5s', () => {\n    cy.wait(5000);\n    cy.get('#ok').should('exist');\n  });\n});", True),

        # Variable delay sleeps
        ("tests/defect_var_sleep_ts.spec.ts", "test('var sleep', async ({ page }) => {\n  const delayMs = 3500;\n  await page.waitForTimeout(delayMs);\n  await expect(page.locator('#ready')).toBeVisible();\n});", True),
        ("Scripts/defect_var_sleep_gr.groovy", "int timeoutSec = 5;\nWebUI.delay(timeoutSec);\nassert WebUI.verifyElementPresent(findTestObject('btn'), 5)", True),
        ("tests/test_empty_test_script.py", "# Empty test script with no assertions\nimport os\nimport sys", True),
    ]

    all_samples = clean_samples + defect_samples
    for idx, (fname, code, is_defective) in enumerate(all_samples):
        snippets.append({
            "id": f"sample_{idx}_{os.path.basename(fname)}",
            "filename": fname,
            "code": code,
            "is_defective": is_defective,
            "extension": os.path.splitext(fname)[1]
        })

    return snippets


class TestCorpusPrecisionRecall(unittest.TestCase):
    """Measures Precision and Recall of infer_linter on 50 corpus samples."""

    @classmethod
    def setUpClass(cls):
        corpus = generate_benchmark_corpus()
        with open(CORPUS_FILE, "w", encoding="utf-8") as f:
            json.dump(corpus, f, indent=2)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(CORPUS_FILE):
            os.remove(CORPUS_FILE)

    def test_corpus_quality_metrics(self):
        with open(CORPUS_FILE, "r", encoding="utf-8") as f:
            corpus = json.load(f)

        self.assertGreaterEqual(len(corpus), 50, "Corpus must have at least 50 samples")

        tp = 0  # Defective correctly caught
        fp = 0  # Clean wrongly flagged
        tn = 0  # Clean correctly allowed
        fn = 0  # Defective missed

        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            for item in corpus:
                rel_filename = item.get("filename", item["id"])
                full_path = os.path.join(tmp_dir, rel_filename)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as tf:
                    tf.write(item["code"])

                res = infer_linter.analyze_script(full_path)
                has_defect = not res["is_clean"]
                expected_defect = item["is_defective"]

                if expected_defect and has_defect:
                    tp += 1
                elif not expected_defect and not has_defect:
                    tn += 1
                elif not expected_defect and has_defect:
                    fp += 1
                elif expected_defect and not has_defect:
                    fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        print(f"\n=======================================================")
        print(f"   CORPUS FAKE-PASS SENTINEL EVALUATION (50 SAMPLES)   ")
        print(f"=======================================================")
        print(f"  Total Samples : {len(corpus)}")
        print(f"  True Positive : {tp} | True Negative : {tn}")
        print(f"  False Positive: {fp} | False Negative: {fn}")
        print(f"  Precision     : {precision * 100:.1f}% (Required >= 90%)")
        print(f"  Recall        : {recall * 100:.1f}% (Required >= 90%)")
        print(f"  F1-Score      : {f1 * 100:.1f}%")
        print(f"=======================================================\n")

        self.assertGreaterEqual(precision, 0.90, f"Precision {precision:.2f} must be >= 0.90")
        self.assertGreaterEqual(recall, 0.90, f"Recall {recall:.2f} must be >= 0.90")


if __name__ == "__main__":
    unittest.main()
