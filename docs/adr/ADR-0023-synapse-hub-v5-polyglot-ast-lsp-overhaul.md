<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0023: Synapse Hub v5.0 Comprehensive Overhaul — Hybrid Polyglot AST, Universal QA LSP, CLI Stratification, Enterprise TMS/Cloud Grid & Real-World Benchmark Certification

- **Status:** Accepted & Certified
- **Date:** 2026-11-26
- **Deciders:** Synapse Hub Core Architecture (`/solo` Tier-2 Deep Super-Plan Execution)
- **Author Attribution:** Thế Vị (@TeeVee98) under MIT License (`tools/core/author_integrity.py` untouched)

---

## 1. Context & Problem Statement

Synapse Hub v4.9.0 achieved strong single-file static defect detection and 11-gate verification, but enterprise adoption across polyglot QA teams exposed five structural friction points:

1. **Cross-File POM Assertion Blindness & Stale Optional Grammar Pin:** Page Object methods encapsulating assertions (`checkoutPage.confirmOrderComplete()`, `dashboardPage.ensureHeaderReady()`) could trigger false-positive `FAKE_PASS_NO_ASSERTION` warnings unless named `verify*`/`assert*`, while optional `[treesitter]` depended on unmaintained `tree-sitter-languages` incompatible with Python 3.12–3.13.
2. **Flat 150+ CLI Command Surface:** Daily workflows competed for visibility with ~143 specialized contrib/research commands in `--help`.
3. **IDE Ecosystem Silo:** Real-time diagnostics existed only in the VS Code JS extension wrapper, leaving JetBrains IDEs (IntelliJ, PyCharm, WebStorm, Aqua) and Neovim without native live linting or Quick-Fix edits.
4. **Enterprise TMS & Cloud Grid Coverage Gaps:** `ALMBridge` supported Jira/Xray/TestRail but lacked Zephyr Scale, Qase.io, and ReportPortal sync adapters; `SynapseGrid` lacked standardized BrowserStack, Sauce Labs, and LambdaTest W3C/Playwright capability generators with credential redaction.
5. **Version & Hygiene Drift:** Stale `10 Quality Gates` strings persisted in CLI/VS Code/MCP manifests, three completed v4 root implementation plans and a stale `v4.6.5` `.vsix` binary remained in the repository, and `docs/ARCHITECTURE*.md` referenced `agent-qa` instead of `synapse-hub` as the PyPI package name.

---

## 2. Governing Architectural Rulings

- **Ruling 1 (Hybrid Zero-Dep Core + Optional `tree-sitter-language-pack` + Cross-File POM Assertion Indexer):** Preserve zero mandatory dependencies via `tools/context/pom_assertion_indexer.py` (cycle-safe reverse BFS resolving transitive Page Object assertions up to `max_depth=3`), upgrade optional `[treesitter]` to `tree-sitter>=0.23.0` + `tree-sitter-language-pack>=0.6.0`, and wire live parsing into `infer_linter.py`, `micro_mutator.py`, and brace-scoped `omni_parser.py`.
- **Ruling 2 (Two-Tier Backward-Compatible CLI Stratification + Quality Ratchet):** Elevate 12 Canonical Core Commands (`lint`, `fix`, `verify`, `mutate`, `distill`, `analyze`, `export-excel`, `scaffold-tc`, `mcp-serve`, `lsp`, `doctor`, `new`), group specialized tools under `synapse lab <subcommand>` / `--list`, keep 100% legacy top-level aliases active in `cli_specs.json` and `bin/agent-qa.js`, expand strict `mypy` overrides, and advance the coverage ratchet floor (`60` -> `65`).
- **Ruling 3 (Universal Stdio LSP 3.17 + Enterprise TMS/Cloud Grid + Empirical FPR Gate):** Ship zero-dependency `tools/mcp/qa_lsp_server.py` (`synapse lsp`), sync VS Code/MCP manifests to 11 Quality Gates + `synapse_lsp_health`, extend `alm_bridge.py` (`zephyr`, `qase`, `reportportal`) and `synapse_grid.py` (`browserstack`, `saucelabs`, `lambdatest` with `***REDACTED***` scrubbing), and enforce empirical `FPR <= 5.0%` / `Recall >= 95.0%` / `P95 <= 50.0ms` via `benchmarks/real_world_fpr_runner.py`.

---

## 3. Verification & Empirical Certification Receipts

| Verification Gate | Target / Command | Measured Empirical Result |
| :--- | :--- | :--- |
| **Dynamic Mutation Sentinel (M1)** | `tools/context/pom_assertion_indexer.py` | **PASSED** — `84.21%` kill score (`16/19` killed, threshold `>= 80.0%`) |
| **Dynamic Mutation Sentinel (M5)** | `tools/mcp/qa_lsp_server.py` | **PASSED** — `80.0%` kill score (`16/20` killed, threshold `>= 80.0%`) |
| **Strict Static Typing (`mypy`)** | `pom_assertion_indexer`, `qa_lsp_server`, `plan_schema_sentinel`, `cli_schema_sentinel` | **PASSED** — `0` errors across all strict override modules |
| **Real-World FPR Benchmark (M8)** | `python benchmarks/real_world_fpr_runner.py --json` | **PASSED** — `51` cases, `0` FP (`FPR = 0.0% <= 5.0%`), `100.0%` recall (`>= 95.0%`), `P95 = 6.953 ms` (`<= 50.0 ms`) |
| **CLI Schema & NPM Allowlist Parity** | `cli_schema_sentinel.py --check --json` & `test_cli_contracts.py` | **PASSED** — `79` tools checked, `drift_count == 0`; `12` core / `143` lab commands; `1:1` allowlist parity |
| **LSP & IDE / MCP 11-Gate Parity** | `synapse lsp --check-health --json`, `editors/vscode/tests/linter.test.js`, `test_mcp_unified_server.py` | **PASSED** — LSP 3.17 `HEALTHY` (`0.012 ms`); VS Code `11/11` passed; MCP `5/5` passed |
| **Adversarial Self-Audit (`--purple`)** | `solo_runner.py --purple` & `--neuro-symbolic` | **CERTIFIED_PURPLE** (`0` must-fix findings across 22 changed files, `fan_in=7`, `has_cycle=false`) |
| **Bilingual Discipline & Docs Lint** | `invariant_checker.py --rule 16 --json` & `lint_ai_docs.py` | **PASSED** — `0` violations; all documented tools/suites verified on disk |
| **Packaging (`setuptools` build)** | `setuptools.build_meta.build_wheel` & `build_sdist` | **VERIFIED** — PEP 621 `synapse-hub` wheel & sdist build cleanly |
| **Workspace Hygiene (M9–M10)** | `docs/plans/HISTORICAL_V4_PLANS_ARCHIVE.md` & `test_super_plan_and_harvester.py` | **PASSED** — 3 legacy drafts archived, stale `v4.6.5` VSIX removed, `implementation_plan_phase2_wiring.md` preserved (`37/37` passed) |
| **Phase-2 Deep AST, Qualified POM & RAM LSP (`test_v5_ten_of_ten_hardening.py`)** | `extract_tree_sitter_method_nodes`, `extract_tree_sitter_test_spans`, receiver-qualified POM bindings, zero-disk-I/O `source_content` RAM LSP, `--external-repo` FPR & `publish_pypi.yml` OIDC | **CERTIFIED (`RED -> GREEN -> MUTATION -> PURPLE`)** — Zero disk tempfiles in LSP, receiver collision blocked (`StringUtil.validate` != `CheckoutPage.validate`), PEP 740 PyPI OIDC workflow added |

---

## 4. Consequences & Rollback Boundaries

- **Positive:** Teams using Playwright TS/Python, Cypress, Katalon Groovy, Java Selenium, JetBrains IDEs, Neovim, VS Code, Zephyr Scale, Qase.io, ReportPortal, BrowserStack, Sauce Labs, and LambdaTest gain first-class polyglot support with zero mandatory external dependencies.
- **Trade-Offs:** Behavioral parity between stdlib state-machine parsing and optional `tree-sitter-language-pack` parsing must remain covered by regression tests, and legacy top-level CLI aliases remain supported alongside `synapse lab <cmd>`.
- **Rollback:** All 11 milestones carry deterministic path-scoped rollback hooks via `tools/lint/plan_schema_sentinel.py::rollback_path_scoped_detailed`.
