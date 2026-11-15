# QA Agent Heuristic Regression Benchmark (25 Challenge Vectors)

> **Synthetic Regression Harness for Deterministic Test-Healing Engines & Quality Sentinels**  
> Verifies self-healing locator cascades, API contract drift heuristics, timing barriers, and AST mutation sensitivity across 25 curated production failure vectors without calling external cloud LLMs.

---

## 1. Scope & Design Philosophy

When building autonomous testing sentinels, rule patterns and heuristics must be rigorously guarded against regressions. 

This Benchmark Suite serves as a **deterministic, offline regression test harness** that validates:
1. **Heuristic Recovery Rate (%):** Verification that the hub's rule cascades correctly resolve known failure vectors.
2. **Harness Latency (MTTR):** Local rule evaluation latency in seconds (< 0.1s offline).
3. **AST Mutation Sensitivity:** Verification that assertion sensitivity catches injected syntactic mutants ($\ge 80\%$).
4. **Action Safety Firewall:** Assurance that suggested remedies comply with non-destructive action policies (`safety_firewall.py`).

> ⚠️ **Important Methodology Note:**  
> This harness is an **internal synthetic benchmark**, not an end-to-end evaluation of live multi-turn LLM agents against cloud APIs. Challenges evaluate deterministic rule-based and heuristic matchers (`heuristic_locator_matcher.py`, `micro_mutator.py`, `safety_firewall.py`). Token counts are character-density heuristics and MTTR represents local processor execution time. Live agent benchmarking with multi-turn API telemetry is planned for future releases.

---

## 2. Failure Domains & Challenge Taxonomy

The benchmark consists of 25 curated challenge vectors across 5 categories:

| Domain | Challenges | Scenarios Covered |
| :--- | :---: | :--- |
| **`locator_drift`** | 5 | Dynamic CSS-in-JS hashes, nested Shadow DOM piercing, CTA text changes, `id` removal, `<a>` to `<button>` ARIA transformation. |
| **`api_contract_drift`** | 5 | Integer to String type mutation, response field rename, nested object flattening, status code shifts (200 $\rightarrow$ 201), Bearer auth headers. |
| **`timing_and_race`** | 5 | 3.5s network throttling, PrimeNG modal backdrop fading intercept, debounced search race, async SVG charts, infinite scroll lazy chunking. |
| **`stale_and_mutation`** | 5 | WebSocket live ticker table re-renders, tab switch DOM detachments, table pagination stale indices, modal re-instantiation, i18n locale swaps. |
| **`fake_pass_tautology`** | 5 | Swallowed HTTP 500 in empty catch blocks, zero-assertion smoke tests, tautological `assert true == true`, unawaited async assertions, unbounded relational checks. |

---

## 3. Running the Benchmark

### Run Complete Suite (All 25 Challenges):
```bash
python benchmarks/qa_eval/eval_runner.py
```

### Run by Specific Category:
```bash
# Evaluate only locator drift challenges
python benchmarks/qa_eval/eval_runner.py --category locator_drift

# Evaluate only API contract drift challenges
python benchmarks/qa_eval/eval_runner.py --category api_contract_drift

# Evaluate only timing and race conditions
python benchmarks/qa_eval/eval_runner.py --category timing_and_race
```

### Output Formats:
- **Terminal Summary:** Colorized table with resolution status, latency, and heuristic token footprints.
- **Markdown Report:** Formatted executive report at `benchmarks/qa_eval/reports/BENCHMARK_REPORT.md`.
- **JSON Telemetry:** Machine-readable metrics at `benchmarks/qa_eval/reports/eval_results.json`.

---

## 4. Current Harness Telemetry

| Benchmark Metric | Harness Result | Validation Mechanism |
| :--- | :---: | :--- |
| **Deterministic Rule Resolution** | **100% (25/25)** | Verified via heuristic cascade & dataset expectations |
| **Harness Evaluation MTTR** | **< 0.1s** | Local Python runtime execution |
| **Heuristic Token Footprint** | **~75 tokens / vector** | Lexical character-to-token compression ratio |
| **Mutation Score Gate** | **$\ge 80\%$** | Verified via `micro_mutator.py` |
| **Action Safety Clearance** | **100% (Pass)** | Verified via `safety_firewall.py` non-destructive policy |
