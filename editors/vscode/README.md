<!--
SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
SPDX-License-Identifier: MIT
Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
-->

# Synapse Hub — Enterprise AI QA Sentinel (VS Code & Cursor Extension)

> **Official VS Code & Cursor Extension for Synapse Hub**  
> Created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

Bring the real-time auditing and self-healing power of **Synapse Hub** directly inside your editor. Detect fake-pass tests, prohibited static sleeps, and Clean POM violations while typing, and fix them in a single click (`Ctrl + .`).

---

## ⚡ Key Capabilities

### 1. Real-Time In-Editor Linter (Meta Infer-Style AST Diagnostics)
* **Static Sleep Detector:** Flags `page.waitForTimeout()`, `cy.wait()`, `time.sleep()`, and `Thread.sleep()` as flaky anti-patterns.
* **Fake-Pass & Tautology Sentinel:** Catches `expect(true).toBe(true)`, `expect(false).toBe(false)`, `expect(1).toBe(1)`, `assert True`, `assert 1 == 1`, and zero-assertion test cases.
* **Swallowed Exception Guard:** Detects empty `except: pass`, dummy suppression `_ = err`, or `catch (...) {}` blocks that mask AUT failures.
* **Clean POM Enforcer:** Flags raw XPath/CSS selectors embedded inside test script files.

### 2. 1-Click Quick Fixes (`Ctrl + .` / `Cmd + .`)
* Instantly converts static sleeps into dynamic Smart Waits:
  * TypeScript/JavaScript (Playwright): `await page.waitForLoadState('networkidle');`
  * Cypress: Dynamic `cy.intercept` alias or DOM visibility assertions.
  * Python: `page.wait_for_load_state('networkidle')`
  * Java/Groovy: Dynamic element visibility checks.
* Refactors swallowed exceptions into logged re-raises.

### 3. Sidebar Activity Bar ("QA Sentinel Toolkit")
A dedicated QA Activity Bar panel featuring 1-click execution:
* **🛡️ DoD 10 Quality Gates:** Run 10 Gates verification (`verify`), scan Meta Infer linter (`lint`), run micro-mutations (`mutate`), or trigger self-healing locators (`heal`).
* **🩺 Health & Diagnostics:** Run environment doctor (`doctor`), 5-in-1 repository health audit (`analyze`), audit Katalon/Groovy scripts (`katalon-lint`), or view the HTML project dashboard/scorecard.
* **🛠️ Authoring & Config:** Synchronize AI agent rules across Cursor/Claude/Copilot (`sync-rules`), query 120+ QA checklists (`checklist`), initialize `.synapse.json`, or export 12-column Excel test cases.

### 4. Default 1-Stroke Keybindings
* `Ctrl + Alt + F` (Mac: `Cmd + Alt + F`): **Fix All Smells in Active File** (instant smart waits & clean POM fixes)
* `Ctrl + Alt + V` (Mac: `Cmd + Alt + V`): **Run 10 Quality Gates DoD Verification**
* `Ctrl + Alt + L` (Mac: `Cmd + Alt + L`): **Run Meta Infer AST Linter on Active File**

### 5. Status Bar Guard
Displays `$(shield-check) Synapse: 100% Clean` in the status bar with 1-click access to the 10 Quality Gates runner.

---

## 📦 Installation

### From Local `.vsix` Package (Offline / Air-Gapped Ready)
1. In VS Code or Cursor, press `Ctrl + Shift + P` (or `Cmd + Shift + P` on macOS).
2. Type and select **Extensions: Install from VSIX...**.
3. Select `synapse-hub-vscode-4.7.3.vsix`.
4. Alternatively, install via terminal:
   ```bash
   code --install-extension editors/vscode/dist/synapse-hub-vscode-4.7.3.vsix
   # Or for Cursor:
   cursor --install-extension editors/vscode/dist/synapse-hub-vscode-4.7.3.vsix
   ```

---

## ⚙️ Extension Settings

* `synapse.enableRealtimeLinter`: Enable or disable background AST scanning (default: `true`).
* `synapse.strictCleanPom`: Flag raw XPath and CSS selectors inside test scripts (default: `true`).
* `synapse.cliCommand`: Base command used by terminal runners (default: `npx @teevee98/synapse-hub`).

---

## 📄 License & Attribution

Distributed under the **MIT License**. Original copyright notice and permission notices must be preserved in all copies or substantial portions of the Software:
```
Copyright (c) 2026 Thế Vị (@TeeVee98)
https://github.com/TeeVee98/Synapse-Hub
```
