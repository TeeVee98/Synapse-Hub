# Empirical Context & Token Reduction Benchmark (Dual-Track)

> **Scientific Disclosure:** This benchmark distinguishes between:
> 1. **Track 1 (Synthetic Micro-Workloads):** Deterministic micro-workloads evaluating isolated context patterns.
> 2. **Track 2 (Empirical Reference Suites):** Live measurements on real example workspaces within the repository.
> - **Tokenizer Engine:** `cl100k_base` (Exact: `True`)
> - **Encoding Scope:** `cl100k_base` (Standard OpenAI BPE encoding for LLMs; benchmark artifact specifies exact tokenizer scope).

## Track 1: Deterministic Micro-Workload Benchmark (Synthetic)

| Metric | Naive LLM Baseline | Synapse Hub Swarm | Empirical Impact |
|---|:---:|:---:|:---:|
| **Total Tokens Consumed** | `2,396` tokens | `423` tokens | **-1,973 tokens** |
| **Context Efficiency Gain** | Baseline (100%) | Optimized (17.7%) | **+82.35% reduction** |
| **Enterprise Threshold (>= 40%)** | — | — | **✅ PASS (Exceeded)** |

### Scenario Breakdown

| ID | Scenario | Baseline Tokens | Synapse Tokens | Tokens Saved | Reduction (%) | Status |
|---|---|:---:|:---:|:---:|:---:|:---:|
| `SCN-01-AUTH` | **Authentication & Session Initialization** | 734 | 147 | -587 | **79.97%** | ✅ PASS |
| `SCN-02-GRID` | **Data Table Grid & Entity Mutation** | 799 | 56 | -743 | **92.99%** | ✅ PASS |
| `SCN-03-MONOLITH` | **Page Class Inspection & Refactoring** | 372 | 111 | -261 | **70.16%** | ✅ PASS |
| `SCN-04-TRIAGE` | **Failure Autopsy & Triage Diagnostics** | 491 | 109 | -382 | **77.8%** | ✅ PASS |

## Track 2: Empirical Reference Suites Benchmark (Real Projects)

> *Methodology: Dynamically enumerates all 13 rules and 53 skills in repository without static per-skill multiplier assumptions.*
> *Disclosure: 'Avoided Disk Read' measures disk file bytes not read from storage, distinguished from prompt context tokens.*

| Reference Project | Detected Stack | Confidence | Catalog Summary Saved | Full Hydration Saved | Avoided Disk Read (I/O) |
|---|---|:---:|:---:|:---:|:---:|
| **Playwright CRM Suite** | `playwright` | 1.0 | **7,858** (69.1%) | **50,897** (79.2%) | ~203 KB |
| **Pytest API Suite** | `api` | 0.8 | **8,775** (77.1%) | **53,758** (83.6%) | ~215 KB |
| **Katalon Suite** | `katalon` | 1.0 | **8,890** (78.2%) | **56,460** (87.8%) | ~226 KB |
| **Selenium Suite** | `selenium` | 0.9 | **8,893** (78.2%) | **56,531** (87.9%) | ~226 KB |

## Key Optimization Drivers

1. **Zero-Second Auth (`storageState.json`):** Bypasses repetitive login forms and CSRF redirect loops.
2. **Accessibility Object Model (AOM):** Extracts compact semantic trees (< 500 tokens) instead of bloated 2,000+ line raw HTML.
3. **Flat Clean POM Separation:** Scopes business methods without cluttering scripts with raw selectors.
4. **Pinpoint Log Distillation:** Replaces hundreds of lines of noise with focused, evidence-preserving triage blocks.

*Report generated: `2026-11-14T08:20:03.313108+00:00` by `tools/benchmark_swarm_context.py`*