// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

const {
  DIAGNOSTIC_CODES,
  SLEEP_PATTERNS,
  SWALLOWED_EXCEPTION_PATTERNS
} = require('./constants');

/**
 * Creates Quick Fix CodeAction objects for Synapse Hub diagnostics.
 */
class SynapseQuickFixProvider {
  constructor(vscodeModule) {
    this.vscode = vscodeModule || (function() {
      try {
        return require('vscode');
      } catch {
        return null;
      }
    })();
  }

  provideCodeActions(document, range, context) {
    if (!this.vscode) return [];
    const actions = [];

    for (const diagnostic of context.diagnostics) {
      if (!diagnostic.source || !diagnostic.source.includes('Synapse Hub')) continue;

      if (diagnostic.code === DIAGNOSTIC_CODES.STATIC_SLEEP) {
        const text = document.getText(diagnostic.range);
        const lang = document.languageId;
        const matched = SLEEP_PATTERNS.find(p => p.lang.includes(lang) && new RegExp(p.regex.source).test(text));

        if (matched) {
          const fix = new this.vscode.CodeAction(
            `⚡ [Synapse Hub] ${matched.desc}`,
            this.vscode.CodeActionKind.QuickFix
          );
          fix.edit = new this.vscode.WorkspaceEdit();
          fix.edit.replace(document.uri, diagnostic.range, matched.replacement);
          fix.diagnostics = [diagnostic];
          fix.isPreferred = true;
          actions.push(fix);
        }
      }

      if (diagnostic.code === DIAGNOSTIC_CODES.SWALLOWED_EXCEPTION) {
        const lang = document.languageId;
        const matched = SWALLOWED_EXCEPTION_PATTERNS.find(p => p.lang.includes(lang));
        if (matched) {
          const fix = new this.vscode.CodeAction(
            `⚡ [Synapse Hub] ${matched.desc}`,
            this.vscode.CodeActionKind.QuickFix
          );
          fix.edit = new this.vscode.WorkspaceEdit();
          fix.edit.replace(document.uri, diagnostic.range, matched.replacement);
          fix.diagnostics = [diagnostic];
          actions.push(fix);
        }
      }
    }

    return actions;
  }
}

module.exports = {
  SynapseQuickFixProvider
};
