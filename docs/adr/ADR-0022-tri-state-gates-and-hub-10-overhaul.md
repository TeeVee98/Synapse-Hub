<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0022: Tri-State Quality Gates, Defense-in-Depth Shell Guard, and Single-Source Governance

- **Date:** 2026-11-25
- **Status:** Accepted
- **Scope:** Quality Gate Engine (`tools/core/verify_all.py`, Gates 8/9/10/11), Shell Security (`tools/lint/pre_bash_guard.py`), Rules & Manual QA (`AGENTS.md`, `testing/manual/manual_testing_rules.md`), Performance SLA (`synapse.config.json`), and 57-Skill Catalog Hygiene (`skills_index.json`, `validate_skills_schema.py`).

## Context
An empirical repository audit (`synapse_hub_audit.md`) uncovered truth-anchor gaps in automated verification and guardrails:
1. `--tier fast` skipped regression tests yet emitted `"100% DoD COMPLIANT"`, while Gate 10 synthesized `local://benchmark` JSON-serialization JTL files to pass HTTP SLA checks and returned `True` when `jtl_analyzer` failed to import.
2. Gate 8 static heuristics and Gate 11 research-simulation tiers reported `"PASS"` / `"VERIFIED"` labels indistinguishable from live runtime verification, and Gate 9 ran UI finish checks on a CLI/library repository.
3. Regex-only matching in `pre_bash_guard.py` missed 10/16 adversarial vectors (`rm -rf /*`, `rm -r -f /`, `bash -c`, `git push origin main --force`, `.env | curl`, `curl | sh`, `pip install`).
4. SLA thresholds diverged across config, rules, and skills; `testing/manual/` lacked an agent-neutral rule file; 40+ skills shared boilerplate Handoff lines; and `solo_runner.py` exceeded 3,900 lines.

## Decision
1. **Tri-State Quality Gates (`PASS`, `HEURISTIC_PASS`, `SKIPPED_NO_LOAD_ARTIFACT`, `SKIPPED_BY_CONFIG`, `FAIL`):**
   - Disabled `auto_benchmark_fallback` by default, excluded synthetic `local://benchmark` artifacts, added baseline P95 regression delta checking (`max_p95_regression_pct: 15.0`), and made `jtl_analyzer` import failures fail closed.
   - Fast-tier runs emit `[PARTIAL PASS - FAST TIER | Regression Suite Not Run]` (`verification_completeness = "PARTIAL_FAST_TIER"`) and never write cryptographic DoD receipts.
   - Separated Gate 11's 6 `RESEARCH_SIMULATION_TIERS` as `[INFO / SIMULATION]` while gating pass/fail on the 9 production-active tiers.
2. **Tokenized Shell Guard (`shlex` + Recursive Unwrapping):**
   - Replaced raw regexes with `shlex` tokenization, flag normalization, bounded recursive unwrapping of `bash -c`/`sh -c`/`eval`/`$(...)`, pipeline secret-exfiltration detection, position-independent `git push --force` blocking, and Python/JS package mutation guards.
3. **Single-Source Rules, Manual QA, 57-Skill Hygiene, and Modularity:**
   - Wired `sync_agent_rules.sync_all(check_only=True)` into Gate 4, created `testing/manual/manual_testing_rules.md` with QUICK-mode exit criteria (`check_quick_exit_criteria`), sorted and de-truncated `skills_index.json` while replacing 40 boilerplate Handoff lines with domain-specific formats enforced by `check_handoff_boilerplate_diversity`, and extracted `tools/orchestration/solo_contracts.py`.

## Consequences
- Quality gate outputs are empirically honest across CI, CLI, and JSON/JUnit exports.
- Existing 57-skill directory IDs and wheel packaging contracts remain 100% intact with zero broken links or trigger collisions.
- `solo_runner.py` re-exports all extracted contract symbols from `solo_contracts.py` for full backward compatibility.
