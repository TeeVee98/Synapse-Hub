// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

/**
 * Diagnostic codes and error signatures used by the Synapse Hub in-editor linter.
 */
const DIAGNOSTIC_CODES = {
  STATIC_SLEEP: 'synapse-static-sleep',
  TAUTOLOGY: 'synapse-tautology',
  SWALLOWED_EXCEPTION: 'synapse-swallowed-exception',
  CLEAN_POM_VIOLATION: 'synapse-clean-pom-violation',
  EMPTY_TEST: 'synapse-empty-test'
};

const SLEEP_PATTERNS = [
  {
    regex: /page\.waitForTimeout\s*\(\s*\d+\s*\)/g,
    lang: ['javascript', 'typescript', 'javascriptreact', 'typescriptreact'],
    replacement: "await page.waitForLoadState('networkidle');",
    desc: "Replace page.waitForTimeout with smart wait (networkidle)"
  },
  {
    regex: /(?:await\s+)?sleep\s*\(\s*\d+\s*\)/g,
    lang: ['javascript', 'typescript'],
    replacement: "await page.waitForLoadState('networkidle');",
    desc: "Replace sleep() with smart wait"
  },
  {
    regex: /time\.sleep\s*\(\s*[\d.]+\s*\)/g,
    lang: ['python'],
    replacement: "page.wait_for_load_state('networkidle')",
    desc: "Replace time.sleep() with smart wait"
  },
  {
    regex: /Thread\.sleep\s*\(\s*\d+\s*\)/g,
    lang: ['groovy', 'java'],
    replacement: "// Smart wait: element visibility / Angular isStable()",
    desc: "Replace Thread.sleep() with dynamic smart wait"
  }
];

const TAUTOLOGY_PATTERNS = [
  {
    regex: /expect\s*\(\s*true\s*\)\.to(?:Be|Equal)\s*\(\s*true\s*\)/g,
    lang: ['javascript', 'typescript'],
    replacement: "// TODO: Replace with semantic assertion: await expect(locator).toBeVisible();",
    desc: "Replace tautological assertion with semantic locator check"
  },
  {
    regex: /assert\s+True\b/g,
    lang: ['python'],
    replacement: "# TODO: Replace with semantic assert: assert actual == expected",
    desc: "Replace 'assert True' with functional check"
  },
  {
    regex: /assertTrue\s*\(\s*true\s*\)/g,
    lang: ['groovy', 'java'],
    replacement: "// TODO: Replace with semantic assertion",
    desc: "Replace assertTrue(true) with functional verification"
  }
];

const SWALLOWED_EXCEPTION_PATTERNS = [
  {
    regex: /except(?:\s+[a-zA-Z0-9_]+)?\s*:\s*\n\s+pass\b/g,
    lang: ['python'],
    replacement: "except Exception as err:\n        # Log and preserve failure traceability\n        raise",
    desc: "Replace empty pass with logged re-raise"
  },
  {
    regex: /catch\s*\([^\)]*\)\s*\{\s*\}/g,
    lang: ['javascript', 'typescript', 'groovy', 'java'],
    replacement: "catch (err) {\n    console.error('Test execution error:', err);\n    throw err;\n  }",
    desc: "Replace empty catch block with error logging and throw"
  }
];

const RAW_XPATH_PATTERNS = [
  {
    regex: /page\.locator\s*\(\s*['"](?:\/\/|\/\*|xpath=)[^'"]+['"]\s*\)/g,
    lang: ['javascript', 'typescript'],
    desc: "Extract raw XPath selector into a Page Class extending BasePage"
  },
  {
    regex: /findTestObject\s*\(\s*['"][^'"]+['"]\s*\)/g,
    lang: ['groovy'],
    desc: "Encapsulate findTestObject inside Page Class method"
  }
];

module.exports = {
  DIAGNOSTIC_CODES,
  SLEEP_PATTERNS,
  TAUTOLOGY_PATTERNS,
  SWALLOWED_EXCEPTION_PATTERNS,
  RAW_XPATH_PATTERNS
};
