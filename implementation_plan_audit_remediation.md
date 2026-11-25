<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# Implementation Plan: Audit Remediation — Hermetic Skill Isolation & KV-Cache Telemetry Sentinel

> **Super-Plan Metadata:** `Tier 1 (STANDARD)` | `RiskScore = 0.473` (`fan_in = 2`, `blast_radius = 7`, `critical_path = True`, `state_mutation = True`)
> **Execution Mode:** Sequential Single-Agent `/solo` (`M1` -> `M2` -> `M3`, strictly `0` `swarm` workers or parallel subagents)
> **Governing Rulings (Locked at Stage 2 Ambiguity Gate):**
> - `Ruling 1 (AS3 Hermetic Skill Isolation):` Preserve `tools/core/skillspector.py` rule `AS3` (`PATTERNS_AS`) without regex relaxation per Invariant 11 (Monotonic Quality Ratchet). Reword `skills/08-code-quality/surgical-coding-principles/SKILL.md` (`L57`) to reference the `/solo` verification workflow conceptually without a literal peer `SKILL.md` file path, then synchronize `skillFolderHash` in `skills-lock.json` via `tools/core/skill_canonical_digest.py::update_skills_lockfile`.
> - `Ruling 2 (KV-Cache --check-latest & Transcript Denominator Contract):` Wire `--check-latest` (with optional `--strict` flag) in `tools/core/kv_cache_sentinel.py::main` to audit the latest entry in `.synapse/telemetry/kv_cache_history.json` (`exit 0` if `cache_hit_rate_pct >= min_required_pct`, `exit 1` on SLA breach `< 85.0%`), and return structured `NO_TELEMETRY_RECORDED` (`exit 0` by default, `exit 1` under `--strict`) when history is absent or empty. Normalize `audit_transcript_file` so uncached step `input_tokens` and `cache_read_tokens` sum into total prompt input tokens (`in_tok + cached_tok`), eliminating `> 100%` hit-rate inflation while keeping `evaluate_cache_hit_rate` 100% backward compatible.
> - `Ruling 3 (Plan Artifact Scope Isolation):` Export this remediation plan exclusively to `implementation_plan_audit_remediation.md` and leave legacy `implementation_plan.md` untouched per Invariant 6 (Out-of-Scope Isolation).

---

## 1. Affected Files & Blast Radius

| Action | Target File & AST Structural Anchor | Line Range | Change Purpose & Blast Radius |
| :---: | :--- | :---: | :--- |
| `[MODIFY]` | `skills/08-code-quality/surgical-coding-principles/SKILL.md` (L54-L61) | `L54-L61` | Replace literal peer skill file reference (`skills/solo/SKILL.md`) in Principle 1 with hermetic conceptual `/solo` workflow wording so `skillspector.py --scan-skills` drops from `risk_score = 20` (`AS3`) to `0`. |
| `[MODIFY]` | `skills-lock.json` (L411-L419) | `L411-L419` | Recalculate deterministic SHA-256 `skillFolderHash` for `surgical-coding-principles` via `skill_canonical_digest.py::update_skills_lockfile` to maintain 100% lockfile integrity across `test_skill_hash_lock.py` and `check_version_sync.py`. |
| `[MODIFY]` | `tools/core/kv_cache_sentinel.py` (AST: audit_transcript_file) | `L140-L254` | Implement `check_latest_telemetry` for `--check-latest` (supporting `--json` and `--strict`), handle missing/empty/corrupt `.synapse/telemetry/kv_cache_history.json` safely, and compute `total_input_tokens = in_tok + cached_tok` in `audit_transcript_file` when `cache_read_tokens` is disjoint from uncached `input_tokens`. |
| `[CREATE]` | `tests/test_audit_skills_and_kv_sentinel.py` (New) | `L1-L180` | Dedicated 4-scenario unit & CLI regression suite covering Positive, Negative, Boundary, and CLI flags (`--check-latest`, `--json`, `--strict`, `--transcript`) plus SkillSpector `0/100` risk and `skills-lock.json` SHA-256 parity. |

- **Blast Radius & Downstream Callers Verified:**
  - `tools/core/sync_agent_rules.py` (`L632`) imports `evaluate_cache_hit_rate` and `load_telemetry_config` from `tools/core/kv_cache_sentinel.py` — both function signatures and return semantics remain unchanged (`0` breaking changes).
  - `tests/test_architectural_hardening.py::test_tc12_kv_cache_sentinel_telemetry_evaluation` calls `evaluate_cache_hit_rate(input_tokens=4000, cached_tokens=3600, min_pct=85.0)` — preserved 100%.
  - `tests/test_skill_hash_lock.py` and `tools/core/check_version_sync.py` validate `skills-lock.json` without creating `.skill-lock.json` (enforced by `invariant_checker.py` Rule 7).

---

## 2. Data Flow & Interface Signatures

```python
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AuditRemediationScopeDTO:
    """Root input contract locking Stage 2 rulings for sequential /solo execution."""
    repo_root: str
    min_kv_cache_hit_rate_pct: float
    preserve_skillspector_as3_sensor: bool


@dataclass(frozen=True)
class SkillIsolationReceiptDTO:
    """Verification contract emitted after remediating AS3 and syncing skills-lock.json."""
    skill_id: str
    updated_folder_hash: str
    skillspector_risk_score: int
    lockfile_verified: bool


@dataclass(frozen=True)
class LatestKVCacheVerdictDTO:
    """Structured telemetry audit outcome returned by kv_cache_sentinel --check-latest."""
    status: str  # "EVALUATED" | "NO_TELEMETRY_RECORDED" | "CORRUPT_TELEMETRY_HISTORY"
    timestamp: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    input_tokens: Optional[int]
    cached_tokens: Optional[int]
    cache_hit_rate_pct: Optional[float]
    min_required_pct: float
    passed: bool
    alert_triggered: bool
    details: str


@dataclass(frozen=True)
class RemediationVerificationReceiptDTO:
    """End-to-end Solo Red-Green-Purple and mutation verification receipt."""
    tests_passed: int
    mutation_score_pct: float
    dod_impact_passed: bool


# Key Function Signatures (Anti-Full-Code — Signatures Only)
def check_latest_telemetry(
    repo_root: str,
    strict: bool = False,
) -> LatestKVCacheVerdictDTO:
    """Reads latest record from .synapse/telemetry/kv_cache_history.json and evaluates SLA compliance."""
    ...


def audit_transcript_file(
    transcript_path: str,
    repo_root: str,
) -> List[Any]:
    """Audits Antigravity transcript JSONL steps using total_input_tokens = uncached_input + cache_read_tokens."""
    ...
```

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Remediate AS3 Skill Prose & Synchronize Canonical Skill Lockfile
- **Node ID:** M1-HERMETIC-SKILL-ISOLATION
- **depends_on:** []
- **Compute Tier:** [Model: Flash | Thinking: Off | Temp: 0.1]
- **Files Modified:** `skills/08-code-quality/surgical-coding-principles/SKILL.md`, `skills-lock.json`
- **Write Set:** ['skills/08-code-quality/surgical-coding-principles/SKILL.md', 'skills-lock.json']
- **consumes:** [{'contract': 'AuditRemediationScopeDTO'}]
- **produces:** [{'contract': 'SkillIsolationReceiptDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 2 files
- **Rollback Hook:** git restore skills/08-code-quality/surgical-coding-principles/SKILL.md skills-lock.json

### Milestone 2: Wire KV-Cache Sentinel --check-latest Contract & Transcript Token Denominator
- **Node ID:** M2-KV-SENTINEL-CHECK-LATEST
- **depends_on:** ['M1-HERMETIC-SKILL-ISOLATION']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `tools/core/kv_cache_sentinel.py`
- **Write Set:** ['tools/core/kv_cache_sentinel.py']
- **consumes:** [{'contract': 'SkillIsolationReceiptDTO'}]
- **produces:** [{'contract': 'LatestKVCacheVerdictDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 1 file
- **Rollback Hook:** git restore tools/core/kv_cache_sentinel.py

### Milestone 3: Author 4-Scenario Solo Regression Suite & Execute Mutation + DoD Gates
- **Node ID:** M3-SOLO-REGRESSION-AND-GATES
- **depends_on:** ['M2-KV-SENTINEL-CHECK-LATEST']
- **Compute Tier:** [Model: Pro | Thinking: High | Temp: 0.1]
- **Files Modified:** `tests/test_audit_skills_and_kv_sentinel.py`
- **Write Set:** ['tests/test_audit_skills_and_kv_sentinel.py']
- **consumes:** [{'contract': 'LatestKVCacheVerdictDTO'}]
- **produces:** [{'contract': 'RemediationVerificationReceiptDTO'}]
- **Circuit Breaker:** Max Fix Attempts: 2 | Scope Guard: <= 1 file
- **Rollback Hook:** rm -f tests/test_audit_skills_and_kv_sentinel.py

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| ID | Milestone | Scenario & Precondition | Expected Deterministic Outcome | Verification Command |
| :---: | :---: | :--- | :--- | :--- |
| **V-01** | `M1` | **Positive Skill Security & Lockfile Parity:** Reword `surgical-coding-principles/SKILL.md` (`L57`), sync `skills-lock.json`, and scan all 57 skills | `skillspector.py` reports `risk_score == 0`, `total_findings == 0`, `severity == "LOW"`; `validate_skills_schema.py`, `lint_ai_docs.py`, and `test_skill_hash_lock.py` exit `0` | `python3 tools/core/skillspector.py --scan-skills --strict --format json && pytest tests/test_skill_hash_lock.py` |
| **V-02** | `M2`–`M3` | **Positive KV-Cache Latest & Transcript Audit:** Seed temp `kv_cache_history.json` with `input_tokens=10000, cached_tokens=9000` (`90.0%`) and temp `transcript.jsonl` with `input_tokens=2514, cache_read_tokens=54206` | `--check-latest --json` exits `0` with `status == "EVALUATED"`, `cache_hit_rate_pct == 90.0`, `passed == True`; `--transcript --json` computes `54206 / (2514 + 54206) == 95.57%` (`<= 100.0%`) | `pytest tests/test_audit_skills_and_kv_sentinel.py -k "positive"` |
| **V-03** | `M2`–`M3` | **Negative SLA Breach & Corrupt History Resilience:** Seed `kv_cache_history.json` with `75.0%` (`< 85.0%`) and test malformed JSON / negative token counts | `75.0%` record exits `1` with `alert_triggered == True` and `passed == False`; malformed JSON returns `status == "CORRUPT_TELEMETRY_HISTORY"` (`exit 1`) without unhandled traceback | `pytest tests/test_audit_skills_and_kv_sentinel.py -k "negative"` |
| **V-04** | `M2`–`M3` | **Boundary Empty/Missing History & Zero-Input Steps:** Run `--check-latest --json` (with and without `--strict`) on an empty temp repo root; audit transcript containing `input_tokens=0, cache_read_tokens=5000` and empty lines | Missing/empty history returns `status == "NO_TELEMETRY_RECORDED"` (`exit 0` default, `exit 1` with `--strict`); `0` uncached + `5000` cached step yields `100.0%` without `ZeroDivisionError` | `pytest tests/test_audit_skills_and_kv_sentinel.py -k "boundary"` |
| **V-05** | `M3` | **CLI Flags, Mutation Sentinel (`>= 80%`) & Hub Impact DoD:** Run `micro_mutator.py` on `tools/core/kv_cache_sentinel.py`, `cli_schema_sentinel.py`, `infer_linter.py`, and `verify_all.py --mode hub --tier impact` | AST mutation score `>= 80.0%` on `kv_cache_sentinel.py`; `test_architectural_hardening.py` and `verify_all.py --mode hub --tier impact` pass `100%` | `python3 tools/lint/micro_mutator.py tools/core/kv_cache_sentinel.py --tests tests/test_audit_skills_and_kv_sentinel.py --threshold 80.0 && python3 tools/core/verify_all.py --mode hub --tier impact` |

---

## 5. Tri-Vulnerability Self-Critique & Red-Teaming

1. **Race Condition & Concurrency Safety:**
   - Executing sequentially under Single-Agent `/solo` (`M1 -> M2 -> M3`) enforces disjoint, ordered file updates with zero concurrent write-set contention.
   - `check_latest_telemetry` performs strictly read-only inspection of `.synapse/telemetry/kv_cache_history.json` (unlike `--record`, it never mutates or truncates history files), making concurrent CI/test invocations completely idempotent and race-free. All tests in `tests/test_audit_skills_and_kv_sentinel.py` isolate filesystem state inside `tempfile.TemporaryDirectory()` via `--repo-root` so live `.synapse/telemetry/` state is never mutated during parallel `pytest` runs.
2. **Boundary & Extreme Resource Resilience:**
   - Missing `.synapse/telemetry/kv_cache_history.json`, empty `[]` JSON arrays, non-list JSON objects, or truncated JSON payloads are handled deterministically without `FileNotFoundError`, `IndexError`, `KeyError`, or `JSONDecodeError` crashes.
   - In `audit_transcript_file`, steps where `input_tokens == 0` and `cache_read_tokens > 0` evaluate cleanly (`total_in_tok = cached_tok -> 100.0%`), while steps with `input_tokens <= 0` and `cache_read_tokens <= 0` are skipped safely without `ZeroDivisionError`; streaming line-by-line iteration bounds memory usage to `O(1)` per line even on multi-megabyte `transcript.jsonl` logs.
3. **Backward Compatibility & Caller Blast Radius:**
   - `evaluate_cache_hit_rate` and `load_telemetry_config` preserve their exact parameter lists, default values, and `KVCacheAuditDTO` fields so downstream callers (`tools/core/sync_agent_rules.py`, `tests/test_architectural_hardening.py`) experience zero breaking changes.
   - `skill_canonical_digest.py::update_skills_lockfile` updates only canonical `skills-lock.json` (never creating forbidden `.skill-lock.json`), preserving full compatibility with `invariant_checker.py` Rule 7, `check_version_sync.py`, and `skills_manifest.json`.

---

## Recommended Execution Model & Thinking Level

- **Primary Executor Model & Thinking Level (Single-Session Default):** `Gemini 4 Hydrogen (High)` (or `Gemini 4 Neon (Medium)` for single-session sequential `/solo` execution across `M1 -> M2 -> M3`, including Red-Green-Purple TDD and `>= 80.0%` AST mutation verification).
- **Milestone Escalation Overrides (Optional / `/teamwork` Only):** Under default `/solo`, all 3 milestones execute sequentially in one session on the Primary Executor (`0` `swarm` workers spawned). If manually adjusting per milestone, `M1` is safe on `Hydrogen (Medium)`, while `M2` and `M3` benefit from `Hydrogen (High)` to guarantee `>= 80%` mutant kill coverage across CLI edge cases.
- **Rationale:** The blast radius is tightly bounded to 4 files (`RiskScore = 0.473`, `Tier 1`), so stepping down from `Gemini 4 Carbon (High)` to `Gemini 4 Hydrogen (High)` cuts token cost substantially while retaining full reasoning rigor for `--check-latest` boundary handling and `micro_mutator.py` verification.
