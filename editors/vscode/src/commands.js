// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

const path = require('path');
const fs = require('fs');
const { SLEEP_PATTERNS } = require('./constants');

let activeTerminal = null;

function getTerminal(vscode) {
  if (activeTerminal && !activeTerminal.exitStatus) {
    return activeTerminal;
  }
  activeTerminal = vscode.window.createTerminal({
    name: 'Synapse Hub QA',
    iconPath: new vscode.ThemeIcon('shield')
  });
  return activeTerminal;
}

function runCliSubcommand(vscode, subcommand) {
  const config = vscode.workspace.getConfiguration('synapse');
  const baseCmd = config.get('cliCommand') || 'npx synapse-hub';
  const terminal = getTerminal(vscode);
  terminal.show();
  terminal.sendText(`${baseCmd} ${subcommand}`);
}

function openHtmlReport(vscode, relativePath) {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    vscode.window.showWarningMessage('[Synapse Hub] No active workspace found to locate reports.');
    return;
  }
  const root = folders[0].uri.fsPath;
  const filePath = path.join(root, relativePath);

  if (fs.existsSync(filePath)) {
    vscode.env.openExternal(vscode.Uri.file(filePath));
  } else {
    vscode.window.showInformationMessage(`[Synapse Hub] Report '${relativePath}' not yet generated. Run verification or analysis first.`);
  }
}

async function fixActiveFile(vscode) {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showInformationMessage('[Synapse Hub] No active editor open to fix.');
    return;
  }

  const document = editor.document;
  const text = document.getText();
  const lang = document.languageId;
  let newText = text;
  let count = 0;

  for (const pattern of SLEEP_PATTERNS) {
    if (!pattern.lang.includes(lang)) continue;
    const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
    newText = newText.replace(regex, () => {
      count++;
      return pattern.replacement;
    });
  }

  if (count > 0) {
    const fullRange = new vscode.Range(
      document.positionAt(0),
      document.positionAt(text.length)
    );
    await editor.edit(editBuilder => {
      editBuilder.replace(fullRange, newText);
    });
    vscode.window.showInformationMessage(`[Synapse Hub] Fixed ${count} prohibited static sleep(s) with Smart Waits.`);
  } else {
    vscode.window.showInformationMessage('[Synapse Hub] No fixable static sleeps found in current file.');
  }
}

function registerCommands(context, vscode) {
  context.subscriptions.push(
    vscode.commands.registerCommand('synapse.runVerify', () => runCliSubcommand(vscode, 'verify')),
    vscode.commands.registerCommand('synapse.runLint', () => runCliSubcommand(vscode, 'lint')),
    vscode.commands.registerCommand('synapse.runAnalyze', () => runCliSubcommand(vscode, 'analyze')),
    vscode.commands.registerCommand('synapse.runMutate', () => runCliSubcommand(vscode, 'mutate --min-score 80')),
    vscode.commands.registerCommand('synapse.runDoctor', () => runCliSubcommand(vscode, 'doctor')),
    vscode.commands.registerCommand('synapse.openDashboard', () => openHtmlReport(vscode, 'reports/PROJECT_DASHBOARD.html')),
    vscode.commands.registerCommand('synapse.openWelcome', () => openHtmlReport(vscode, 'reports/WELCOME.html')),
    vscode.commands.registerCommand('synapse.initConfig', () => runCliSubcommand(vscode, 'init-config')),
    vscode.commands.registerCommand('synapse.exportExcel', () => runCliSubcommand(vscode, 'export-excel')),
    vscode.commands.registerCommand('synapse.fixCurrentFile', () => fixActiveFile(vscode))
  );
}

module.exports = {
  registerCommands,
  runCliSubcommand,
  openHtmlReport,
  fixActiveFile
};
