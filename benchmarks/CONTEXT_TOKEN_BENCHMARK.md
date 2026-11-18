# Empirical Context & Token Reduction Benchmark (Dual-Track)

> **Scientific Disclosure:** This benchmark distinguishes between:
> 1. **Track 1 (Synthetic Micro-Workloads):** Deterministic micro-workloads evaluating isolated context patterns.
> 2. **Track 2 (Empirical Reference Suites):** Live static file inspections on real example workspaces within the repository.
> - **Tokenizer Engine:** `cl100k_base` (Exact: `True`)
> - **Encoding Scope:** `cl100k_base` (Standard OpenAI BPE encoding for LLMs).
> - **Billing Notice:** Offline estimates do not represent live LLM provider billing usage. Live provider usage reduction is only verified when real provider response metrics are paired.

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

## Track 2: Empirical Reference Suites Benchmark (Static Workspace Inspection)

> *Methodology: Dynamically enumerates all 14 rules and 57 skills in repository without static per-skill multiplier assumptions.*
> *Disclosure: 'Avoided Disk Read (I/O)' measures filesystem file size bytes not read from storage; it is strictly distinguished from context tokens and is not billed token savings.*

| Reference Project | Detected Stack | Confidence | Catalog Summary Saved | Full Hydration Saved | Avoided Disk Read (I/O) |
|---|---|:---:|:---:|:---:|:---:|
| **Playwright CRM Suite** | `playwright` | 1.0 | **11,242** (77.1%) | **82,850** (84.4%) | ~341 KB |
| **Pytest API Suite** | `api` | 0.8 | **10,540** (72.3%) | **83,209** (84.8%) | ~343 KB |
| **Katalon Suite** | `katalon` | 1.0 | **12,007** (82.3%) | **88,162** (89.8%) | ~363 KB |
| **Selenium Suite** | `selenium` | 0.9 | **12,010** (82.3%) | **88,411** (90.0%) | ~364 KB |

## Key Optimization Drivers

1. **Zero-Second Auth (`storageState.json`):** Bypasses repetitive login forms and CSRF redirect loops.
2. **Accessibility Object Model (AOM):** Extracts compact semantic trees (< 500 tokens) instead of bloated 2,000+ line raw HTML.
3. **Flat Clean POM Separation:** Scopes business methods without cluttering scripts with raw selectors.
4. **Pinpoint Log Distillation:** Replaces hundreds of lines of noise with focused, evidence-preserving triage blocks.

*Report generated: `2026-11-18T12:06:47.687868+00:00` by `tools/benchmark_swarm_context.py`*