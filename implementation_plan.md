<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Implementation Plan: Agensi.io 6-Pack Standalone Skill & Tool Packager

> **Changelog (v1 -> v2 — Post-Audit Hardening):**
> - Placed packager at `scripts/package_agensi_skills.py` (outside `tools/contrib/`) to match repo packaging conventions (`scripts/package_dist.py`) and avoid `cli_schema_sentinel.py` unregistered-public-tool drift.
> - Replaced nonexistent `plan_schema_sentinel.py --rollback` CLI flag with executable `rollback_path_scoped_detailed(...)` Python rollback hooks across all 6 milestones.
> - Added missing core scripts & reference docs referenced by source `SKILL.md` files: `tools/api/generate_api_matrix.py` (for `api-contract-and-fuzzer`), `tools/manual/checklist_query.py` + `tools/lint/manual_tc_linter.py` + `testing/manual/manual_testing_rules.md` (for `rbt-manual-testing-excel`), and `resources/implementation-playbook.md` normalization (for `wcag-a11y-audit`).
> - Added explicit standalone runtime-root rewrites (`HUB_ROOT`/`REPO_ROOT` -> `os.getcwd()` for reports/audit logs/test cwd; `DEFAULT_CHECKLIST_PATH` -> `../references/field_validation_checklist.md`), English CLI help localization for exported `template_excel_exporter.py`/`md_to_xlsx.py`, dead CLI command rewriting (`agent-qa`, `synapse`, `tools/...` -> `scripts/...`), and `skillspector.py` self-scan reviewer note.

> **Super-Plan Metadata:** `Tier 1 (STANDARD_PLUS_SUPER)` | `RiskScore = 0.65` (`BlastRadius = 15`, `CrossBoundary = True`, `StateMutation = False` on `tools/` & `skills/`)
> **Execution Mode:** Sequential Single-Agent `/solo` (`M1 -> M2 -> M3 -> M4 -> M5 -> M6`, strictly zero `swarm` workers)
> **Governing Rulings (Locked at Stage 2 Ambiguity Gate):**
> - `Ruling 1 (AST-Rewritten Standalone Vendor Bundle):` Copy required sibling Python modules into each package's `scripts/` folder inside `dist/agensi/<slug>/`; strip repo `import tools` bootstraps, anchor standalone runtime roots (`HUB_ROOT`/`REPO_ROOT`) to `os.getcwd()` (and `checklist_query.py` checklist path to `../references/`), and rewrite markdown CLI commands to `scripts/` only inside exported copies; upstream `tools/` and `skills/` remain unmodified.
> - `Ruling 2 (Tiered 6-Pack Launch):` Build 6 standalone packages (`review-spec` Free, `skillspector-security-guard` $7-$9.99, `rbt-manual-testing-excel` $7-$9.99, `wcag-a11y-audit` $5-$7, `api-contract-and-fuzzer` $9.99-$15, `anti-fake-pass-mutation` $9.99-$14.99), deferring `self-healing-clean-pom` and `security-dast-sentinel` to Phase 2.
> - `Ruling 3 (Graceful Dependency Guard, English CLI Polish & Out-of-Repo Smoke Tests):` Include `requirements.txt` for non-stdlib deps (`openpyxl`, optional `pathspec`), wrap optional/third-party imports with friendly English install/fallback guards (zero raw tracebacks or Vietnamese CLI strings), bundle `README.md` + `LICENSE` (MIT attribution to Thế Vị (@TeeVee98)), and verify every `.zip` from an isolated temporary directory outside the repository.

### Stage 2 Orthogonal Architectural Tournament (Trade-Off Matrix)

| Dimension | Branch A: Wrapper CLI (`npx` / `pip`) | Branch B (Selected): AST-Rewritten Standalone Bundles | Branch C: Copy Full `tools/` Tree |
| :--- | :--- | :--- | :--- |
| **Buyer Experience** | Forces full Synapse Hub install | **Zero-setup unzip & run immediately from any user project** | Bloated 166-script zip; confusing layout |
| **Import & Path Reliability** | Requires repo/global install | **All sibling modules vendored + `cwd`-anchored runtime roots** | Works but pollutes `.claude/skills/` with `HUB_ROOT` writes |
| **Security Scan Hygiene** | Minimal files | **Targeted files; `SkillSpector` score = 0/100 + reviewer note** | High false-positive surface on Agensi |

---

## 1. Affected Files & Blast Radius

### New Files to Create (Packager, Tests & Release Playbook)

| Action | Target File & Symbol Anchor | Line Range | Change Purpose & Blast Radius |
| :---: | :--- | :---: | :--- |
| `[CREATE]` | `scripts/package_agensi_skills.py::AgensiPackager` | `(New)` | Deterministic AST-aware standalone packager, vendor resolver, runtime-root rewriter, markdown/CLI normalizer, POSIX zip builder, and out-of-repo smoke tester. |
| `[CREATE]` | `tests/test_agensi_packager.py::test_build_all_six_packs` | `(New)` | Pytest suite validating Positive, Negative, Boundary, UTF-8 No BOM, zero Vietnamese CLI leaks, zero broken markdown links, ZIP POSIX paths, AST isolation, and out-of-repo CLI execution. |
| `[CREATE]` | `docs/agensi-release-playbook.md` | `(New)` | Listing copy, pricing tiers ($0 / $5-$15), affiliate checklist, `skillspector.py` Agensi reviewer note, buyer troubleshooting guide, and final build/audit receipt. |

### Read-Only Upstream Sources (Zero Mutation — Read & Vendor Only)

| Role | Source File & Symbol Anchor | Line Range | Vendored / Adapted Behavior in Exported `dist/agensi/` |
| :--- | :--- | :---: | :--- |
| `[READ-ONLY]` | `tools/orchestration/goldfish_review.py::VAGUE_ASSERTION_PATTERNS` | `(L24-L60)` | Strip `import tools` bootstrap; rewrite `review-spec/SKILL.md` commands to `python scripts/goldfish_review.py`. |
| `[READ-ONLY]` | `tools/core/skillspector.py::scan_target` | `(L43-L55, L1222-L1291)` | Strip `import tools` & suppress `author_integrity` stderr noise; rewrite `SKILL.md` commands from `synapse skillspector` to `python scripts/skillspector.py`. |
| `[READ-ONLY]` | `tools/contrib/template_excel_exporter.py::find_project_config` | `(L18-L70, L478-L501)` | Vendor `tools/contrib/md_to_xlsx.py`; localize L478-L482 & `md_to_xlsx.py` L320-L321 Vietnamese/Synapse CLI hints to English; add `requirements.txt` (`openpyxl`) + friendly install guard. |
| `[READ-ONLY]` | `tools/manual/checklist_query.py::CANONICAL_FIELDS` | `(L33-L44)` | Rewrite `DEFAULT_CHECKLIST_PATH` to `../references/field_validation_checklist.md`; bundle with `tools/lint/manual_tc_linter.py` and `testing/manual/manual_testing_rules.md` into `rbt-manual-testing-excel`. |
| `[READ-ONLY]` | `tools/contrib/wcag_audit.py::WCAGAuditor` | `(L17-L60)` | Strip `import tools`; normalize `resources/implementation-playbook.md` into `references/`; rewrite `SKILL.md` to `python scripts/wcag_audit.py` (drop `agent-qa vpat`). |
| `[READ-ONLY]` | `tools/api/generate_api_matrix.py::get_field_fuzz_scenarios` | `(L15-L40)` | Bundle with `tools/api/api_drift_sentinel.py::load_spec` `(L12-L45)`, `tools/api/api_fuzzer.py::STACKTRACE_LEAK_PATTERNS` `(L19-L96)`, `tools/security/pentest_scope_guard.py` `(L65-L66)`, and `tools/api/fuzz_payloads.py`; anchor `HUB_ROOT`/`REPO_ROOT` to `os.getcwd()`. |
| `[READ-ONLY]` | `tools/lint/micro_mutator.py::ScopedMutationReceipt` | `(L23-L105, L1658)` | Vendor `tools/lint/equivalent_mutant_filter.py` & `tools/core/test_impact.py`; rewrite `tools.*` imports; anchor `HUB_ROOT` to `os.getcwd()`; merge `test-driven-development` + `verification-before-completion` into one clean `SKILL.md`. |

---

## 2. Data Flow & Interface Signatures

```text
skills/<domain>/<skill>/SKILL.md + tools/<target>.py + references/*
        │
        ▼ (AST import/root rewrite + English CLI polish + markdown link/CLI normalizer)
AgensiPackageSpec ──► Stage dist/agensi/<slug>.staging/ (SKILL.md, LICENSE, README.md, scripts/, references/, requirements.txt)
        │
        ▼ (Atomic replace -> POSIX zipfile + UTF-8 No BOM + link/CLI audit + SkillSpector gate)
dist/agensi/<slug>.zip ──► Extract to isolated temp dir outside repo (PYTHONPATH="") ──► Run CLI fixtures ──► SmokeTestReceipt
```

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AgensiPackageSpec:
    slug: str
    display_name: str
    pricing_tier: str
    suggested_price_usd: str
    source_skill_dirs: List[str]
    entry_scripts: List[str]
    vendored_modules: List[str]
    extra_references: Dict[str, str]
    pip_dependencies: List[str]
    smoke_test_cases: List[Dict[str, Any]]


@dataclass(frozen=True)
class DependencyRewriteReport:
    script_name: str
    stripped_tools_bootstrap: bool
    rewritten_imports: List[str]
    anchored_runtime_roots: bool
    localized_cli_strings: bool
    external_pip_deps: List[str]
    syntax_valid: bool


@dataclass(frozen=True)
class SmokeTestReceipt:
    slug: str
    zip_path: str
    extracted_in_isolated_dir: bool
    commands_run: int
    exit_code: int
    stdout_summary: str
    dead_cli_refs_found: int
    broken_links_found: int
    skillspector_verdict: str
    passed: bool


@dataclass(frozen=True)
class PackagerReportDTO:
    packages_built: int
    packages_passed: int
    specs: List[AgensiPackageSpec]
    rewrite_reports: List[DependencyRewriteReport]
    smoke_receipts: List[SmokeTestReceipt]
    passed: bool
```

---

## 3. Atomic Milestones & Execution DAG

### Milestone 1: Package Registry, AST Import & Runtime-Root Rewriter
- **Node ID:** `M1`
- **depends_on:** `[]`
- **consumes:** `[]`
- **produces:** `[{'contract': 'AgensiPackageSpec'}, {'contract': 'DependencyRewriteReport'}]`
- **Files Modified:** `scripts/package_agensi_skills.py`
- **Write Set:** `['scripts/package_agensi_skills.py']`
- **Compute Tier:** `[Model: Pro | Thinking: High]`
- **Scope:** Define `AgensiPackageSpec` entries for all 6 launch packages (`review-spec`, `skillspector-security-guard`, `rbt-manual-testing-excel`, `wcag-a11y-audit`, `api-contract-and-fuzzer`, `anti-fake-pass-mutation`), implement AST-verified stripping of `_TOOLS_ROOT`/`import tools` bootstraps, local sibling import rewrites (`tools.lint.*`, `tools.contrib.*`, `tools.*`), `author_integrity` noise suppression in standalone `skillspector.py`, `HUB_ROOT`/`REPO_ROOT` -> `os.getcwd()` anchoring (and `checklist_query.py` `DEFAULT_CHECKLIST_PATH` -> `../references/field_validation_checklist.md`), and English CLI help/error localization for `template_excel_exporter.py` & `md_to_xlsx.py`.
- **Circuit Breaker:** Max Fix Attempts = 2; stop if `ast.parse()` fails on any rewritten script or any upstream file under `tools/` is mutated.
- **Rollback Hook:** `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(created_files=['scripts/package_agensi_skills.py'])"`

### Milestone 2: Bundle Assembler, Markdown/CLI Normalizer & Atomic POSIX Zip Builder
- **Node ID:** `M2`
- **depends_on:** `['M1']`
- **consumes:** `[{'contract': 'AgensiPackageSpec'}, {'contract': 'DependencyRewriteReport'}]`
- **produces:** `[{'contract': 'PackagerReportDTO'}]`
- **Files Modified:** `scripts/package_agensi_skills.py`
- **Write Set:** `['scripts/package_agensi_skills.py']`
- **Compute Tier:** `[Model: Flash | Thinking: Off]`
- **Scope:** Generate normalized standalone `SKILL.md` for each package (valid `agentskills.io` frontmatter with `name == slug`, `description <= 1024`, `license: MIT`, `compatibility`, `metadata.author: Thế Vị (@TeeVee98)`; unified `SKILL.md` for `anti-fake-pass-mutation`; zero dead `agent-qa`/`synapse`/`tools/` commands; all relative links resolved including bundled `references/manual_testing_rules.md` and `references/implementation-playbook.md`), copy `LICENSE`, emit buyer `README.md` + `requirements.txt`, enforce 100% UTF-8 No BOM, and build POSIX `.zip` via atomic staging directory replacement into `dist/agensi/`.
- **Circuit Breaker:** Max Fix Attempts = 2; halt if any markdown relative link fails resolution, any dead CLI ref (`agent-qa`, `synapse `, `tools/`) survives, or zip contains `\` separators.
- **Rollback Hook:** `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(created_files=['scripts/package_agensi_skills.py'])"`

### Milestone 3: Isolated Out-of-Repo Smoke Tester & Security Hygiene Gate
- **Node ID:** `M3`
- **depends_on:** `['M2']`
- **consumes:** `[{'contract': 'PackagerReportDTO'}]`
- **produces:** `[{'contract': 'SmokeTestReceipt'}]`
- **Files Modified:** `scripts/package_agensi_skills.py`
- **Write Set:** `['scripts/package_agensi_skills.py']`
- **Compute Tier:** `[Model: Pro | Thinking: High]`
- **Scope:** Implement `--verify-isolated` runner extracting each `.zip` into an isolated `tempfile.TemporaryDirectory()` outside the repo (`PYTHONPATH=""`, `cwd=temp_work_dir`, `timeout=15s`), running `--help` plus real functional invocations for every entry script (`goldfish_review.py` on sample spec, `skillspector.py` on sample SKILL.md, `checklist_query.py --fields email,password` + `manual_tc_linter.py` + `template_excel_exporter.py` with & without `openpyxl`, `wcag_audit.py` on sample HTML, `generate_api_matrix.py` + `api_drift_sentinel.py` + `api_fuzzer.py --dry-run` on sample OpenAPI, `micro_mutator.py --dry-run` on sample Python file), asserting zero writes outside `temp_work_dir`, and running `skillspector.py` across all 6 folders (plus documenting static-pattern scan review behavior for `skillspector.py` itself).
- **Circuit Breaker:** Max Fix Attempts = 2; fail closed on any `ModuleNotFoundError`, raw traceback, non-English CLI leak, or unintended file write outside `cwd`.
- **Rollback Hook:** `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(created_files=['scripts/package_agensi_skills.py'])"`

### Milestone 4: 4-Scenario Pytest Verification Suite
- **Node ID:** `M4`
- **depends_on:** `['M3']`
- **consumes:** `[{'contract': 'SmokeTestReceipt'}, {'contract': 'PackagerReportDTO'}]`
- **produces:** `[{'contract': 'VerifiedPytestSuite'}]`
- **Files Modified:** `tests/test_agensi_packager.py`
- **Write Set:** `['tests/test_agensi_packager.py']`
- **Compute Tier:** `[Model: Flash | Thinking: Off]`
- **Scope:** Implement pytest coverage across 4 scenarios: (a) Positive full 6-pack build + isolated functional execution receipts + zero stray files outside `cwd`, (b) Negative invalid `--slug` and malformed source rejection without partial zip creation, (c) Boundary missing `openpyxl` blocked-import guard (verifying clean English install guidance without traceback), empty HTML/OpenAPI inputs, and `checklist_query.py` isolated lookup, (d) CLI `--build-all`, `--slug`, `--verify-isolated`, `--json` contract assertions.
- **Circuit Breaker:** Max Fix Attempts = 2; forbid empty tests or relaxed assertions.
- **Rollback Hook:** `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(created_files=['tests/test_agensi_packager.py'])"`

### Milestone 5: Listing Copy, Pricing & Buyer Support Playbook
- **Node ID:** `M5`
- **depends_on:** `['M2']`
- **consumes:** `[{'contract': 'PackagerReportDTO'}]`
- **produces:** `[{'contract': 'ReleasePlaybookDoc'}]`
- **Files Modified:** `docs/agensi-release-playbook.md`
- **Write Set:** `['docs/agensi-release-playbook.md']`
- **Compute Tier:** `[Model: Flash | Thinking: Off]`
- **Scope:** Write ready-to-paste Agensi.io upload metadata (Title, Short Summary, About, FAQ, Pricing tiers Free / $5-$15, affiliate 90%/20% distribution checklist, Agensi security-review explanation note for `skillspector-security-guard` containing detection regexes, and buyer quickstart/troubleshooting guide) for all 6 packages.
- **Circuit Breaker:** Max Fix Attempts = 2; preserve MIT copyright attribution (`Thế Vị (@TeeVee98)`) across all listings.
- **Rollback Hook:** `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(created_files=['docs/agensi-release-playbook.md'])"`

### Milestone 6: End-to-End 6-Pack Build, Audit & Hub Impact Certification
- **Node ID:** `M6`
- **depends_on:** `['M4', 'M5']`
- **consumes:** `[{'contract': 'VerifiedPytestSuite'}, {'contract': 'ReleasePlaybookDoc'}]`
- **produces:** `[{'contract': 'CertifiedReleaseArtifacts'}]`
- **Files Modified:** `docs/agensi-release-playbook.md`
- **Write Set:** `['docs/agensi-release-playbook.md']`
- **Compute Tier:** `[Model: Pro | Thinking: High]`
- **Scope:** Build all 6 `.zip` artifacts in `dist/agensi/`, run isolated smoke tests, `pytest tests/test_agensi_packager.py -v`, `python tools/lint/cli_schema_sentinel.py --check --json`, and `python tools/core/verify_all.py --mode hub --tier impact`; append empirical verification receipt table to `docs/agensi-release-playbook.md` and confirm `git status` shows zero edits to `tools/` or `skills/`.
- **Circuit Breaker:** Max Fix Attempts = 2; stop and report if any pre-existing Hub gate fails outside task scope.
- **Rollback Hook:** `python -c "from tools.lint.plan_schema_sentinel import rollback_path_scoped_detailed; rollback_path_scoped_detailed(created_files=['docs/agensi-release-playbook.md'])"`

---

## 4. Verification Matrix

| Scenario | Package / Target | Command to Execute | Deterministic Expected Result |
| :--- | :--- | :--- | :--- |
| **Positive (Build + Isolated Functional Run)** | All 6 packs in `dist/agensi/` | `python scripts/package_agensi_skills.py --build-all --verify-isolated --json` | `passed: true`, `packages_built == 6`, `packages_passed == 6`, all `exit_code == 0`, `dead_cli_refs_found == 0`, `broken_links_found == 0` from isolated temp dirs outside repo. |
| **Negative (Bad Input / Unknown Slug)** | Invalid `--slug unknown-pack` | `pytest tests/test_agensi_packager.py -k "negative" -v` | Non-zero exit code with structured JSON error; zero partial/corrupt `.zip` written. |
| **Boundary (Missing `openpyxl` / Empty Spec / `cwd` Isolation)** | `rbt-manual-testing-excel`, `api-contract-and-fuzzer`, `anti-fake-pass-mutation` | `pytest tests/test_agensi_packager.py -k "boundary" -v` | Blocked `openpyxl` import prints clean English `pip install -r requirements.txt` message (no traceback, no Vietnamese text); `checklist_query.py` resolves `../references/field_validation_checklist.md`; no writes outside `cwd`. |
| **CLI, Schema & Hub Impact Hygiene** | Packager, tests, docs, and all 6 zips | `pytest tests/test_agensi_packager.py -v` and `python tools/lint/cli_schema_sentinel.py --check --json` and `python tools/core/verify_all.py --mode hub --tier impact` | All pytest tests pass; `cli_schema_sentinel` reports `drift_count == 0` and `unregistered_public == []`; every zip passes UTF-8 No BOM and `SkillSpector` audit. |

---

## 5. Tri-Vulnerability Self-Critique (Red-Teaming)

1. **Race Condition & Idempotent Staging (`race_condition`):** Re-running or overlapping builds targeting `dist/agensi/<slug>/` can mix stale files from older builds. Mitigation: stage every build in a clean `dist/agensi/<slug>.staging/` directory and atomically swap folder + `.zip` only after all validations pass.
2. **Boundary, Runtime Paths & Agensi Scanner Limits (`boundary_resource`):**
   - **Runtime Root Drift:** Running scripts from `.claude/skills/<slug>/scripts/` makes `SCRIPT_DIR/../..` resolve inside `.claude/skills/` instead of the buyer's workspace. Mitigation: rewrite runtime roots (`HUB_ROOT`, `REPO_ROOT`, `REPORTS_DIR`, `DEFAULT_AUDIT_LOG`) to `os.getcwd()` and assert zero writes into the extracted skill directory during isolated smoke tests.
   - **Missing Optional Dependencies & Non-English Leaks:** Buyers without `openpyxl` or `pathspec` must never hit raw tracebacks or Vietnamese CLI hints (`template_excel_exporter.py` L478-L482). Mitigation: inject English CLI guard + `requirements.txt` and test with `openpyxl` explicitly blocked via `sys.modules`.
   - **Agensi Static Security Scanner on `skillspector.py`:** Because `skillspector.py` contains 71 attack-detection regex patterns and skips itself (`SKIP_FILES`), Agensi's automated scanner may flag it for manual review. Mitigation: document a concise Agensi reviewer note in `docs/agensi-release-playbook.md` and ensure zero live execution or unsafe shell-pipe instructions appear anywhere in `SKILL.md` or scripts; bound all smoke-test subprocesses with `timeout=15s`.
3. **Backward Compatibility & Blast Radius (`backward_compat`):** Placing the packager at `scripts/package_agensi_skills.py` and writing outputs strictly under gitignored `dist/agensi/` guarantees zero mutations to upstream `tools/`, `skills/`, `tools_schema.json`, or `TOOL_CATALOG.json`, while preserving MIT copyright attribution (`Thế Vị (@TeeVee98)`) in every package's `LICENSE`, `SKILL.md`, and `README.md`.

---

## Recommended Execution Model & Thinking Level

- **Primary Executor Model & Thinking Level (Single-Session Default):** `Gemini 4 Hydrogen (High)` running sequentially via `/solo` (`M1 -> M2 -> M3 -> M4 -> M5 -> M6`).
- **Milestone Escalation Overrides (`/teamwork` Only):** Under default `/solo`, all milestones run sequentially in one session on `Gemini 4 Hydrogen (High)`. If explicitly invoking `/teamwork`, `M1` and `M3` (AST/runtime-root rewriting & isolated smoke-test harness) can use `Gemini 4 Neon (High)`, while `M2`, `M4`, `M5` use `Flash`.
- **Rationale:** AST import/root rewriting across 12 source scripts, English CLI polish, and isolated out-of-repo subprocess verification need high reasoning accuracy without paying `Neon` overhead on documentation and boilerplate milestones.
