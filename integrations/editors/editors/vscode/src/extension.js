// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

const vscode = require('vscode');
const { lintDocumentText } = require('./linter');
const { SynapseQuickFixProvider } = require('./quickFix');
const { SynapseTreeDataProvider } = require('./treeView');
const { registerCommands } = require('./commands');

let diagnosticCollection = null;
let lintTimeout = null;

function updateDiagnostics(document) {
  if (!diagnosticCollection || !document) return;

  const supportedLanguages = [
    'javascript',
    'typescript',
    'javascriptreact',
    'typescriptreact',
    'python',
    'groovy',
    'java'
  ];

  if (!supportedLanguages.includes(document.languageId)) {
    return;
  }

  const config = vscode.workspace.getConfiguration('synapse');
  const enabled = config.get('enableRealtimeLinter', true);
  if (!enabled) {
    diagnosticCollection.delete(document.uri);
    return;
  }

  const text = document.getText();
  const diagnostics = lintDocumentText(text, document.languageId, document.fileName, vscode);
  diagnosticCollection.set(document.uri, diagnostics);
}

function triggerDebouncedLint(document) {
  if (lintTimeout) {
    clearTimeout(lintTimeout);
  }
  lintTimeout = setTimeout(() => {
    updateDiagnostics(document);
  }, 250);
}

function activate(context) {
  const outputChannel = vscode.window.createOutputChannel('Synapse Hub QA');
  outputChannel.appendLine('[Synapse Hub] Enterprise AI QA Sentinel extension activated.');

  // 1. Diagnostic Collection
  diagnosticCollection = vscode.languages.createDiagnosticCollection('synapse-hub');
  context.subscriptions.push(diagnosticCollection);

  // 2. Document Event Listeners
  if (vscode.window.activeTextEditor) {
    updateDiagnostics(vscode.window.activeTextEditor.document);
  }

  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor(editor => {
      if (editor) updateDiagnostics(editor.document);
    }),
    vscode.workspace.onDidChangeTextDocument(event => {
      triggerDebouncedLint(event.document);
    }),
    vscode.workspace.onDidSaveTextDocument(document => {
      updateDiagnostics(document);
    }),
    vscode.workspace.onDidCloseTextDocument(document => {
      if (diagnosticCollection) {
        diagnosticCollection.delete(document.uri);
      }
    })
  );

  // 3. Quick Fix Code Action Provider
  const supportedSelector = [
    { language: 'javascript' },
    { language: 'typescript' },
    { language: 'python' },
    { language: 'groovy' },
    { language: 'java' }
  ];

  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider(
      supportedSelector,
      new SynapseQuickFixProvider(vscode),
      {
        providedCodeActionKinds: [vscode.CodeActionKind.QuickFix]
      }
    )
  );

  // 4. Sidebar Activity Bar TreeView
  const treeDataProvider = new SynapseTreeDataProvider(vscode);
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider('synapse-qa-commands', treeDataProvider)
  );

  // 5. Status Bar Item
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.text = '$(shield) Synapse: Clean POM';
  statusBarItem.tooltip = 'Synapse Hub: Click to Run 10 Quality Gates DoD';
  statusBarItem.command = 'synapse.runVerify';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // 6. Register Commands
  registerCommands(context, vscode);
}

function deactivate() {
  if (diagnosticCollection) {
    diagnosticCollection.clear();
    diagnosticCollection.dispose();
  }
  if (lintTimeout) {
    clearTimeout(lintTimeout);
  }
}

module.exports = {
  activate,
  deactivate,
  updateDiagnostics
};
