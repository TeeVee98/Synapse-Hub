---
name: eval-harness
description: >
  Eval-Driven Development (EDD) skill: design, implement, and interpret model
  evaluation harnesses with pass@k scoring, consistency checks, and regression
  baselines. Use when developing or validating AI-generated outputs against
  deterministic rubrics.
version: 1.0.0
attribution: Adapted from ECC (affaan-m/ecc, Apache 2.0). Extended by Thế Vị (@TeeVee98).
---

# Eval-Driven Development Skill (`eval-harness`)

## Overview

Eval-Driven Development treats AI output quality the same way test-driven development treats software correctness: **define the rubric first, then iterate until all evals pass**. This skill governs how to design, run, and interpret evaluation harnesses within Synapse Hub.

> [!IMPORTANT]
> Never relax an eval rubric to manufacture a passing score. Eval failures are
> ground truth signals — not obstacles to route around. (Truth Anchor invariant.)

## When to Activate

- Designing evaluation criteria for a new AI-assisted test generation feature.
- Validating that a prompt/skill produces consistently correct outputs.
- Running regression baselines before shipping a new agent persona or skill.
- Comparing two model versions on the same task distribution.

## Core Concepts

### pass@k Scoring

For a task with `k` sampled outputs, `pass@k` is the probability that at least one sample passes all rubric checks:

$$\text{pass@k} = 1 - \frac{\binom{n - c}{k}}{\binom{n}{k}}$$

Where `n` = total samples drawn, `c` = number of correct samples.

**Practical thresholds (Synapse Hub defaults):**
- `pass@1 >= 0.80` — acceptable for production skills
- `pass@3 >= 0.95` — required for critical QA automation paths
- `pass@10 >= 0.99` — required for regression-guarded core skills

### Rubric Design Rules

1. **Atomic, falsifiable criteria** — each rubric item must be a boolean assertion, not a subjective rating.
2. **Deterministic reference fixtures** — maintain a versioned golden fixture set in `tests/fixtures/eval/`.
3. **Adversarial falsification** — for each rubric, propose 3 ways the model could plausibly fail it. Write counter-examples as negative test cases.

## Skill Lifecycle

```
Phase 1 — RUBRIC DESIGN
  ↓ Define atomic pass/fail criteria
  ↓ Create reference fixtures in tests/fixtures/eval/
  ↓ Author negative (expected-to-fail) counter-examples

Phase 2 — HARNESS IMPLEMENTATION
  ↓ Script sampler (n >= 20 samples per task)
  ↓ Deterministic scorer (zero fuzzy string matching)
  ↓ pass@k calculator

Phase 3 — BASELINE & REGRESSION
  ↓ Record baseline scores to reports/eval_baseline.json
  ↓ Gate: CI blocks merge if pass@1 drops > 5% from baseline
  ↓ Archive per-run SARIF report via tools/report/sarif_exporter.py
```

## Implementation Template

```python
# tests/eval/run_eval.py — Minimal Eval Harness (Synapse Hub)
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98)
# SPDX-License-Identifier: MIT

import json
from pathlib import Path
from typing import Callable, List


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k estimator."""
    if n - c < k:
        return 1.0
    from math import comb
    return 1.0 - comb(n - c, k) / comb(n, k)


def run_eval(
    task_fn: Callable[[], str],
    rubric_checks: List[Callable[[str], bool]],
    n_samples: int = 20,
) -> dict:
    """Sample n outputs and score against all rubric checks."""
    results = []
    for _ in range(n_samples):
        output = task_fn()
        passed = all(check(output) for check in rubric_checks)
        results.append(passed)
    c = sum(results)
    return {
        "n": n_samples,
        "c": c,
        "pass@1": pass_at_k(n_samples, c, 1),
        "pass@3": pass_at_k(n_samples, c, 3),
    }
```

## Non-Goals

- Do not use fuzzy string similarity as a sole eval criterion.
- Do not fake evals by reducing `n_samples` below 10.
- Do not suppress eval failures — always surface them in reports.
