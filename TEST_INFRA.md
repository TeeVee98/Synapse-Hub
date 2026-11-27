<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
-->

# Synapse Hub: Autonomous Reasoning E2E Test Infrastructure (`TEST_INFRA.md`)

> **Author:** Thế Vị (@TeeVee98)  
> **Repository:** [Synapse-Hub](https://github.com/TeeVee98/Synapse-Hub)  
> **License:** MIT License  
> **Master Test Suites:** `tests/e2e/test_deep_reasoning_pipeline_e2e.py`, `tests/e2e/test_reference_enhancements_e2e.py`  
> **Scope:** Deep Autonomous Reasoning Techniques (R1–R5) & End-to-End System Integration

---

## 1. Executive Summary & Test Philosophy

The Autonomous Reasoning test infrastructure in Synapse Hub validates the five deep reasoning modules from an **opaque-box, contract-driven, and multi-tier** perspective. Rather than testing internal class mechanics in isolation, the E2E test harness treats each reasoning engine as an autonomous agent capability executed via standard CLI contracts and public Python entrypoints.

### Core Testing Invariants:
1. **Truth Anchor (Zero Fake Passes):** Every test exercises genuine execution logic with strict mathematical and structural assertions. Catch-and-swallow constructs (`except: pass`, dummy suppression) are strictly forbidden.
2. **100% UTF-8 No BOM:** Zero BOM bytes (`0xEF, 0xBB, 0xBF`) across all test code, fixtures, and telemetry.
3. **Dynamic Smart Waits Only:** Static sleeps (`time.sleep`, `Thread.sleep`) are strictly prohibited to prevent pipeline flakiness. All timing bounds are enforced via dynamic subprocess timeouts (`timeout=30.0`).
4. **Dynamic & Idempotent Test Isolation:** Every test run generates dynamic entity identifiers via `unique_code()` and confines all SQLite databases, input payloads, and generated artifacts to pytest's sandboxed `tmp_path` fixture.
5. **Progressive Testability (`require_tool`):** Tests utilize a progressive capability check (`require_tool`) that gracefully skips (`pytest.skip`) if an unmerged milestone tool is not yet present on disk, ensuring continuous non-breaking CI execution.

---

## 2. Quality Gates & DoD Compliance Matrix

The master E2E test suite adheres to all ten Synapse Hub Quality Gates (DoD):

| Gate # | DoD Requirement | Mechanism in E2E Test Suite | Verification Command |
|---|---|---|---|
| **Gate 01** | 100% UTF-8 No BOM | All files created with standard UTF-8 without BOM bytes | `python tools/core/verify_all.py --mode hub` |
| **Gate 02** | Invariant Integrity | Conforms to `docs/INVARIANTS.md` and repository architectural rules | `python tools/lint/invariant_checker.py --json` |
| **Gate 03** | CLI Schema Compliance | Validates argument schemas, help flags, and return codes | `python tools/lint/cli_schema_sentinel.py --check --json` |
| **Gate 04** | Author Attribution | MIT License & Thế Vị (@TeeVee98) copyright headers preserved | `python tools/core/author_integrity.py` |
| **Gate 05** | No Debug Crumbs | Zero console log residue, stray prints, or temporary trace files | `python tools/core/debug_crumbs.py --check --json` |
| **Gate 06** | Ratchet Sentinel | Rule ratchet invariant preserved; no relaxing of assertions | `python tools/lint/ratchet_sentinel.py --check` |
| **Gate 07** | Infer Linter | Zero fake passes, zero swallowed exceptions, zero static sleeps | `python tools/lint/infer_linter.py tests/e2e/test_deep_reasoning_pipeline_e2e.py` |
| **Gate 08** | Skills Schema Validation | Reasoning skills conform to schema index and docs standards | `python tools/lint/validate_skills_schema.py` |
| **Gate 09** | Test Suite Pass Rate | 100% test pass rate across E2E reasoning suites | `pytest tests/e2e/test_deep_reasoning_pipeline_e2e.py tests/e2e/test_reference_enhancements_e2e.py -v` |
| **Gate 10** | Impact Scope Tiering | Full test battery completes cleanly within fast dev-loop bounds | `python tools/core/verify_all.py --mode hub --tier impact` |

---

## 3. Four-Tier Architecture Specification

The E2E test suites `tests/e2e/test_deep_reasoning_pipeline_e2e.py` and `tests/e2e/test_reference_enhancements_e2e.py` validate deep reasoning pipelines and enhancements across four tiers:

```
+-------------------------------------------------------------------------------------------------------+
|                                    SYNAPSE HUB E2E TEST ARCHITECTURE                                  |
+-------------------------------------------------------------------------------------------------------+
|  Tier 1: Feature Coverage (27 Tests)                                                                 |
|    - R1: Unconstrained-to-Constrained Decoding (6 tests)                                             |
|    - R2: Prover-Verifier Games (6 tests)                                                             |
|    - R3: Semantic Entropy & Epistemic Search (5 tests)                                               |
|    - R4: Information-Theoretic Entropy Pruning (5 tests)                                             |
|    - R5: Associative Graph Memory & Sleep Consolidation (5 tests)                                     |
+-------------------------------------------------------------------------------------------------------+
|  Tier 2: Boundary & Corner Cases (27 Tests)                                                           |
|    - R1 Boundary & Adversarial Conditions (6 tests)                                                  |
|    - R2 Boundary & Adversarial Conditions (6 tests)                                                  |
|    - R3 Boundary & Adversarial Conditions (5 tests)                                                  |
|    - R4 Boundary & Adversarial Conditions (5 tests)                                                  |
|    - R5 Boundary & Adversarial Conditions (5 tests)                                                  |
+-------------------------------------------------------------------------------------------------------+
|  Tier 3: Cross-Feature Combinations (6 Tests)                                                         |
|    - T3.1: R1 -> R2 | Decoded JSON proposal fed to Prover-Verifier debate                            |
|    - T3.2: R4 -> R3 | Pruned code evaluated for semantic equivalence & entropy                      |
|    - T3.3: R2 -> R5 | Winning debate thesis stored & sleep consolidated in associative graph         |
|    - T3.4: R1 -> R4 | Pushdown projected patch compressed via entropy pruner                         |
|    - T3.5: R3 -> R5 | High semantic entropy triggers epistemic search querying associative memory   |
|    - T3.6: R4 -> R2 | Entropy-pruned log context supplied to Prover-Verifier debate                  |
+-------------------------------------------------------------------------------------------------------+
|  Tier 4: Real-World Autonomous Agent Workflows (5 Tests)                                              |
|    - T4.1: Autonomous Defect Triage -> Epistemic Search -> Patch Projection -> Memory Consolidation   |
|    - T4.2: CI Test Failure Autopsy with Log Pruning, Autopsy JSON Projection & Adversarial Debate     |
|    - T4.3: Hallucination Containment & Autonomous Epistemic Self-Correction Loop                     |
|    - T4.4: Progressive Knowledge Graph Lifecycle: Multi-Sprint Decay and Sleep Consolidation          |
|    - T4.5: Closed-Loop Enterprise Agent Self-Healing Pipeline with DoD Verification                   |
+-------------------------------------------------------------------------------------------------------+
```

---

## 4. Master Feature Inventory & Test Case Catalog (65 Tests)

### Tier 1: Core Feature Coverage (27 Tests)
| # | Test Function Name | Module | Feature Tested | Expected Contract |
|---|---|---|---|---|
| 1 | `test_tier1_r1_freeform_thought_to_json` | R1 | Free-form Thought Extraction & JSON Projection | Returns `status: "ok"`, `mode: "json"`, parses valid JSON dictionary |
| 2 | `test_tier1_r1_schema_validation_conformance` | R1 | JSON Schema-Guided Validation | Validates required fields, returns `status: "ok"`, valid payload |
| 3 | `test_tier1_r1_unified_diff_patch_projection` | R1 | Unified Diff Patch Generation | Extracts unified diff hunks (`---`, `+++`, `@@`), valid diff format |
| 4 | `test_tier1_r1_python_ast_projection` | R1 | Python AST Extraction & Compilation | Compiles extracted code snippet into valid Python AST tree |
| 5 | `test_tier1_r1_fsm_syntax_auto_repair` | R1 | Pushdown FSM Syntax Auto-Repair | Auto-repairs trailing commas, single quotes, unquoted keys |
| 6 | `test_tier1_r1_output_file_serialization` | R1 | CLI Output Serialization via `--output` | Writes projected output to disk, verifiable content |
| 7 | `test_tier1_r2_prover_accepted_debate` | R2 | Prover Argument Formulation & Win | Defends proposal with citations; returns `status: "ACCEPTED"`, `winner: "prover"` |
| 8 | `test_tier1_r2_verifier_refuted_debate` | R2 | Verifier Falsification & Attack Probe | Detects static sleeps/anti-patterns; returns `status: "REFUTED"`, `winner: "verifier"` |
| 9 | `test_tier1_r2_debate_rounds_configuration` | R2 | Multi-Round Debate Progression | Controls debate transcript depth (`--rounds 2` vs `--rounds 3`) |
| 10 | `test_tier1_r2_context_evidence_evaluation` | R2 | Context File Evaluation in Debate | Reads `--context` trace file and incorporates into argument evidence |
| 11 | `test_tier1_r2_transcript_structure_verification` | R2 | Debate Transcript Schema Integrity | Transcript items have speaker, round, claims, evidence/attacks |
| 12 | `test_tier1_r2_direct_api_run_debate` | R2 | Direct Python API Invocations | Executes `ProverVerifierGame().run_debate()` returning complete dict |
| 13 | `test_tier1_r3_low_entropy_consensus` | R3 | Semantic Clustering & Low Entropy | Equivalent hypotheses yield single cluster, $H_{\text{norm}} = 0.0$, write allowed |
| 14 | `test_tier1_r3_high_entropy_divergence` | R3 | Divergent Hypotheses & Write-Lock | Conflicting hypotheses yield 4 clusters, $H_{\text{norm}} = 1.0$, write locked |
| 15 | `test_tier1_r3_epistemic_search_plan_structure` | R3 | Epistemic Directive Generation | Emits structured 4-step search plan (read_file, AST check, schema inspect) |
| 16 | `test_tier1_r3_cli_prompt_mode` | R3 | Heuristic Prompt Hypothesis Generation | Generates 4 candidate interpretations from `--prompt`, evaluates entropy |
| 17 | `test_tier1_r3_cli_hypotheses_file` | R3 | Batch Evaluation via `--hypotheses-file` | Loads JSON array of hypotheses, emits structured evaluation |
| 18 | `test_tier1_r4_python_class_compression` | R4 | Multi-line Python Code Compression | Strips comments/docstrings/types, valid `ast.parse` on result |
| 19 | `test_tier1_r4_100pct_invariant_preservation` | R4 | Hard-Pinned Invariant Guarantee | Preserves 100% of variables, functions, branches, asserts (`100.0%`) |
| 20 | `test_tier1_r4_surprisal_ranking_comment_removal` | R4 | Shannon Surprisal Comment Ranking | Prunes repetitive comments before high-surprisal domain notes |
| 21 | `test_tier1_r4_budget_tokens_constraint` | R4 | Token Budget Ceiling Enforcement | Output token count bounded by `--budget-tokens` |
| 22 | `test_tier1_r4_cli_file_and_output` | R4 | CLI File Ingestion & Output Serialization | Reads `--file`, writes `--output`, emits JSON telemetry |
| 23 | `test_tier1_r5_node_and_association_upsert` | R5 | SQLite Node & Directional Edge CRUD | Records entity node and association edge; auto-provisions nodes |
| 24 | `test_tier1_r5_query_associations_descending_weight` | R5 | Knowledge Querying & Weight Ordering | Queries connected edges filtered by `min_weight`, ordered DESC |
| 25 | `test_tier1_r5_exponential_time_decay_math` | R5 | Continuous Exponential Temporal Decay | $w(t) = w_0 \cdot e^{-\lambda \Delta t}$, half-life decay verified |
| 26 | `test_tier1_r5_sleep_consolidation_defect_generalization` | R5 | Sleep Consolidation & Defect Archival | Clusters recurrent defects into generalized rule; archives defects |
| 27 | `test_tier1_r5_cli_subcommand_suite` | R5 | Complete Subcommand Suite Execution | Exercises `record`, `query`, `decay`, `consolidate`, `stats` via CLI |

### Tier 2: Boundary, Adversarial & Corner Cases (27 Tests)
| # | Test Function Name | Module | Boundary Condition Tested | Expected Safety Behavior |
|---|---|---|---|---|
| 28 | `test_tier2_r1_empty_input_handling` | R1 | Empty string, whitespace, blank thought | Clean exit with error status; zero unhandled crash |
| 29 | `test_tier2_r1_deeply_nested_structures` | R1 | Deep nesting (> 25 levels) | Pushdown descent without `RecursionError` |
| 30 | `test_tier2_r1_unrepairable_garbage_input` | R1 | Pure non-structured noise | Exit code 1 with diagnostic error message |
| 31 | `test_tier2_r1_nonexistent_files` | R1 | Missing `--input` or `--schema` file | Exit code 1/2 with "not found" diagnostic; no traceback |
| 32 | `test_tier2_r1_utf8_multibyte_and_emojis` | R1 | Vietnamese diacritics & UTF-8 emojis | Byte-for-byte character fidelity preserved |
| 33 | `test_tier2_r1_massive_scratchpad_performance` | R1 | Large scratchpad (> 100 KB) | Finishes in < 5.0s without regex backtracking lockup |
| 34 | `test_tier2_r2_empty_proposal_handling` | R2 | Blank/empty proposal text | Clean rejection; no divide-by-zero or crash |
| 35 | `test_tier2_r2_rounds_clamping_boundary` | R2 | Extreme rounds (`--rounds 0`, `--rounds 10`) | Safe execution without infinite loop or negative indexing |
| 36 | `test_tier2_r2_missing_context_file` | R2 | Non-existent `--context` file | Exit code 1 with clean diagnostic |
| 37 | `test_tier2_r2_unsubstantiated_claims_zero_citations` | R2 | Zero citations in proposal | Penalized by Verifier; fails evidence standard |
| 38 | `test_tier2_r2_counter_example_attack_severity` | R2 | Multi-flaw adversarial proposal | Verifier accumulates severity score proportionally |
| 39 | `test_tier2_r2_adversarial_prompt_injection` | R2 | "Ignore previous instructions" in proposal | Treated strictly as plain text data; debate continues |
| 40 | `test_tier2_r3_empty_hypotheses_handling` | R3 | Empty hypotheses list `[]` | Returns 0.0 entropy, confident status; no exception |
| 41 | `test_tier2_r3_single_item_hypothesis` | R3 | Single hypothesis `[H]` | Evaluates without $\log_2(1)$ division-by-zero error |
| 42 | `test_tier2_r3_extreme_threshold_boundaries` | R3 | Threshold at `0.0` vs `1.0` | 0.0 forces lockout; 1.0 permits code writes |
| 43 | `test_tier2_r3_short_tokens_empty_feature_clustering` | R3 | Short words ($<3$ chars) / stopwords only | Jaccard empty union handled gracefully ($J=1.0$) |
| 44 | `test_tier2_r3_cli_missing_and_invalid_args` | R3 | Missing both `--prompt` and `--hypotheses-file` | Exit code 1 with informative error message |
| 45 | `test_tier2_r4_empty_or_whitespace_string` | R4 | Empty/whitespace source text | Returns 0 tokens, 0.0 ratio, empty output; no crash |
| 46 | `test_tier2_r4_extreme_target_ratios` | R4 | Target ratio `1.0` vs `0.0` | 1.0 retains all; 0.0 retains 100% of invariants |
| 47 | `test_tier2_r4_docstring_only_body_pass_insertion` | R4 | Function with only a docstring | Inserts `pass` after stripping; valid Python AST |
| 48 | `test_tier2_r4_lexical_fallback_non_python` | R4 | Non-Python / JS / Markdown text | `ast.parse` triggers lexical fallback; strips comments safely |
| 49 | `test_tier2_r4_cli_argument_validation_matrix` | R4 | Missing args, both file & text, ratio > 1 | Every case exits with returncode 1 and diagnostic |
| 50 | `test_tier2_r5_empty_database_operations` | R5 | Operations on empty SQLite database | Queries return `[]`; consolidate returns 0 counts; no crash |
| 51 | `test_tier2_r5_future_timestamp_clock_skew` | R5 | Future timestamps / clock skew ($\Delta t < 0$) | Weights never artificially increase |
| 52 | `test_tier2_r5_weak_edge_pruning_and_orphan_rule_archival` | R5 | Sub-threshold edges & orphan rules | Weak edges deleted; disconnected rules marked archived |
| 53 | `test_tier2_r5_sqlite_wal_mode_and_concurrency` | R5 | WAL mode & concurrent connection queries | `journal_mode=wal`, no table lock contention |
| 54 | `test_tier2_r5_cli_error_handling_emits_structured_json` | R5 | CLI errors with `--json` flag | Emits valid JSON `{"status": "error", "error": "..."}` |

### Tier 3: Cross-Feature Combinations (6 Tests)
| # | Test Function Name | Pipeline | Cross-Feature Interaction Validated |
|---|---|---|---|
| 55 | `test_tier3_r1_projected_json_fed_to_r2_debate` | R1 -> R2 | Unstructured thinking decoded to schema-valid JSON proposal, evaluated in debate |
| 56 | `test_tier3_r4_pruned_code_evaluated_by_r3_entropy` | R4 -> R3 | Pruned code tested against original code via semantic clustering to confirm equivalence |
| 57 | `test_tier3_r2_debate_outcome_consolidated_in_r5_memory` | R2 -> R5 | Winning debate thesis stored as resolution edge in SQLite graph, sleep consolidated |
| 58 | `test_tier3_r1_patch_diff_pruned_by_r4_invariant_preservation` | R1 -> R4 | Projected unified diff compressed via surprisal pruner with 100% invariant preservation |
| 59 | `test_tier3_r3_epistemic_search_queries_r5_associative_memory` | R3 -> R5 | High semantic entropy write-lockout queries associative graph to resolve uncertainty |
| 60 | `test_tier3_r4_compressed_context_supplied_to_r2_debate` | R4 -> R2 | Verbose test trace log pruned by 70% and supplied as grounded debate context |

### Tier 4: Real-World Autonomous Agent Workloads (5 Tests)
| # | Test Function Name | Workflow Summary | Techniques Integrated |
|---|---|---|---|
| 61 | `test_tier4_defect_triage_epistemic_search_patch_projection_memory` | Triage flaky test -> epistemic memory query -> patch projection -> debate -> consolidation | R3 + R5 + R1 + R2 |
| 62 | `test_tier4_ci_log_distillation_autopsy_and_adversarial_adjudication` | 5,000-line CI failure log compressed -> autopsy JSON projected -> debate -> memory stored | R4 + R1 + R2 + R5 |
| 63 | `test_tier4_hallucination_containment_and_epistemic_self_correction` | Agent hallucinates fictitious methods -> entropy locks code -> code read -> safe patch | R3 + R4 + R1 |
| 64 | `test_tier4_progressive_knowledge_lifecycle_decay_and_consolidation` | Multi-sprint knowledge lifecycle: seeding -> debate -> 30-day temporal decay -> consolidation | R5 + R2 + R5 |
| 65 | `test_tier4_closed_loop_self_healing_swarm_with_dod_verification` | Heals broken Playwright test: log pruned -> entropy check -> patch -> debate -> infer_linter verify | R4 + R3 + R1 + R2 + R5 |

---

## 5. Harness Utilities & Fixtures Specification

The test harness exposes four core utilities ensuring idempotent, hermetic, and safe test execution:

```python
def require_tool(rel_path: str) -> Path:
    """
    Validates tool existence before executing tests.
    If absent, marks the test as SKIPPED to support progressive milestone delivery.
    """
    tool_path = REPO_ROOT / rel_path
    if not tool_path.exists():
        pytest.skip(f"Tool '{rel_path}' is not yet implemented (scheduled for milestone delivery)")
    return tool_path


def run_cli(
    cmd: List[str],
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: float = 30.0
) -> subprocess.CompletedProcess:
    """Executes subprocess with explicit timeout and SYNAPSE_LANG=en environment propagation."""
    full_env = os.environ.copy()
    full_env.setdefault("SYNAPSE_LANG", "en")
    if env:
        full_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=full_env,
        timeout=timeout
    )


def unique_code(prefix: str = "E2E_REASON_") -> str:
    """Generates an idempotent dynamic unique test token with timestamp and UUID."""
    return f"{prefix}{int(time.time())}_{uuid.uuid4().hex[:8]}"
```

All file operations, database paths, and temporary artifacts must strictly utilize pytest's built-in `tmp_path` fixture:
```python
def test_example(tmp_path):
    db_path = tmp_path / "sandbox.db"
    # execute test using db_path...
```

---

## 6. Execution Runbook & Verification Commands

### Full E2E Test Suite Run:
```bash
pytest tests/e2e/test_deep_reasoning_pipeline_e2e.py tests/e2e/test_reference_enhancements_e2e.py -v
```

### Tier-Specific Execution Commands:
```bash
# Tier 1: Feature Coverage Only
pytest tests/e2e/test_reference_enhancements_e2e.py -k "tier1" -v

# Tier 2: Boundary & Corner Cases Only
pytest tests/e2e/test_reference_enhancements_e2e.py -k "tier2" -v

# Tier 3: Cross-Feature Pairwise Pipelines
pytest tests/e2e/test_reference_enhancements_e2e.py -k "tier3" -v

# Tier 4: Real-World Workflows
pytest tests/e2e/test_reference_enhancements_e2e.py -k "tier4" -v
```

### Static Quality Linter (Gate 07):
```bash
python3 tools/lint/infer_linter.py tests/e2e/test_deep_reasoning_pipeline_e2e.py
```

### 10-Gate Full DoD Verification:
```bash
python3 tools/core/verify_all.py --mode hub
```

---

## 7. Defect Triage & Troubleshooting Matrix

| Symptom | Probable Cause | Action / Remediation |
|---|---|---|
| `SKIPPED: Tool '...' is not yet implemented` | Milestone tool file has not landed on disk yet | Normal progressive testability behavior; skips gracefully until worker milestone merges |
| `infer_linter.py: FAKE_PASS_NO_ASSERTION` | Test contains zero assertions or asserts literal `True` | Add meaningful behavioral assertion checking output dictionary or returncode |
| `infer_linter.py: SWALLOWED_EXCEPTION` | Test contains `except: pass` or dummy assignment `_ = e` | Assert on exception type or use `pytest.raises` |
| `infer_linter.py: EXCESSIVE_HARD_DELAY` | Static `time.sleep` used in test | Remove `time.sleep`; rely on subprocess `timeout=30.0` or dynamic assertion checks |
| `sqlite3.OperationalError: database is locked` | SQLite database opened without WAL mode | Initialize database with `auto_wal=True` and ensure connection closure |
| `UnicodeDecodeError` / BOM detected | File contains UTF-8 BOM (`0xEF, 0xBB, 0xBF`) | Save file with strict UTF-8 (No BOM) encoding |
