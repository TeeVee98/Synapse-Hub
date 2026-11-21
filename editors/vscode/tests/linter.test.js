// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

const assert = require('assert');
const { lintDocumentText } = require('../src/linter');
const { DIAGNOSTIC_CODES } = require('../src/constants');

console.log('🧪 Starting Synapse Hub VS Code Extension Unit Tests...\n');

let passCount = 0;
let failCount = 0;

function it(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passCount++;
  } catch (err) {
    console.error(`  ✗ ${name}`);
    console.error(`    ${err.message}`);
    failCount++;
  }
}

// 1. Static Sleep Tests
it('Detects Playwright page.waitForTimeout', () => {
  const code = "await page.waitForTimeout(5000);";
  const diags = lintDocumentText(code, 'typescript', 'tests/e2e.spec.ts', null);
  const found = diags.find(d => d.code === DIAGNOSTIC_CODES.STATIC_SLEEP);
  assert.ok(found, 'Expected STATIC_SLEEP diagnostic for waitForTimeout');
});

it('Detects Cypress cy.wait with static milliseconds', () => {
  const code = "cy.get('.btn').click(); cy.wait(3000);";
  const diags = lintDocumentText(code, 'javascript', 'tests/cypress.spec.js', null);
  const found = diags.find(d => d.code === DIAGNOSTIC_CODES.STATIC_SLEEP);
  assert.ok(found, 'Expected STATIC_SLEEP diagnostic for cy.wait');
});

it('Detects Python time.sleep', () => {
  const code = "time.sleep(2.5)";
  const diags = lintDocumentText(code, 'python', 'tests/test_flow.py', null);
  const found = diags.find(d => d.code === DIAGNOSTIC_CODES.STATIC_SLEEP);
  assert.ok(found, 'Expected STATIC_SLEEP diagnostic for time.sleep');
});

it('Detects Java/Groovy Thread.sleep', () => {
  const code = "Thread.sleep(1000)";
  const diags = lintDocumentText(code, 'groovy', 'Scripts/LoginTest.groovy', null);
  const found = diags.find(d => d.code === DIAGNOSTIC_CODES.STATIC_SLEEP);
  assert.ok(found, 'Expected STATIC_SLEEP diagnostic for Thread.sleep');
});

// 2. Tautology & Fake Pass Tests
it('Detects expect(true).toBe(true) and expect(false).toBe(false)', () => {
  const code = "expect(true).toBe(true);\nexpect(false).toBe(false);";
  const diags = lintDocumentText(code, 'typescript', 'tests/test.spec.ts', null);
  const tautologies = diags.filter(d => d.code === DIAGNOSTIC_CODES.TAUTOLOGY);
  assert.strictEqual(tautologies.length, 2, 'Expected 2 TAUTOLOGY diagnostics');
});

it('Detects expect(1).toBe(1)', () => {
  const code = "expect(1).toBe(1);";
  const diags = lintDocumentText(code, 'javascript', 'tests/test.spec.js', null);
  const found = diags.find(d => d.code === DIAGNOSTIC_CODES.TAUTOLOGY);
  assert.ok(found, 'Expected TAUTOLOGY diagnostic for expect(1).toBe(1)');
});

it('Detects Python assert True and assert 1 == 1', () => {
  const code = "assert True\nassert 1 == 1";
  const diags = lintDocumentText(code, 'python', 'tests/test_auth.py', null);
  const tautologies = diags.filter(d => d.code === DIAGNOSTIC_CODES.TAUTOLOGY);
  assert.strictEqual(tautologies.length, 2, 'Expected 2 TAUTOLOGY diagnostics for Python');
});

// 3. Swallowed Exceptions & Dummy Suppressions
it('Detects Python except pass and except _ = err', () => {
  const code = "try:\n    do_work()\nexcept Exception:\n    pass\n\ntry:\n    do_work()\nexcept Exception:\n    _ = err";
  const diags = lintDocumentText(code, 'python', 'tests/test_api.py', null);
  const swallowed = diags.filter(d => d.code === DIAGNOSTIC_CODES.SWALLOWED_EXCEPTION);
  assert.strictEqual(swallowed.length, 2, 'Expected 2 SWALLOWED_EXCEPTION diagnostics for Python');
});

it('Detects JavaScript empty catch and dummy suppression', () => {
  const code = "try { fn(); } catch (e) {}\ntry { fn(); } catch (e) { const _ = e; }";
  const diags = lintDocumentText(code, 'typescript', 'tests/test_ui.spec.ts', null);
  const swallowed = diags.filter(d => d.code === DIAGNOSTIC_CODES.SWALLOWED_EXCEPTION);
  assert.strictEqual(swallowed.length, 2, 'Expected 2 SWALLOWED_EXCEPTION diagnostics for JavaScript');
});

// 4. Clean POM Raw Selector Violations
it('Detects raw XPath in test script', () => {
  const code = "await page.locator('//button[@id=\"login\"]').click();";
  const diags = lintDocumentText(code, 'typescript', 'tests/e2e.spec.ts', null);
  const found = diags.find(d => d.code === DIAGNOSTIC_CODES.CLEAN_POM_VIOLATION);
  assert.ok(found, 'Expected CLEAN_POM_VIOLATION for raw xpath in test file');
});

// 5. Unawaited Expect in Playwright
it('Detects unawaited expect in Playwright test', () => {
  const code = "expect(page.locator('.title')).toBeVisible();";
  const diags = lintDocumentText(code, 'typescript', 'tests/e2e.spec.ts', null);
  const found = diags.find(d => d.code === DIAGNOSTIC_CODES.UNAWAITED_EXPECT);
  assert.ok(found, 'Expected UNAWAITED_EXPECT diagnostic');
});

console.log(`\n==================================================`);
console.log(`Total: ${passCount + failCount} | Passed: ${passCount} | Failed: ${failCount}`);
console.log(`==================================================`);

if (failCount > 0) {
  process.exit(1);
} else {
  console.log('🎉 All VS Code Extension Unit Tests Passed Successfully!\n');
}
