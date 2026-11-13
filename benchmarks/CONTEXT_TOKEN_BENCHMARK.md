# Empirical Context & Token Reduction Benchmark (Dual-Track)

> **Scientific Disclosure:** This benchmark distinguishes between:
> 1. **Track 1 (Synthetic Micro-Workloads):** Deterministic micro-workloads evaluating isolated context patterns.
> 2. **Track 2 (Empirical Reference Suites):** Live measurements on real example workspaces within the repository.

## Track 1: Deterministic Micro-Workload Benchmark (Synthetic)

| Metric | Naive LLM Baseline | Synapse Hub Swarm | Empirical Impact |
|---|:---:|:---:|:---:|
| **Total Tokens Consumed** | `2,855` tokens | `496` tokens | **-2,359 tokens** |
| **Context Efficiency Gain** | Baseline (100%) | Optimized (17.4%) | **+82.63% reduction** |
| **Enterprise Threshold (>= 40%)** | — | — | **✅ PASS (Exceeded)** |

### Scenario Breakdown

| ID | Scenario | Baseline Tokens | Synapse Tokens | Tokens Saved | Reduction (%) | Status |
|---|---|:---:|:---:|:---:|:---:|:---:|
| `SCN-01-AUTH` | **Authentication & Session Initialization** | 812 | 179 | -633 | **77.96%** | ✅ PASS |
| `SCN-02-GRID` | **Data Table Grid & Entity Mutation** | 1,104 | 66 | -1,038 | **94.02%** | ✅ PASS |
| `SCN-03-MONOLITH` | **Page Class Inspection & Refactoring** | 480 | 146 | -334 | **69.58%** | ✅ PASS |
| `SCN-04-TRIAGE` | **Failure Autopsy & Triage Diagnostics** | 459 | 105 | -354 | **77.12%** | ✅ PASS |

## Track 2: Empirical Reference Suites Benchmark (Real Projects)

| Reference Project | Detected Stack | Confidence | Catalog Summary Saved | Full Hydration Saved | Avoided Disk Read |
|---|---|:---:|:---:|:---:|:---:|
| **Playwright CRM Suite** | `playwright` | 1.0 | **9,520** (74.0%) | **86,800** (85.2%) | ~354 KB |
| **Pytest API Suite** | `api` | 0.8 | **10,140** (78.8%) | **89,100** (87.4%) | ~363 KB |
| **Katalon Suite** | `katalon` | 1.0 | **10,380** (80.7%) | **92,700** (91.0%) | ~377 KB |
| **Selenium Suite** | `selenium` | 0.9 | **10,380** (80.7%) | **92,700** (91.0%) | ~377 KB |

## Key Optimization Drivers

1. **Zero-Second Auth (`storageState.json`):** Bypasses repetitive login forms and CSRF redirect loops.
2. **Accessibility Object Model (AOM):** Extracts compact semantic trees (< 500 tokens) instead of bloated 2,000+ line raw HTML.
3. **Flat Clean POM Separation:** Scopes business methods without cluttering scripts with raw selectors.
4. **Pinpoint Log Distillation:** Replaces hundreds of lines of noise with focused, evidence-preserving triage blocks.

*Report generated: `2026-11-13T15:57:11.520186+00:00` by `tools/benchmark_swarm_context.py`*