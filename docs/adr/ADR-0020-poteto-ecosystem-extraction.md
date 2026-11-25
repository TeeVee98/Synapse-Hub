<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0020: Extraction & Integration of Lauren Tan (`@poteto`) Ecosystem Patterns

- **Status:** Accepted
- **Date:** 2026-11-25
- **Reference Clones:** `reference_repos/poteto/{brainmaxxing,noodle,how,verification-skill-example,cursor-plugins/pstack}`

## Context

Lauren Tan (`@poteto`, Grok Bot core team) published open-source agentic engineering workflows (`pstack`, `brainmaxxing`, `noodle`, `how`, `verification-skill-example`). Rather than importing entire external plugins that collide with Synapse Hub's 57 existing skills and 11 deterministic gates (`verify_all.py`), we audited each repository for net-new mechanisms.

## Decision

1. **Adopted (Extended Existing Skills & Stdlib Tools):**
   - `show-me-your-work` -> `tools/core/decision_log.py` + `persistent-planning-files` (append-only `decisions.tsv` with formula-injection escaping and audit).
   - `create-verification-skill` / `verify-atlas` -> `templates/verification/FEATURE_MAP_TEMPLATE.md` + `playwright-webapp-testing` (`Doctor` preflight, User-POV Feature Map, evidence-preserving `Cleanup`).
   - `benchmark-checklist` -> `web-vitals-and-performance-profiler` & `backend-load-and-stress-patterns` (7-question empirical vetting gate).
   - `brainmaxxing` -> `tools/core/brain_indexer.py` + `qa-memory-os` (Markdown vault `[[wikilinks]]` + `/reflect` structural-first routing & `/meditate` pruning).
   - `poteto/how` -> `senior-code-review` (5-section onboarding `Explain` mode & 4-tier Lead Verdict: `Act on / Consider / Noted / Dismissed`).
   - `in-your-own-words` & `arena` Context-Dump -> `surgical-coding-principles` (Pre-Execution 3-Line Contract) & `meta-prompt-crafter` (4-Part Context-Dump Kickoff Template + `sharpen` & `reframe` modes).
   - `pstack/blast-radius` -> `graphify-impact-analyzer` (Phase 5: One Safety Fact + 5-Level Empirical Proof Ladder beyond AST grep).
   - `pstack/correct` -> `systematic-debugging` (5-Level Repeat-Mistake Structural Elimination Ladder: Architecture -> Types -> Actionable Lint -> Behavior Test -> Docs Last).

2. **Skipped (Already Enforced in Synapse Hub):**
   - `poteto-mode` static-sleep ban, skill-first reading, and verification-before-completion are already mechanically enforced by `AGENTS.md` Invariants 3, 7, 14 and `tools/lint/infer_linter.py`.

## Consequences

- Zero skill ID collisions in `skills_index.json`.
- Two new Python stdlib utilities (`decision_log.py`, `brain_indexer.py`) covered by unit tests and `micro_mutator.py` (>= 80% mutation score).
- Follow-up hardening (v4.8.4+):
  - `decision_log.py` uses `FileLock` for concurrent appends, enforces non-empty core cells (`ts`, `phase`, `decision`, `result`), adds `--strict` audit checks for `why`/`evidence`, and establishes explicit boundary separation from `tools/core/decision_ledger.py` (`decisions.tsv` per-run scratch trail vs `docs/decisions.jsonl` repo-wide architectural ledger).
  - `brain_indexer.py` ignores fenced code blocks (` ``` ` / `~~~`), flags ambiguous basename `[[wikilinks]]`, uses `FileLock` on `index.md`, and adds `--strict` fail-closed exit status.
  - Both tools are exposed via unified CLI subcommands (`agent-qa brain-index`, `agent-qa decision-log`) in `tools/core/cli_specs.json` and `bin/agent-qa.js`.
