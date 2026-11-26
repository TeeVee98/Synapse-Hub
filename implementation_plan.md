<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Spec-Driven Implementation Plan: Closed-Loop Hardening of `/review` Command (v2.1)

> **Reference Protocol:** [AGENTS.md Section 5](AGENTS.md), [standards/qa-process/plan-protocol.md](standards/qa-process/plan-protocol.md)
> **Pre-Plan Model Fit Gate:** Recommended `Gemini 4 Neon (High)` (Tier 2 Deep-Track: RiskScore `0.355`, Transitive Fan-In `26`, Blast Radius `29` across 11 files)
> **Execution Mode:** Single-Agent Sequential (`/solo`) - One session, one recommended model/thinking level, executing milestones sequentially (`M1 -> M2 -> M3 -> M4 -> M5`). Do NOT spawn `swarm` workers or parallel subagents.
> **Ambiguity Gate Status:** Resolved (`has_ambiguity: false` via `super_plan_engine.py ambiguity-check`)
> **Plan Changelog (v1.0):**
> - Initial deep evaluation and hardening blueprint grounded in live AST inspection of `senior_code_review.py`, `plan_review_auditor.py`, `solo_contracts.py`, `solo_runner.py`, `plan_dag_bridge.py`, and `output_diff_sentinel.py`.

---

## Orthogonal Architectural Tournament (3-Way Branching)

- **Branch A (Minimalist Patch):** Patch only `senior_code_review.py` regexes and `--strict-solo` missing-file checks without touching `solo_contracts.py` or `plan_dag_bridge.py`. *Rejected:* Leaves `assert True` tautologies, unsigned mutation receipts, multi-file milestone receipt overwrites, and `OutputDiffSentinel` staged/branch mismatch unresolved.
- **Branch B (Layered Closed-Loop Hardening - Selected):** Strengthen leaf contracts (`solo_contracts.py`, `output_diff_sentinel.py`), harden diff/AST/CoVe/read-only hygiene in `senior_code_review.py`, close Layer 2-5 AST/provenance gaps in `plan_review_auditor.py`, aggregate/sign mutation receipts in `plan_dag_bridge.py` + `solo_runner.py`, and publish `ADR-0027` + updated `.agent/skills/review/SKILL.md`. Keeps `plan_review_auditor.py` strictly acyclic with `solo_runner.py`.
- **Branch C (Full External AST/LSP Daemon Rewrite):** Replace `senior_code_review.py` and `plan_review_auditor.py` with a persistent LSP sidecar daemon. *Rejected:* Violates Lean Dev, introduces stateful daemon lifecycle risks, and breaks CLI backward compatibility.

---

## 1. Affected Files & Blast Radius

### Target Files & Structural Anchors
| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[MODIFY]` | `tools/orchestration/solo_contracts.py` (AST: AstTautologyAnalyzer) | Add opt-in true-tautology detection (`assert True`, `assert 1 == 1`), `compute_mutation_receipt_hmac`, `verify_mutation_receipt_hmac`, and read-only HMAC key lookup (`create_if_missing=False`). |
| `[MODIFY]` | `tools/lint/output_diff_sentinel.py` (AST: OutputDiffSentinel) | Support `target` (`uncommitted`, `staged`, branch ref) in `audit_git_diff` instead of hardcoding unstaged `git diff --numstat`. |
| `[MODIFY]` | `tools/orchestration/senior_code_review.py` (AST: evaluate_review) | Include untracked `[CREATE]` files in `uncommitted` diff, fix `parse_diff` `\ No newline` offsets and quoted paths, check body-edited functions for nesting/mutable defaults, add AST unused import/var `simplify` check, replace self-referential `--verify-cove` with factual claim-vs-disk verification, and avoid read-only key/cache writes. |
| `[MODIFY]` | `tests/test_senior_code_review.py` (AST: TestSeniorCodeReview) | Add regression tests for untracked `[CREATE]` files, `assert True` fake passes, edited-body deep nesting, `\ No newline` line mapping, staged/branch diff bloat, unused imports, and factual CoVe report checks. |
| `[MODIFY]` | `tools/orchestration/plan_review_auditor.py` (AST: audit_plan_and_solo_execution) | Parse class methods, `(file, symbol)` keys, return types, and milestone-scoped Section 2 contracts. Support polyglot & boolean `and`/grouped `-k` in Section 4. Enforce missing mutation receipt, missing `decisions.tsv`, `CERTIFIED_RED` status, non-empty `test_tree_hash`, and HMAC checks under `--strict-solo`. Parse multi-line `def` signatures & `pkg/__init__.py` cycles in Layer 5. |
| `[MODIFY]` | `tests/test_review_plan_solo_reconciliation.py` (AST: test_positive_clean_solo_matches_super_plan) | Add 4-scenario tests for missing mutation/`decisions.tsv` under `--strict-solo`, `assert True` matrix rejection, multi-line `def` broken callers, class method drift, `AST_CONTRACT_VERIFIED` bypass guard, and `__init__.py` cycles. |
| `[MODIFY]` | `tools/orchestration/plan_dag_bridge.py` (AST: execute_plan_via_solo) | Aggregate multi-file milestone mutation results into one `M*_mutation.json` receipt without overwriting earlier targets, and sign receipt HMAC. |
| `[MODIFY]` | `tools/orchestration/solo_runner.py` (AST: certify_mutation_phase) | Sign mutation receipts with HMAC, fix `certify_purple_phase` `"title"` severity lookup, and forward `implementation_plan.md` when present in standalone `--purple` auto-review. |
| `[MODIFY]` | `tests/test_plan_dag_solo_bridge.py` (AST: test_v21_multifile_milestone_mutation_aggregation_and_hmac) | Add regression coverage verifying multi-file milestone mutation receipt aggregation and HMAC signing in `execute_plan_via_solo`. |
| `[MODIFY]` | `.agent/skills/review/SKILL.md` (AST: module_root) | Update 7-layer protocol specification, true-tautology & signed mutation provenance rules, factual `--verify-cove`, and strict read-only side-effect guarantees. |
| `[CREATE]` | `docs/adr/ADR-0027-review-v21-closed-loop-hardening.md` (New) | Record architectural decisions, backward-compatibility guarantees, and acyclic layering invariants for `/review` v2.1. |

### Blast Radius & Downstream Dependencies
- **Direct Callers:** `tools/orchestration/solo_runner.py`, `tools/orchestration/plan_dag_bridge.py`, `tools/core/cli.py`, `tests/test_solo_runner.py`, `tests/test_plan_dag_solo_bridge.py`.
- **Downstream Tests:** `tests/test_senior_code_review.py`, `tests/test_review_plan_solo_reconciliation.py`, `tests/test_solo_runner.py`, `tests/test_plan_dag_solo_bridge.py`.
- **Regression Risk:** Low-Medium (All public function signatures retain default values for existing callers, keeping 100% backward compatibility with `TestSeniorCodeReview` and `test_solo_runner.py`).

---

## 2. Data Flow & Interface Signatures

> **Anti-Full-Code Invariant:** Define ONLY DTOs, schemas, and function signatures with type contracts. Full implementation body is deferred to the `/solo` execution phase.

```python
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class UntrackedFileDiffDTO:
    """Synthesized unified diff metadata for an untracked workspace file."""

    rel_path: str
    line_count: int
    is_binary: bool
    truncated: bool


@dataclass(frozen=True)
class ReportClaimVerificationDTO:
    """Factual claim-vs-disk verification summary for exported Markdown review reports."""

    status: str
    factual_confidence_pct: float
    total_claims_checked: int
    verified_claims: int
    discrepancies: Tuple[str, ...]


@dataclass(frozen=True)
class AggregatedMutationReceiptDTO:
    """Milestone-level mutation receipt aggregating multiple target source files."""

    milestone_id: str
    status: str
    passed: bool
    mutation_score: float
    required_threshold: float
    targets_evaluated: Tuple[str, ...]
    total_generated: int
    killed: int
    survived: int
    receipt_hmac: str


def compute_mutation_receipt_hmac(
    payload: Dict[str, object],
    key: Optional[bytes] = None,
    repo_root: Optional[str] = None,
) -> str:
    ...


def verify_mutation_receipt_hmac(
    payload: Dict[str, object],
    key: Optional[bytes] = None,
    repo_root: Optional[str] = None,
) -> bool:
    ...


def get_receipt_hmac_key_readonly(repo_root: Optional[str] = None) -> Optional[bytes]:
    ...


def verify_review_markdown_claims(
    report_path: str,
    repo_dir: str,
    expected_payload: Optional[Dict[str, object]] = None,
) -> ReportClaimVerificationDTO:
    ...


def build_untracked_file_diff(repo_dir: str, max_bytes: int = 262144) -> str:
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Leaf Forensic & Diff Sentinel Contracts
- **Node ID:** `M1` | **depends_on:** `[]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 2):** `tools/orchestration/solo_contracts.py`, `tools/lint/output_diff_sentinel.py`
- **Write Set:** `['tools/orchestration/solo_contracts.py', 'tools/lint/output_diff_sentinel.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[]`
  - **produces:** `[{"contract": "SoloContractsV21", "fields": {"compute_mutation_receipt_hmac": "callable", "verify_mutation_receipt_hmac": "callable", "get_receipt_hmac_key_readonly": "callable"}}]`
  - **invariants:** `["backward_compatible(AstTautologyAnalyzer)", "constant_time_hmac_compare", "zero_disk_key_write_on_readonly"]`
- **Goal:** Extend `AstTautologyAnalyzer` with `flag_true_tautologies: bool = False`, add mutation receipt HMAC signing/verification helpers plus `get_receipt_hmac_key_readonly`, and parameterize `OutputDiffSentinel.audit_git_diff` with `target: str = "uncommitted"`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside M1 write set are touched
- **Rollback Hook:** `git checkout -- tools/orchestration/solo_contracts.py tools/lint/output_diff_sentinel.py`
- **Pass Gate:** `python3 -m pytest tests/test_solo_runner.py -k "tautolog or hmac" -q`

### Milestone 2: Core `/review` Diff, AST Simplify & Factual CoVe Hardening
- **Node ID:** `M2` | **depends_on:** `[M1]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 2):** `tools/orchestration/senior_code_review.py`, `tests/test_senior_code_review.py`
- **Write Set:** `['tools/orchestration/senior_code_review.py', 'tests/test_senior_code_review.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "SoloContractsV21"}]`
  - **produces:** `[{"contract": "UntrackedFileDiffDTO", "fields": {"rel_path": "str", "is_binary": "bool"}}, {"contract": "ReportClaimVerificationDTO", "fields": {"factual_confidence_pct": "float", "status": "str"}}]`
  - **invariants:** `["untracked_files_scanned_in_uncommitted", "no_newline_marker_preserves_line_numbers", "verify_cove_checks_claims_against_disk"]`
- **Goal:** Include untracked files in `get_git_diff`, fix `parse_diff` line tracking and quoted paths, run function-level AST checks when body lines change, enable `AstTautologyAnalyzer(flag_true_tautologies=True)`, add unused import/variable AST `simplify` findings, guard `.md` dead-code regex, pass `target` to `OutputDiffSentinel`, implement `verify_review_markdown_claims`, and update `tests/test_senior_code_review.py`.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside M2 write set are touched
- **Rollback Hook:** `git checkout -- tools/orchestration/senior_code_review.py tests/test_senior_code_review.py`
- **Pass Gate:** `python3 -m pytest tests/test_senior_code_review.py -q`

### Milestone 3: Zero-Trust Plan Reconciliation & Strict Solo Provenance
- **Node ID:** `M3` | **depends_on:** `[M1, M2]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 2):** `tools/orchestration/plan_review_auditor.py`, `tests/test_review_plan_solo_reconciliation.py`
- **Write Set:** `['tools/orchestration/plan_review_auditor.py', 'tests/test_review_plan_solo_reconciliation.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "SoloContractsV21"}, {"contract": "ReportClaimVerificationDTO"}]`
  - **produces:** `[{"contract": "PlanReconciliationV21", "fields": {"passed": "bool", "alignment_score_pct": "float"}}]`
  - **invariants:** `["acyclic_no_solo_runner_import", "strict_solo_requires_mutation_and_decisions", "multiline_def_and_init_cycles_detected"]`
- **Goal:** Upgrade Layer 2 (class methods, `(file, symbol)` keys, return types, milestone-scoped Section 2), Layer 3 (polyglot test paths, boolean `and`/grouped `-k`, true-tautology checks), Layer 4 (`--strict-solo` missing mutation receipt & missing `decisions.tsv` blockers, `CERTIFIED_RED` status & `test_tree_hash` checks, mutation HMAC check, bounded `AST_CONTRACT_VERIFIED`), and Layer 5 (multi-line `def` AST diffing, `pkg/__init__.py` cycle resolution, receiver-aware caller checks, truncation warning), plus 4-scenario tests.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if `solo_runner` imported or out-of-scope files modified
- **Rollback Hook:** `git checkout -- tools/orchestration/plan_review_auditor.py tests/test_review_plan_solo_reconciliation.py`
- **Pass Gate:** `python3 -m pytest tests/test_review_plan_solo_reconciliation.py -q`

### Milestone 4: `/solo` Bridge Receipt Aggregation & Mutation Signing
- **Node ID:** `M4` | **depends_on:** `[M1, M3]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High | Best-of-3]`
- **Files Modified (Max 3):** `tools/orchestration/plan_dag_bridge.py`, `tools/orchestration/solo_runner.py`, `tests/test_plan_dag_solo_bridge.py`
- **Write Set:** `['tools/orchestration/plan_dag_bridge.py', 'tools/orchestration/solo_runner.py', 'tests/test_plan_dag_solo_bridge.py']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "SoloContractsV21"}, {"contract": "PlanReconciliationV21"}]`
  - **produces:** `[{"contract": "AggregatedMutationReceiptDTO", "fields": {"milestone_id": "str", "receipt_hmac": "str"}}]`
  - **invariants:** `["multi_file_mutation_receipt_never_overwrites", "mutation_receipt_hmac_signed"]`
- **Goal:** Aggregate multi-file milestone mutation results into `AggregatedMutationReceiptDTO` in `plan_dag_bridge.py`, emit HMAC-signed mutation receipts in `solo_runner.py`, fix `certify_purple_phase` `"title"` finding lookup, and forward `implementation_plan.md` in standalone `--purple` auto-review when present.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside M4 write set are touched
- **Rollback Hook:** `git checkout -- tools/orchestration/plan_dag_bridge.py tools/orchestration/solo_runner.py`
- **Pass Gate:** `python3 -m pytest tests/test_plan_dag_solo_bridge.py tests/test_solo_runner.py -q`

### Milestone 5: Skill Spec Alignment & ADR-0027 Publication
- **Node ID:** `M5` | **depends_on:** `[M2, M3, M4]`
- **Compute Tier:** `[Model: Flash | Thinking: Off | Temp: 0.1]`
- **Files Modified (Max 2):** `.agent/skills/review/SKILL.md`, `docs/adr/ADR-0027-review-v21-closed-loop-hardening.md`
- **Write Set:** `['.agent/skills/review/SKILL.md', 'docs/adr/ADR-0027-review-v21-closed-loop-hardening.md']`
- **Typed Interface Manifest:**
  - **consumes:** `[{"contract": "AggregatedMutationReceiptDTO"}]`
  - **produces:** `[{"contract": "ReviewV21Documentation", "fields": {"verified": "bool"}}]`
  - **invariants:** `["english_only_rules", "humanize_clean", "zero_cli_schema_drift"]`
- **Goal:** Update `.agent/skills/review/SKILL.md` for v2.1 closed-loop checks and document `ADR-0027-review-v21-closed-loop-hardening.md`, then verify end-to-end tests and hub gates.
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: Halt if files outside M5 write set are touched
- **Rollback Hook:** `rm -f docs/adr/ADR-0027-review-v21-closed-loop-hardening.md && git checkout -- .agent/skills/review/SKILL.md`
- **Pass Gate:** `python3 -m pytest tests/test_senior_code_review.py tests/test_review_plan_solo_reconciliation.py tests/test_plan_dag_solo_bridge.py -q`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Untracked `[CREATE]` file & `assert True` detection | New untracked source fixture with hardcoded secret and temporary test fixture with `assert True` | `evaluate_review(target="uncommitted")` flags secret, tautology, and unplanned scope creep (`Must fix`, exit `1`) | `python3 -m pytest tests/test_senior_code_review.py -k "untracked or true_tautology" -q` |
| **TC-02** | Edited-body nesting & `\ No newline` line accuracy | Modified body inside existing `def` with 5 nesting levels + diff lacking trailing newline | AST flags deep nesting at exact shifted-free `file:line` (`Should fix`) | `python3 -m pytest tests/test_senior_code_review.py -k "nesting or no_newline" -q` |
| **TC-03** | Staged/branch `OutputDiffSentinel` & factual `--verify-cove` | Staged rewrite violation + exported `review.md` citing finding with `time.sleep` | `OutputDiffSentinel` checks staged diff, and `--verify-cove` reports `PASS` (`100.0%`) when claims match disk truth | `python3 -m pytest tests/test_senior_code_review.py -k "cove or staged_bloat" -q` |
| **TC-04** | `--strict-solo` missing mutation / `decisions.tsv` / unsigned tamper | Repo with valid `M1_red.json` but missing `M1_mutation.json` or missing `decisions.tsv` | `_audit_solo_provenance` fails with `MISSING_MUTATION_RECEIPT` / `MISSING_DECISION_LOG` (`CHANGES_REQUESTED`, exit `1`) | `python3 -m pytest tests/test_review_plan_solo_reconciliation.py -k "strict_solo" -q` |
| **TC-05** | Multi-line `def` caller break, method drift & `pkg/__init__.py` cycle | Removed parameter in multi-line `def` + method return drift + cycle via `pkg/__init__.py` | `BROKEN_DOWNSTREAM_CALLER`, `CONTRACT_SIGNATURE_DRIFT`, `CIRCULAR_IMPORT_DETECTED` raised | `python3 -m pytest tests/test_review_plan_solo_reconciliation.py -k "multiline or method or init_cycle" -q` |
| **TC-06** | Section 4 boolean `-k` & polyglot matrix verification | Matrix row with `-k "test_a and test_b"` where `test_b` is missing, plus `.spec.ts` row | Missing `test_b` flagged as `UNVERIFIED_MATRIX_SCENARIOS` (`Must fix`) | `python3 -m pytest tests/test_review_plan_solo_reconciliation.py -k "matrix" -q` |
| **TC-07** | Multi-file milestone mutation aggregation & HMAC receipt | Plan milestone with 2 source files run via `execute_plan_via_solo` | Single `M1_mutation.json` preserves both targets and valid `receipt_hmac` | `python3 -m pytest tests/test_plan_dag_solo_bridge.py tests/test_solo_runner.py -k "mutation" -q` |
| **TC-08** | Hub schema, acyclicity & impact verification | Post-edit verification across all touched modules and docs | `cli_schema_sentinel`, `verify_all --tier impact`, and review suites pass 100% | `python3 tools/core/verify_all.py --mode hub --tier impact` |

---

## 5. Tri-Vulnerability Self-Critique & Execution Handoff

### Tri-Vulnerability Mitigation Analysis
- **Concurrency & Race Conditions (`race_condition`):** Signing mutation receipts (`compute_mutation_receipt_hmac`) and writing `M*_mutation.json` in `plan_dag_bridge.py` must use `_write_json_atomic` (`tempfile.mkstemp` + `os.replace`) so parallel test shards or external readers never observe partial JSON. Read-only `/review` key lookup (`get_receipt_hmac_key_readonly`) avoids racing with `.git/synapse_receipt_hmac.key` creation.
- **Boundary & Resource Exhaustion (`boundary_resource`):** `build_untracked_file_diff` must skip `.git/`, `.cache/`, `node_modules/`, binary files (`\x00` check), and truncate files exceeding `262144` bytes so large untracked artifacts never cause OOM or timeout during `uncommitted` review. Layer 5 caller scanning keeps the `MAX_CALLER_FILES = 50` cap and emits an explicit truncation note instead of failing silently.
- **Backward Compatibility & Blast Radius (`backward_compat`):** All existing public signatures (`AstTautologyAnalyzer`, `OutputDiffSentinel.audit_git_diff`, `run_review`, `evaluate_review`, `audit_plan_and_solo_execution`) preserve default arguments and return schemas. `AstTautologyAnalyzer` defaults `flag_true_tautologies=False` so `--red` anti-cheat behavior in `solo_runner.py` stays intact, and unsigned legacy mutation receipts fail only under explicit `--strict-solo` or when `receipt_hmac` is present and invalid.

### Execution Handoff
- **Recommended Execution Model & Thinking Level:** `Gemini 4 Neon (High)` (or `Gemini 4 Hydrogen (High)` with sequential single-agent discipline) for one continuous `/solo` session executing `M1 -> M2 -> M3 -> M4 -> M5`.
- **Clean Context Handoff:**
  ```bash
  # Interactive single-agent handoff:
  # "Read implementation_plan.md and execute sequentially via /solo (single-agent mode, no swarm workers)"
  # Mechanical closed-loop verification runner:
  agent-qa solo --from-plan implementation_plan.md --json
  ```
