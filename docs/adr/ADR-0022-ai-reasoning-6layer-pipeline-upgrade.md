<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0022: 6-Layer AI Reasoning & Verification Pipeline Upgrade

- **Status:** Accepted
- **Date:** 2026-11-25
- **Deciders:** Thế Vị (@TeeVee98), Enterprise QA Architecture Review
- **Plan Reference:** `implementation_plan_ai_reasoning_upgrade.md`

## 1. Context & Problem Statement

A 6-layer self-verification audit across Synapse Hub's deterministic reasoning and AI quality engines (`fan_in = 23` across `super_plan_engine.py`, `solo_runner.py`, `senior_code_review.py`, `self_evolving_loop.py`, and 9 test suites) uncovered six alignment and sensor-precision gaps:
1. **Step-Back Domain Blindness & Wait Drift:** `tools/reasoning/step_back_engine.py` lacked an architecture/verification abstraction category (`HARNESS_VERIFICATION_ARCHITECTURE`) and still emitted unconditional `network idle` wait guidance conflicting with `AGENTS.md` Rule 1.3.
2. **Self-Discover Retry Cap Skew:** `tools/reasoning/self_discover_engine.py` omitted architecture/verification selection boosters and emitted `K <= 3` retry limits instead of `K <= 2` (`AGENTS.md` Rule 1.13).
3. **Un-grounded Semantic Entropy & Brand Noise:** `tools/reasoning/semantic_entropy.py` defaulted unmatched repository queries to high-entropy divergent fallbacks (`SE = 1.0`) without checking physical repository files/symbols, and included `Synapse`/`Hub` brand tokens in epistemic search targets.
4. **Identical Multi-Round Debate Fallbacks:** `tools/reasoning/prover_verifier_games.py` emitted identical fallback stress text across rounds `1..5` when evaluating governance specifications such as `AGENTS.md`.
5. **CoVe Substring False Positives & Single-Class Blind Spot:** `tools/ai/cove_verifier.py` matched substring tokens (`post`, `add`, `timeout`), inspected only `classes[0]` in `INHERITANCE_INVARIANT`, and lacked a blind `EXCEPTION_HYGIENE` AST check.
6. **TextGrad Dead `--metric` Flag & EvalRunner Exception/Clock Hygiene:** `tools/ai/textgrad_optimizer.py` ignored CLI `--metric`, penalized `# synapse-ignore` markers, and risked injecting `raise RuntimeError` into `except ImportError` bootstrap blocks; `tools/core/eval_runner.py` retained bare `except ...: pass` blocks and wall-clock `time.time()` duration measurement.

## 2. Considered Options & Rulings

Selected **Branch B: Clean Architecture** (backward-compatible default-preserving contracts across all 7 engines) over Branch A (minimalist `eval_runner.py`-only patch) and Branch C (async daemon indexing):

1. **Ruling 1 — EvalRunner & TextGrad Dual Hardening:**
   - Removed bare `pass` blocks and `# synapse-ignore` markers in `tools/core/eval_runner.py`, narrowed UTF-8 stdio reconfiguration to `(AttributeError, OSError, ValueError)` with explicit `logger.debug` telemetry, switched `duration_sec` to `time.monotonic()`, and added `resilience_metadata` (`clock_source`, `subprocess_timeout_sec`).
   - Wired `--metric` (`all | clean-pom | resilience`) into `TextGradOptimizer` and `evaluate_loss()`, respected `# synapse-ignore` suppression markers without false fatal loss, fixed `isinstance(stmt, ast.Assign)` dummy suppression inspection, and preserved valid non-crashing Python syntax in `apply_textual_update()` for `except ImportError` bootstrap guards.
2. **Ruling 2 — Grounded Repo-AST Probe in Semantic Entropy:**
   - Added stdlib-only `_probe_repo_grounding()` in `SemanticEntropyEngine` bounded strictly to lightweight manifests (`tools/tools_schema.json`, `skills_index.json`, `AGENTS.md`) and `<= 5` targeted files (`< 64 KB` read cap, zero recursive repo walk), allowing grounded repository prompts to converge at `SE <= 0.50` while keeping ambiguous prompts locked at `SE > 0.50` and preserving all legacy prompt triggers.
   - Filtered `Synapse`/`Hub` brand noise from `_generate_epistemic_search_plan()` while preserving symbol extraction (`BasePage`, `EvalRunner`).
3. **Ruling 3 — Full 6-Layer Tier-2 Scope & Isolated Certification:**
   - Added `HARNESS_VERIFICATION_ARCHITECTURE` and bounded `waitForURL` / `waitForResponse` guardrails in `StepBackEngine`, added architecture/verification boosters and `K <= 2` alignment in `SelfDiscoverEngine`, rotated 5 distinct `ROUND_STRESS_VECTORS` across rounds `1..5` in `VerifierAgent.generate_attack()`, and upgraded `ChainOfVerificationEngine` with call/word-boundary regexes, multi-class `INHERITANCE_INVARIANT`, and `EXCEPTION_HYGIENE`.

## 3. Empirical Verification & Mutation Matrix

- **Regression Suites:** `tests/test_ai_reasoning_6layer_upgrade.py` (TC-01 through TC-06 across Positive, Negative, Boundary, and CLI Flags) plus all 9 existing reasoning/AI/EvalRunner test suites passed (`100%` pass rate, zero skipped/relaxed assertions).
- **EvalRunner Native Quality:** `tools/core/eval_runner.py` achieved `100.0%` (`PASS`) on `cove_verifier.py` and `10.0/10` (`loss == 0.0`) on `textgrad_optimizer.py --metric all`.
- **Diff-Scoped Dynamic Mutation Kill Scores (`solo_runner.py --mutation --threshold 80.0`):**
  - `tools/reasoning/step_back_engine.py`: `100.0%` (`4/4` killed)
  - `tools/reasoning/self_discover_engine.py`: `100.0%` (`7/7` killed)
  - `tools/reasoning/semantic_entropy.py`: `94.1%` (`16/17` killed)
  - `tools/reasoning/prover_verifier_games.py`: `100.0%` (`14/14` killed)
  - `tools/ai/cove_verifier.py`: `95.0%` (`19/20` killed)
  - `tools/ai/textgrad_optimizer.py`: `85.0%` (`17/20` killed)
  - `tools/core/eval_runner.py`: `80.0%` (`16/20` killed)

## 4. Consequences

- **Positive:** Every declared Guide invariant across all 6 AI reasoning/verification layers maps to a deterministic, AST-grounded Sensor without substring false positives, swallowed exceptions, or caller breakage (`fan_in = 23` preserved).
- **Trade-offs:** `_probe_repo_grounding()` intentionally bounds inspection to top-level manifests and standard `tools/*` directories (`<= 5` files, `< 64 KB`) to keep CLI latency sub-25ms; prompts referencing deeply nested non-standard paths require explicit `--hypotheses-file` input.
