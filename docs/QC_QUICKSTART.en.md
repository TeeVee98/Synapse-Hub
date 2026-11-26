# ⚡ Synapse Hub — 1-Page QC Team Quickstart

[🇻🇳 Tiếng Việt](QC_QUICKSTART.md) | [🇬🇧 English Edition](QC_QUICKSTART.en.md) • [⬅️ Back to README](../README.en.md)

> **Author:** Thế Vị ([@TeeVee98](https://github.com/TeeVee98)) | **License:** MIT  
> **Goal:** Get your QC team productive in **3 minutes** — without memorizing 57 skills or 153 CLI commands.

---

## 📦 Installation (Pick One Channel)

- **Option A — Recommended (Node.js >= 18 + Python >= 3.10):** Run directly with `npx @teevee98/synapse-hub <command>`, or install globally:
  ```bash
  npm install -g @teevee98/synapse-hub
  ```
- **Option B — Pure Python >= 3.10 (GitHub Source):**
  ```bash
  pip install git+https://github.com/TeeVee98/Synapse-Hub.git
  ```

---

## 👔 Track 1: Manual QC / Zero-Code (3 Daily Commands)

> Use the **VS Code Extension** ([QA Sentinel Toolkit](https://marketplace.visualstudio.com/items?itemName=Teevee98.synapse-hub-vscode)) for 1-click UI actions, or run these 3 commands:

| # | Daily Command | Purpose |
|---|---|---|
| **1** | `npx @teevee98/synapse-hub doctor` | Verify Python, Node.js, Git, and local QC environment health |
| **2** | `npx @teevee98/synapse-hub export-excel` | Export User Stories / Test Cases into a 12-column Enterprise Excel sheet |
| **3** | `npx @teevee98/synapse-hub scaffold-tc testcase.md --out tests/e2e/` | Transpile manual Markdown test cases into Clean POM Playwright specs |

---

## 🤖 Track 2: Automation QC (4 Daily Commands)

> Use across Playwright, Cypress, Pytest, or Katalon suites to catch fake-pass tests, fixed sleeps, and credential leaks before pushing:

| # | Daily Command | Purpose |
|---|---|---|
| **1** | `npx @teevee98/synapse-hub doctor` | Confirm runtime prerequisites before running quality checks |
| **2** | `npx @teevee98/synapse-hub init --profile standard` | Initialize Synapse Hub configuration in your automation repository |
| **3** | `npx @teevee98/synapse-hub lint` | Catch 0-assert fake passes, static sleeps, and swallowed exceptions |
| **4** | `npx @teevee98/synapse-hub verify` | Run the full 11 Definition-of-Done (DoD) Quality Gates before PR merge |

---

## 🔧 Windows / PATH Troubleshooting (Top 3 Issues)

| Symptom | Root Cause | Quick Fix |
|---|---|---|
| `python3` opens Microsoft Store or reports `not found` | Windows App Execution Alias intercepts `python3` via `WindowsApps` stub | Install Python >= 3.10 with **Add python.exe to PATH**, or disable `python3.exe` under *Manage app execution aliases* |
| `npx @teevee98/synapse-hub` reports missing Python / Node | Binary is not on the active terminal `PATH` | Reopen your terminal after installation and run `npx @teevee98/synapse-hub doctor` to inspect detected paths |
| Garbled output or Gate 1 UTF-8 BOM failure on Windows | File saved with UTF-8 BOM or legacy Windows console codepage | Save files as **UTF-8** (without BOM) and set `PYTHONIOENCODING=utf-8` in your shell |

> 📚 **Next references:** [11 DoD Quality Gates](QUALITY_GATES.en.md) • [Full CLI Reference](CLI_REFERENCE.en.md)
