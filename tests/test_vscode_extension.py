#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_vscode_extension.py
--------------------------------
Comprehensive unit tests verifying the Synapse Hub VS Code / Cursor extension:
1. Package manifest integrity & version sync.
2. In-editor linter detection for static sleeps, tautology, swallowed exceptions, and Clean POM violations.
3. Sidebar TreeDataProvider structure.
4. QuickFix code action synthesis.
"""

import os
import json
import subprocess
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXT_DIR = os.path.join(REPO_ROOT, "editors", "vscode")


class TestVSCodeExtension(unittest.TestCase):

    def setUp(self):
        self.package_json_path = os.path.join(EXT_DIR, "package.json")
        self.readme_path = os.path.join(EXT_DIR, "README.md")
        self.root_pkg_path = os.path.join(REPO_ROOT, "package.json")

    def test_extension_package_manifest_integrity(self):
        """Verifies package.json contains all required metadata, version sync, and author attribution."""
        self.assertTrue(os.path.isfile(self.package_json_path), "Missing editors/vscode/package.json")

        with open(self.package_json_path, "r", encoding="utf-8") as f:
            pkg = json.load(f)

        with open(self.root_pkg_path, "r", encoding="utf-8") as f:
            root_pkg = json.load(f)

        self.assertEqual(pkg.get("name"), "synapse-hub-vscode")
        self.assertEqual(pkg.get("version"), root_pkg.get("version"), "Extension version not synced with Hub version")
        self.assertIn("TeeVee98", str(pkg.get("author")))
        self.assertIn("Thế Vị", str(pkg.get("author")))
        self.assertEqual(pkg.get("license"), "MIT")

        # Verify contributed commands
        commands = [c.get("command") for c in pkg.get("contributes", {}).get("commands", [])]
        expected_commands = [
            "synapse.runVerify",
            "synapse.runLint",
            "synapse.runFix",
            "synapse.runAnalyze",
            "synapse.runMutate",
            "synapse.runDoctor",
            "synapse.openDashboard",
            "synapse.openScorecard",
            "synapse.openWelcome",
            "synapse.initConfig",
            "synapse.exportExcel",
            "synapse.fixCurrentFile",
        ]
        for cmd in expected_commands:
            self.assertIn(cmd, commands, f"Command '{cmd}' not contributed in package.json")

        # Verify activity bar views container
        containers = pkg.get("contributes", {}).get("viewsContainers", {}).get("activitybar", [])
        self.assertTrue(any(c.get("id") == "synapse-qa" for c in containers), "Missing synapse-qa viewsContainer")

    def test_linter_detects_anti_patterns_via_node(self):
        """Executes src/linter.js in Node.js to verify diagnostics detection."""
        test_script = """
        const { lintDocumentText } = require('./editors/vscode/src/linter');
        const jsCode = "test('flaky', async () => { await sleep(5000); expect(true).toBe(true); page.locator('//button'); expect(page.locator('#id')).toBeVisible(); expect(page.locator('#dangling')); });";
        const jsDiags = lintDocumentText(jsCode, 'javascript', 'tests/flaky.spec.js');
        const pyCode = "def test_foo():\\n    time.sleep(2)\\n    assert True\\n    try:\\n        pass\\n    except:\\n        pass\\n";
        const pyDiags = lintDocumentText(pyCode, 'python', 'tests/test_foo.py');
        console.log(JSON.stringify({ jsDiags, pyDiags }));
        """

        result = subprocess.run(
            ["node", "-e", test_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0, f"Node execution failed: {result.stderr}")

        output = json.loads(result.stdout.strip())
        js_codes = [d.get("code") for d in output.get("jsDiags", [])]
        py_codes = [d.get("code") for d in output.get("pyDiags", [])]

        # Verify JS Diagnostics
        self.assertIn("synapse-static-sleep", js_codes)
        self.assertIn("synapse-tautology", js_codes)
        self.assertIn("synapse-clean-pom-violation", js_codes)
        self.assertIn("synapse-unawaited-expect", js_codes)
        self.assertIn("synapse-dangling-expect", js_codes)

        # Verify Python Diagnostics
        self.assertIn("synapse-static-sleep", py_codes)
        self.assertIn("synapse-tautology", py_codes)
        self.assertIn("synapse-swallowed-exception", py_codes)

    def test_tree_view_structure_via_node(self):
        """Executes src/treeView.js in Node.js to verify TreeDataProvider returns expected hierarchy."""
        test_script = """
        const { SynapseTreeDataProvider } = require('./editors/vscode/src/treeView');
        const provider = new SynapseTreeDataProvider(null);
        const roots = provider.getChildren();
        const rootLabels = roots.map(r => r.label);
        const gateChildren = provider.getChildren(roots[0]);
        const gateLabels = gateChildren.map(c => c.label);
        console.log(JSON.stringify({ rootLabels, gateLabels }));
        """

        result = subprocess.run(
            ["node", "-e", test_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0, f"Node treeView failed: {result.stderr}")

        data = json.loads(result.stdout.strip())
        root_labels = " ".join(data.get("rootLabels", []))
        self.assertIn("Quality Gates", root_labels)
        self.assertIn("Health", root_labels)
        self.assertIn("Authoring", root_labels)

        gate_labels = " ".join(data.get("gateLabels", []))
        self.assertIn("10 Gates", gate_labels)
        self.assertIn("Linter", gate_labels)
        self.assertIn("Auto-Fix", gate_labels)
        self.assertIn("Mutation", gate_labels)

    def test_quick_fix_provider_actions_via_node(self):
        """Verifies SynapseQuickFixProvider provides code actions for unawaited expect and sleep."""
        test_script = """
        const { SynapseQuickFixProvider } = require('./editors/vscode/src/quickFix');
        const { DIAGNOSTIC_CODES } = require('./editors/vscode/src/constants');

        // Mock vscode module for CodeAction synthesis
        const mockVscode = {
          CodeActionKind: { QuickFix: 'QuickFix' },
          CodeAction: function(title, kind) {
            this.title = title;
            this.kind = kind;
          },
          WorkspaceEdit: function() {
            this.replacements = [];
            this.replace = (uri, range, text) => {
              this.replacements.push({ uri, range, text });
            };
          }
        };

        const provider = new SynapseQuickFixProvider(mockVscode);
        const doc = {
          uri: 'file:///tests/login.spec.ts',
          languageId: 'typescript',
          getText: (range) => (range && range.start.line === 1 ? 'await page.waitForTimeout(5000)' : 'expect(page.locator("#btn")).toBeVisible()')
        };
        const context = {
          diagnostics: [
            {
              source: 'Synapse Hub',
              code: DIAGNOSTIC_CODES.UNAWAITED_EXPECT,
              range: { start: { line: 0, character: 0 }, end: { line: 0, character: 40 } }
            },
            {
              source: 'Synapse Hub',
              code: DIAGNOSTIC_CODES.STATIC_SLEEP,
              range: { start: { line: 1, character: 0 }, end: { line: 1, character: 25 } }
            }
          ]
        };

        const actions = provider.provideCodeActions(doc, null, context);
        const titles = actions.map(a => a.title);
        console.log(JSON.stringify(titles));
        """

        result = subprocess.run(
            ["node", "-e", test_script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0, f"Node quickFix failed: {result.stderr}")
        titles = json.loads(result.stdout.strip())
        titles_str = " ".join(titles)
        self.assertIn("Prepend missing 'await'", titles_str)
        self.assertIn("Replace", titles_str)

    def test_readme_and_media_exist(self):
        """Verifies README and media assets exist."""
        self.assertTrue(os.path.isfile(self.readme_path), "Missing README.md in extension")
        with open(self.readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Thế Vị", content)
        self.assertIn("TeeVee98/Synapse-Hub", content)

        icon_path = os.path.join(EXT_DIR, "media", "shield.svg")
        self.assertTrue(os.path.isfile(icon_path), "Missing media/shield.svg icon")


if __name__ == "__main__":
    unittest.main()
