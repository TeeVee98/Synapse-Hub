// SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
// SPDX-License-Identifier: MIT
// Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

/**
 * Tree item representing a command or category in the Synapse Hub QA Sentinel view.
 */
class SynapseTreeItem {
  constructor(label, collapsibleState, command, iconId, tooltip) {
    this.label = label;
    this.collapsibleState = collapsibleState;
    this.command = command;
    this.tooltip = tooltip || label;

    try {
      const vscode = require('vscode');
      if (iconId) {
        this.iconPath = new vscode.ThemeIcon(iconId);
      }
    } catch {
      // Fallback in headless / unit-test mode
      this.iconPath = iconId;
    }
  }
}

/**
 * TreeDataProvider for the Synapse Hub Activity Bar view.
 */
class SynapseTreeDataProvider {
  constructor(vscodeModule) {
    this.vscode = vscodeModule || (function() {
      try {
        return require('vscode');
      } catch {
        return null;
      }
    })();
  }

  getTreeItem(element) {
    return element;
  }

  getChildren(element) {
    const CollapsibleState = this.vscode ? this.vscode.TreeItemCollapsibleState : { None: 0, Expanded: 2 };

    if (!element) {
      return [
        new SynapseTreeItem('🛡️ DoD 10 Quality Gates', CollapsibleState.Expanded, null, 'shield', 'Definition-of-Done verification gates'),
        new SynapseTreeItem('🩺 Health & Diagnostics', CollapsibleState.Expanded, null, 'pulse', 'System and repository health audits'),
        new SynapseTreeItem('🛠️ Authoring & Config', CollapsibleState.Expanded, null, 'tools', 'Configuration and test case authoring utilities')
      ];
    }

    if (element.label.includes('10 Quality Gates')) {
      return [
        new SynapseTreeItem('⚡ Run 10 Gates Verification', CollapsibleState.None, { command: 'synapse.runVerify', title: 'Verify 10 Gates' }, 'check-all', 'Run verify_all.py (10 Quality Gates DoD)'),
        new SynapseTreeItem('🔍 Run Meta Infer AST Linter', CollapsibleState.None, { command: 'synapse.runLint', title: 'Infer Linter' }, 'search', 'Scan for fake passes and swallowed exceptions'),
        new SynapseTreeItem('🧬 Run Micro-Mutation Sentinel', CollapsibleState.None, { command: 'synapse.runMutate', title: 'Mutate' }, 'flame', 'Test assertion sensitivity (Threshold >= 80%)')
      ];
    }

    if (element.label.includes('Health & Diagnostics')) {
      return [
        new SynapseTreeItem('🩺 Run Environment Doctor', CollapsibleState.None, { command: 'synapse.runDoctor', title: 'Doctor' }, 'heart', 'Diagnose environment prerequisites'),
        new SynapseTreeItem('📈 5-in-1 Repository Health Audit', CollapsibleState.None, { command: 'synapse.runAnalyze', title: 'Analyze' }, 'graph', 'Analyze repository health, risks, and architecture'),
        new SynapseTreeItem('📊 Open Executive HTML Dashboard', CollapsibleState.None, { command: 'synapse.openDashboard', title: 'Dashboard' }, 'dashboard', 'Open reports/PROJECT_DASHBOARD.html'),
        new SynapseTreeItem('📖 Open Interactive Welcome Guide', CollapsibleState.None, { command: 'synapse.openWelcome', title: 'Welcome' }, 'book', 'Open reports/WELCOME.html')
      ];
    }

    if (element.label.includes('Authoring & Config')) {
      return [
        new SynapseTreeItem('⚙️ Initialize .synapse.json Config', CollapsibleState.None, { command: 'synapse.initConfig', title: 'Init Config' }, 'gear', 'Generate .synapse.json configuration file'),
        new SynapseTreeItem('📑 Export Excel Test Cases Template', CollapsibleState.None, { command: 'synapse.exportExcel', title: 'Export Excel' }, 'file-spreadsheet', 'Export 12-column Excel test case template'),
        new SynapseTreeItem('🪄 Fix Smells in Active File', CollapsibleState.None, { command: 'synapse.fixCurrentFile', title: 'Fix Smells' }, 'wand', 'Auto-replace static sleeps with smart waits')
      ];
    }

    return [];
  }
}

module.exports = {
  SynapseTreeItem,
  SynapseTreeDataProvider
};
