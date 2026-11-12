// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

const {
  DIAGNOSTIC_CODES,
  SLEEP_PATTERNS,
  TAUTOLOGY_PATTERNS,
  SWALLOWED_EXCEPTION_PATTERNS,
  RAW_XPATH_PATTERNS
} = require('./constants');

/**
 * Scans document text for anti-patterns and returns diagnostic descriptor objects.
 * Designed to run seamlessly both inside VS Code runtime and in isolated unit tests.
 *
 * @param {string} text - Full text of the source document
 * @param {string} languageId - Document language ('javascript', 'typescript', 'python', 'groovy')
 * @param {string} fileName - Document filename/path to check script context
 * @param {object} [vscodeModule] - Optional injected vscode instance
 * @returns {Array} Array of diagnostic objects
 */
function lintDocumentText(text, languageId, fileName, vscodeModule) {
  const diagnostics = [];
  const vscode = vscodeModule || (function() {
    try {
      return require('vscode');
    } catch {
      return null;
    }
  })();

  const isTestScript = /[\/\\](?:tests|Scripts|specs|__tests__)[\/\\]/i.test(fileName) ||
                       /\.(?:spec|test)\.[a-zA-Z]+$/i.test(fileName);

  // Helper to compute line and character offset
  function indexToPosition(str, index) {
    const lines = str.substring(0, index).split('\n');
    const line = lines.length - 1;
    const character = lines[lines.length - 1].length;
    return { line, character };
  }

  function createDiagnostic(startIdx, endIdx, message, severityLevel, code) {
    const start = indexToPosition(text, startIdx);
    const end = indexToPosition(text, endIdx);

    if (vscode) {
      const range = new vscode.Range(
        new vscode.Position(start.line, start.character),
        new vscode.Position(end.line, end.character)
      );
      const severity = severityLevel === 'Error'
        ? vscode.DiagnosticSeverity.Error
        : vscode.DiagnosticSeverity.Warning;
      const diag = new vscode.Diagnostic(range, message, severity);
      diag.code = code;
      diag.source = 'Synapse Hub';
      return diag;
    }

    return {
      range: {
        start: { line: start.line, character: start.character },
        end: { line: end.line, character: end.character }
      },
      message,
      severity: severityLevel,
      code,
      source: 'Synapse Hub'
    };
  }

  // 1. Scan Prohibited Static Sleeps
  for (const pattern of SLEEP_PATTERNS) {
    if (!pattern.lang.includes(languageId)) continue;
    let match;
    const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
    while ((match = regex.exec(text)) !== null) {
      diagnostics.push(createDiagnostic(
        match.index,
        match.index + match[0].length,
        `[Synapse Hub] Prohibited static sleep: '${match[0]}'. Use dynamic smart waits (e.g. 'page.waitForLoadState("networkidle")' or element visibility) to prevent CI flakiness.`,
        'Warning',
        DIAGNOSTIC_CODES.STATIC_SLEEP
      ));
    }
  }

  // 2. Scan Tautological Assertions
  for (const pattern of TAUTOLOGY_PATTERNS) {
    if (!pattern.lang.includes(languageId)) continue;
    let match;
    const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
    while ((match = regex.exec(text)) !== null) {
      diagnostics.push(createDiagnostic(
        match.index,
        match.index + match[0].length,
        `[Synapse Hub] Fake-Pass tautology: '${match[0]}'. This assertion always passes without verifying application behavior.`,
        'Error',
        DIAGNOSTIC_CODES.TAUTOLOGY
      ));
    }
  }

  // 3. Scan Swallowed Exceptions
  for (const pattern of SWALLOWED_EXCEPTION_PATTERNS) {
    if (!pattern.lang.includes(languageId)) continue;
    let match;
    const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
    while ((match = regex.exec(text)) !== null) {
      diagnostics.push(createDiagnostic(
        match.index,
        match.index + match[0].length,
        `[Synapse Hub] Swallowed exception detected. Catching exceptions without logging or rethrowing conceals system defects.`,
        'Error',
        DIAGNOSTIC_CODES.SWALLOWED_EXCEPTION
      ));
    }
  }

  // 4. Scan Raw XPath & DOM Selectors in Test Scripts (Clean POM Violation)
  if (isTestScript) {
    for (const pattern of RAW_XPATH_PATTERNS) {
      if (!pattern.lang.includes(languageId)) continue;
      let match;
      const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
      while ((match = regex.exec(text)) !== null) {
        diagnostics.push(createDiagnostic(
          match.index,
          match.index + match[0].length,
          `[Synapse Hub] Clean POM Violation: Raw locator in test script '${match[0]}'. Encapsulate all locators inside Page Classes.`,
          'Warning',
          DIAGNOSTIC_CODES.CLEAN_POM_VIOLATION
        ));
      }
    }
  }

  return diagnostics;
}

module.exports = {
  lintDocumentText
};
