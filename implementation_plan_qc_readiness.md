<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: QC Team Readiness Upgrade (v4.9.1 Prep)

> **Reference Protocol:** [AGENTS.md §5](AGENTS.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md), [.agent/skills/super-plan/SKILL.md](.agent/skills/super-plan/SKILL.md)
> **Grounding Verification:** Inspected files: `tools/orchestration/solo_runner.py`, `tools/orchestration/worktree_manager.py`, `tools/core/gates/gate_06_credentials.py`, `tools/lint/git_pre_commit_guard.py`, `tests/test_architectural_hardening.py`, `tests/test_perfection_10.py`, `tests/test_solo_runner.py`, `tests/test_i18n.py`, `tests/test_git_pre_commit_guard.py`, `README.md`, `README.en.md`, `package.json`, `pyproject.toml`
> **Risk-Routing Telemetry:** Tier `DEEP_SUPER_PLAN` | `RiskScore: 0.40` | `Fan-In: 10` | `CrossBoundary: false` | `StateMutation: false` | `HistoryDrift: 0.10`
> **Execution Mode:** Sequential Single-Agent `/solo` (Default — 1 session, `M1 -> M2 -> M3 -> M4 -> M5`, zero `swarm` workers)
> **Ambiguity Gate Status:** Resolved via user decisions (A1: Truthful NPM + GitHub pip docs, remove unverified PyPI claim; A2: Bilingual 1-pager `docs/QC_QUICKSTART.md` & `.en.md` with no new CLI subcommand; A3: Fold uncommitted Gate 6 Telegram Bot Token changes into this plan for unified 11/11 DoD green certification)
> **Plan Changelog (v1.0):**
> - Initial spec-driven super-plan drafted for QC team rollout readiness (`implementation_plan_qc_readiness.md`), keeping root `implementation_plan.md` untouched.

---

## 0. Architectural Tournament & Design Ruling

| Branch | Strategy | Diff Scope | Regression Risk | Decision |
|---|---|---|---|---|
| **Branch A (Minimalist — Selected)** | Fix Windows `python3` resolution inside `BaseTestAdapter.execute`, update 2 Windows NTFS junction tests + 1 timeout margin, certify Gate 6 Telegram token parity, add bilingual 1-pager `docs/QC_QUICKSTART*.md`, and align `README*.md` to verified NPM + GitHub pip channels. | 10 modified + 2 new files (zero new CLI subcommands, zero new dependencies) | **Low** | **SELECTED** |
| **Branch B (Clean Adapter + CLI Command)** | Introduce a dedicated `CommandNormalizer` abstraction and register a new `synapse-hub quickstart` CLI subcommand across `bin/agent-qa.js`, `tools/core/cli.py`, and `tools/tools_schema.json`. | 15+ files + schema/catalog regen | Medium | Rejected (user chose docs-only 1-pager to avoid CLI bloat) |
| **Branch C (Full PyPI Release Pipeline)** | Build & activate a new GitHub Actions PyPI Trusted Publishing workflow (`publish_pypi.yml`) alongside README PyPI instructions. | CI secrets + external PyPI account setup | Medium-High | Deferred (user chose truthful GitHub install until PyPI is configured) |

> **Ruling:** Adopt Branch A — resolves all 5 deterministic Windows Gate 7 failures at the root, eliminates broken PyPI onboarding traps, delivers a 3-minute QC Quickstart 1-pager, and unifies Gate 6 Telegram secret scanning into one clean 11/11 DoD certification — **Cost:** pure-Python QC users install via GitHub URL until a future PyPI workflow is configured.

---

## 1. Affected Files & Blast Radius

### Target Files & Structural Anchors

| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/orchestration/solo_runner.py` (AST: execute) (L729-L749) | Normalize `python3` / Windows Store `WindowsApps` stub to `sys.executable` inside `BaseTestAdapter.execute` via `_normalize_python_command` |
| `[MODIFY]` | `tests/test_solo_runner.py` (AST: test_red_phase_error_fingerprint) (L536-L548) | Verify `certify_red_phase` passes on Windows with `python3 -c` and add 4-scenario unit tests for `_normalize_python_command` |
| `[MODIFY]` | `tests/test_architectural_hardening.py` (AST: test_tc04_worktree_dependency_sharing) (L96-L106) | Accept valid Windows NTFS junction (`os.path.isjunction`) alongside POSIX symlink; verify `test_tc03_*` pass via M1 normalization |
| `[MODIFY]` | `tests/test_perfection_10.py` (AST: test_tc01_worktree_link_directory_creation) (L51-L68) | Accept `link_type in ("symlink", "junction")` on `win32` when `os.symlink` falls back to NTFS junction; preserve strict `"symlink"` check on POSIX |
| `[MODIFY]` | `tests/test_i18n.py` (AST: test_cli_lang_persistence_via_flag) (L835-L881) | Raise subprocess timeout from `5`s to `15`s so `pytest -n auto` parallel workers do not flake near the 4.93s baseline |
| `[MODIFY]` | `tools/core/gates/gate_06_credentials.py` (AST: gate_6_credential_security) (L50-L60) | Finalize Telegram Bot Token pattern (`\b\d{8,12}:AA[A-Za-z0-9_-]{33}\b`) in Gate 6 directory scanner |
| `[MODIFY]` | `tools/lint/git_pre_commit_guard.py` (AST: check_secrets) (L239-L249) | Finalize parity Telegram Bot Token pattern in `GATE_6_SECRET_PATTERNS` for pre-commit diff scanning |
| `[MODIFY]` | `tests/test_git_pre_commit_guard.py` (AST: test_check_secrets_detects_telegram_bot_token_and_gate6_parity) (L128-L161) | Verify 4-scenario Telegram Bot Token detection, boundary exclusion, and `# gate6-allowlist` parity |
| `[CREATE]` | `docs/QC_QUICKSTART.md` (New) | Vietnamese 1-page QC onboarding cheat sheet (Manual QC: 3 commands; Automation QC: 4 commands; Troubleshooting) |
| `[CREATE]` | `docs/QC_QUICKSTART.en.md` (New) | English parity 1-page QC onboarding cheat sheet (Manual QC: 3 commands; Automation QC: 4 commands; Troubleshooting) |
| `[MODIFY]` | `README.md` (L75-L130) | Replace nonexistent PyPI `pip install synapse-hub` claim with verified NPM + GitHub `pip install git+...` channels and link `docs/QC_QUICKSTART.md` |
| `[MODIFY]` | `README.en.md` (L75-L130) | Mirror distribution truthfulness update and link `docs/QC_QUICKSTART.en.md` in English README |

### Blast Radius & Downstream Dependencies
- **Direct Callers:** `tools/orchestration/solo_runner.py::certify_red_phase`, `tools/orchestration/solo_runner.py::certify_green_phase`, `tools/core/verify_all.py::gate_6_credential_security`, `tools/core/verify_all.py::gate_7_infer_linter`, `tools/lint/lint_ai_docs.py`
- **Downstream Tests:** `pytest tests/test_solo_runner.py tests/test_architectural_hardening.py tests/test_perfection_10.py tests/test_i18n.py tests/test_git_pre_commit_guard.py`
- **Regression Risk:** Low — zero breaking signature changes; POSIX behavior remains strictly unchanged; zero new third-party dependencies.
- **Mitigation Strategy:** Preserve existing function signatures (`BaseTestAdapter.execute`, `gate_6_credential_security`, `check_secrets`); restrict `python3` substitution exclusively to `win32` when `shutil.which` resolves missing or a `WindowsApps` Store stub.

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY DTOs, contracts, and function signatures with strict types. Full implementation bodies are deferred to sequential `/solo` execution.

### Schemas & Contract DTO Types
```python
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class WindowsRunnerContract:
    normalized_cmd: List[str]
    substituted_python: bool
    platform: str
    reason: str


@dataclass(frozen=True)
class WindowsTestParityContract:
    worktree_link_types_allowed: Tuple[str, ...]
    i18n_subprocess_timeout_sec: int
    windows_gate7_failures: int


@dataclass(frozen=True)
class Gate6SecretRuleContract:
    rule_label: str
    pattern: str
    gate6_parity_verified: bool
    allowlist_supported: bool


@dataclass(frozen=True)
class QcQuickstartDocContract:
    vi_doc_path: str
    en_doc_path: str
    manual_qc_command_count: int
    automation_qc_command_count: int
    utf8_no_bom_verified: bool


@dataclass(frozen=True)
class QcReleaseReadinessContract:
    target_patch_version: str
    gates_passed: int
    gates_total: int
    readme_pypi_drift_resolved: bool
    ready_for_manual_release: bool
```

### Function & Helper Signatures
```python
def _normalize_python_command(
    cmd_parts: List[str],
    platform_name: Optional[str] = None,
    resolved_which: Optional[str] = None,
    executable: Optional[str] = None,
) -> List[str]:
    """Rewrites Windows 'python3' / Store WindowsApps stub invocations to sys.executable.

    Guarantees:
      - Returns cmd_parts unchanged on non-win32 platforms or when cmd_parts is empty.
      - Leaves non-python3 binaries (pytest, node, npx, python) untouched.
      - Substitutes sys.executable on win32 when python3 is absent or resolves under WindowsApps.
    """
    ...


def _is_directory_link_or_junction(path: str) -> bool:
    """Returns True when path is a POSIX/Windows symlink or a Windows NTFS junction."""
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Windows Python3 Runtime Normalization in Solo Runner
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High]`
- **Files Modified (Max 2):** `tools/orchestration/solo_runner.py`, `tests/test_solo_runner.py`
- **Write Set:** `['tools/orchestration/solo_runner.py', 'tests/test_solo_runner.py']`
- **produces:** `[{'contract': 'WindowsRunnerContract'}]`
- **Goal:** Implement `_normalize_python_command` in `tools/orchestration/solo_runner.py` and wire it into `BaseTestAdapter.execute` so Windows `python3` / Microsoft Store stub commands execute via `sys.executable`. Add unit tests covering positive substitution, POSIX pass-through, real non-stub `python3`, and empty command boundary in `tests/test_solo_runner.py`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside M1 write-set are touched | Rollback: `git checkout -- tools/orchestration/solo_runner.py tests/test_solo_runner.py`
- **Rollback Hook:** `git checkout -- tools/orchestration/solo_runner.py tests/test_solo_runner.py`
- **Pass Gate:** `pytest tests/test_solo_runner.py -k "test_red_phase_error_fingerprint or normalize_python_command"`

### Milestone 2: Windows Worktree Junction Parity & i18n Timeout Stabilization
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 3):** `tests/test_architectural_hardening.py`, `tests/test_perfection_10.py`, `tests/test_i18n.py`
- **Write Set:** `['tests/test_architectural_hardening.py', 'tests/test_perfection_10.py', 'tests/test_i18n.py']`
- **consumes:** `[{'contract': 'WindowsRunnerContract'}]`
- **produces:** `[{'contract': 'WindowsTestParityContract'}]`
- **Goal:** Update `test_tc04_worktree_dependency_sharing` and `test_tc01_worktree_link_directory_creation` to validate NTFS junctions on `win32` while preserving strict `"symlink"` assertions on POSIX; confirm `test_tc03_*` pass cleanly via M1; increase `test_cli_lang_persistence_via_flag` subprocess timeout from `5`s to `15`s in `tests/test_i18n.py`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside M2 write-set are touched | Rollback: `git checkout -- tests/test_architectural_hardening.py tests/test_perfection_10.py tests/test_i18n.py`
- **Rollback Hook:** `git checkout -- tests/test_architectural_hardening.py tests/test_perfection_10.py tests/test_i18n.py`
- **Pass Gate:** `pytest tests/test_architectural_hardening.py tests/test_perfection_10.py tests/test_i18n.py -q`

### Milestone 3: Gate 6 Telegram Bot Token Rule Parity & Verification
- **Node ID:** `M3` | **depends_on:** `[M2]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 3):** `tools/core/gates/gate_06_credentials.py`, `tools/lint/git_pre_commit_guard.py`, `tests/test_git_pre_commit_guard.py`
- **Write Set:** `['tools/core/gates/gate_06_credentials.py', 'tools/lint/git_pre_commit_guard.py', 'tests/test_git_pre_commit_guard.py']`
- **consumes:** `[{'contract': 'WindowsTestParityContract'}]`
- **produces:** `[{'contract': 'Gate6SecretRuleContract'}]`
- **Goal:** Audit, harden, and certify the Telegram Bot Token regex across Gate 6 (`gate_6_credential_security`) and `git_pre_commit_guard.py` (`GATE_6_SECRET_PATTERNS`), verifying 4-scenario coverage (positive leak, negative env lookup, boundary short colon string, `# gate6-allowlist` bypass) with zero false positives across the repository.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside M3 write-set are touched | Rollback: `git checkout -- tools/core/gates/gate_06_credentials.py tools/lint/git_pre_commit_guard.py tests/test_git_pre_commit_guard.py`
- **Rollback Hook:** `git checkout -- tools/core/gates/gate_06_credentials.py tools/lint/git_pre_commit_guard.py tests/test_git_pre_commit_guard.py`
- **Pass Gate:** `pytest tests/test_git_pre_commit_guard.py -q`

### Milestone 4: Bilingual QC Quickstart 1-Pager Authoring
- **Node ID:** `M4` | **depends_on:** `[M3]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `docs/QC_QUICKSTART.md`, `docs/QC_QUICKSTART.en.md`
- **Write Set:** `['docs/QC_QUICKSTART.md', 'docs/QC_QUICKSTART.en.md']`
- **consumes:** `[{'contract': 'Gate6SecretRuleContract'}]`
- **produces:** `[{'contract': 'QcQuickstartDocContract'}]`
- **Goal:** Create concise, zero-overwhelm 1-page QC onboarding guides in Vietnamese (`docs/QC_QUICKSTART.md`) and English (`docs/QC_QUICKSTART.en.md`) presenting exactly 3 daily commands for Manual QC (`doctor`, `export-excel`, `scaffold-tc` + VS Code Extension) and 4 daily commands for Automation QC (`doctor`, `init --profile standard`, `lint`, `verify`), plus a 3-item Windows/PATH troubleshooting table.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside M4 write-set are touched | Rollback: `rm -f docs/QC_QUICKSTART.md docs/QC_QUICKSTART.en.md`
- **Rollback Hook:** `rm -f docs/QC_QUICKSTART.md docs/QC_QUICKSTART.en.md`
- **Pass Gate:** `python tools/lint/lint_ai_docs.py`

### Milestone 5: Distribution Truthfulness in READMEs & Full 11/11 DoD Certification
- **Node ID:** `M5` | **depends_on:** `[M4]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `README.md`, `README.en.md`
- **Write Set:** `['README.md', 'README.en.md']`
- **consumes:** `[{'contract': 'QcQuickstartDocContract'}]`
- **produces:** `[{'contract': 'QcReleaseReadinessContract'}]`
- **Goal:** Remove the unverified `pip install synapse-hub` PyPI claim from `README.md` and `README.en.md`, document verified installation channels (`npx @teevee98/synapse-hub`, `npm install -g @teevee98/synapse-hub`, and Python GitHub source `pip install git+https://github.com/TeeVee98/Synapse-Hub.git`), add prominent links to `docs/QC_QUICKSTART.md` / `docs/QC_QUICKSTART.en.md`, and execute full 11/11 DoD verification (`verify_all.py --mode hub --parallel`), `invariant_checker.py`, and VS Code extension unit tests without auto-pushing or auto-publishing.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt on out-of-scope legacy failures | Rollback: `git checkout -- README.md README.en.md`
- **Rollback Hook:** `git checkout -- README.md README.en.md`
- **Pass Gate:** `python tools/core/verify_all.py --mode hub --parallel`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Positive: Windows `python3` Stub Normalization | `cmd_parts=['python3', '-c', 'assert 1==2']`, `platform_name='win32'`, `resolved_which='C:\\Users\\X\\AppData\\Local\\Microsoft\\WindowsApps\\python3.exe'` | `_normalize_python_command` returns `[sys.executable, '-c', 'assert 1==2']`; `certify_red_phase` returns `status == 'CERTIFIED_RED'` | `pytest tests/test_solo_runner.py -k "test_red_phase_error_fingerprint or normalize_python_command"` |
| **TC-02** | Negative: POSIX & Non-Python Pass-Through | `cmd_parts=['python3', '-m', 'pytest']` on `platform_name='linux'`, or `cmd_parts=['npx', 'playwright', 'test']` on `win32` | `_normalize_python_command` returns `cmd_parts` unmodified without rewriting binary | `pytest tests/test_solo_runner.py -k "normalize_python_command"` |
| **TC-03** | Boundary: Empty Command & Env Error Red Rejection | `cmd_parts=[]` and `certify_red_phase` with `ECONNREFUSED` error on Windows | Empty list returns `[]` without `IndexError`; `test_tc03_negative_environmental_red_rejected` returns `status == 'ENVIRONMENT_ERROR_RED_REJECTED'` | `pytest tests/test_architectural_hardening.py -k "test_tc03"` |
| **TC-04** | Cross-Platform Worktree Junction & Parallel Timeout | `link_shared_dependencies` and `create_directory_link` on Windows without Admin/Developer Mode + `test_cli_lang_persistence_via_flag` under `-n auto` | `link_type in ('symlink', 'junction')` on `win32`; `test_tc04_worktree_dependency_sharing`, `test_tc01_worktree_link_directory_creation`, and `test_cli_lang_persistence_via_flag` all PASS | `pytest tests/test_architectural_hardening.py tests/test_perfection_10.py tests/test_i18n.py -n auto -q` |
| **TC-05** | Gate 6 Telegram Secret Parity & Allowlist | Synthetic Telegram token diff, env lookup diff, short colon boundary, and `# gate6-allowlist` file | Leaked token blocked by both `check_secrets` and `gate_6_credential_security`; clean boundary and allowlisted line pass | `pytest tests/test_git_pre_commit_guard.py -k "telegram"` |
| **TC-06** | Docs Link Integrity, Rule 16 & Full 11/11 DoD Gate | `docs/QC_QUICKSTART.md`, `docs/QC_QUICKSTART.en.md`, `README.md`, `README.en.md` on Windows | `lint_ai_docs.py` exits 0 (0 broken links); `invariant_checker.py --json` exits 0 (0 violations); `verify_all.py --mode hub --parallel` reports `11/11 PASS` (`0 failed`) | `python tools/lint/lint_ai_docs.py` and `python tools/core/verify_all.py --mode hub --parallel` |

---

## 5. Tri-Vulnerability Self-Critique (Red-Teaming)

1. **Race Condition & Parallel Concurrency (`race_condition`):**
   - *Risk:* Running `pytest -n auto` across 12+ workers causes CPU contention on Windows subprocess tests (observed 4.93s runtime hitting a 5s timeout in `tests/test_i18n.py::test_cli_lang_persistence_via_flag` and transient `INTERRUPTED_OR_USAGE_ERROR_RED_REJECTED` when competing with concurrent `verify_all.py`).
   - *Mitigation:* Raise subprocess timeout in `tests/test_i18n.py` to `15`s without weakening any stdout/exit-code assertions, and run `verify_all.py --mode hub --parallel` standalone during M5 certification rather than concurrently with an external `pytest -n auto` process.
2. **Boundary & Extreme Input Resilience (`boundary_resource`):**
   - *Risk:* Empty `cmd_parts` (`[]`), whitespace-only `test_cmd`, missing `python3` binary (`shutil.which` returning `None`), or a case-insensitive Windows path containing `windowsapps\python3.exe` could trigger `IndexError` or bypass normalization.
   - *Mitigation:* Guard `if not cmd_parts: return []`, compare `os.path.basename(cmd_parts[0]).lower() in ("python3", "python3.exe")`, and match `windowsapps` case-insensitively on `resolved_which`. For Gate 6 Telegram tokens, enforce exact digit/prefix length (`\b\d{8,12}:AA[A-Za-z0-9_-]{33}\b`) so short `host:port` or `id:label` strings never trigger false positives.
3. **Backward Compatibility & Blast Radius (`backward_compat`):**
   - *Risk:* Modifying `BaseTestAdapter.execute` affects all callers of `certify_red_phase` and `certify_green_phase`; changing symlink tests could accidentally weaken POSIX symlink verification; editing `README.md` / `README.en.md` could break Gate 4 relative link checks or Rule 16 invariants.
   - *Mitigation:* Keep `_normalize_python_command` strictly scoped to `win32` + broken/stub `python3` (zero impact on Linux/macOS CI or custom virtualenvs); gate the `junction` assertion strictly under `sys.platform == "win32"` while keeping strict `"symlink"` on POSIX; validate all Markdown links via `tools/lint/lint_ai_docs.py` and invariants via `tools/lint/invariant_checker.py --json`.

---

## 6. Recommended Execution Model & Thinking Level

- **Primary Executor Model & Thinking Level (Single-Session `/solo` Default):** **`Gemini 4 Hydrogen (High)`**
- **Milestone Escalation Overrides (Optional / `/teamwork` Only):** Under default `/solo`, run all 5 milestones (`M1 -> M2 -> M3 -> M4 -> M5`) sequentially in a single session on `Gemini 4 Hydrogen (High)`. Only if manually escalating or explicitly invoking `/teamwork`, assign `M1` (`solo_runner.py` runtime normalization + live mutation check) to `Gemini 4 Neon (Medium)` and keep `M2–M5` on `Gemini 4 Hydrogen (Medium/High)`.
- **Rationale:** `RiskScore` is moderate (`0.40`) with localized, deterministic changes across Windows test/runtime parity, Gate 6 regex verification, and bilingual documentation. `Gemini 4 Hydrogen (High)` provides strong accuracy for `/solo` Red-Green-Mutation-Purple execution at significantly lower token cost and faster latency than `Gemini 4 Neon (High)`.
