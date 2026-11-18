---
name: cost-aware-llm-pipeline
description: >
  Cost-aware LLM pipeline design skill: route tasks to the cheapest capable model
  using complexity classifiers, implement token budgets, and instrument pipelines
  with cost metrics. Use when building multi-step AI workflows where inference cost
  is a production concern.
version: 1.0.0
attribution: Adapted from ECC (affaan-m/ecc, Apache 2.0). Extended by Thế Vị (@TeeVee98).
---

# Cost-Aware LLM Pipeline Skill (`cost-aware-llm-pipeline`)

## Overview

Not every task requires the most powerful (and expensive) model. This skill governs **model routing by task complexity** — sending simple, well-defined tasks to small fast models and reserving large models for genuinely complex reasoning tasks.

> [!TIP]
> A well-tuned routing classifier typically reduces LLM inference costs by 60-80%
> with less than 2% degradation in output quality on structured tasks.

## When to Activate

- Designing a multi-step AI pipeline where different stages have different complexity profiles.
- Auditing an existing pipeline where all tasks use the same (expensive) model.
- Implementing token budgets for a CI agent that must stay within cost limits.

## Complexity Routing Tiers

| Tier | Task Type | Recommended Model Class | Token Budget |
|------|-----------|------------------------|--------------|
| Tier 1 | Structured extraction, format conversion, regex generation | Small / Flash | 500 input, 200 output |
| Tier 2 | Code review, test case generation, summarization | Medium | 2000 input, 800 output |
| Tier 3 | Multi-file refactoring, architecture design, complex debugging | Large / Pro | 8000 input, 2000 output |
| Tier 4 | Novel research, adversarial falsification, full system design | Largest | Unbounded (human review required) |

## Complexity Classifier Rules

```python
# tools/orchestration/complexity_router.py
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98)
# SPDX-License-Identifier: MIT
"""Heuristic complexity classifier for LLM task routing."""

from __future__ import annotations
import re
from enum import IntEnum


class Tier(IntEnum):
    T1_SIMPLE = 1
    T2_MEDIUM = 2
    T3_COMPLEX = 3
    T4_RESEARCH = 4


# Heuristic signals for complexity classification
_T3_SIGNALS = re.compile(
    r"\b(refactor|architecture|design|multi[- ]file|system|distributed|"
    r"concurrency|deadlock|migration|schema|performance|optimization)\b",
    re.IGNORECASE,
)
_T4_SIGNALS = re.compile(
    r"\b(novel|research|adversarial|unprecedented|first[- ]principles|"
    r"open[- ]ended|exploratory)\b",
    re.IGNORECASE,
)
_T1_SIGNALS = re.compile(
    r"\b(extract|convert|format|rename|list|count|summarize in one sentence|"
    r"regex for|translate to json)\b",
    re.IGNORECASE,
)


def classify_task(prompt: str, context_tokens: int = 0) -> Tier:
    """Classify a task prompt into a routing tier."""
    if _T4_SIGNALS.search(prompt):
        return Tier.T4_RESEARCH
    if _T3_SIGNALS.search(prompt) or context_tokens > 4000:
        return Tier.T3_COMPLEX
    if _T1_SIGNALS.search(prompt) and context_tokens < 500:
        return Tier.T1_SIMPLE
    return Tier.T2_MEDIUM
```

## Token Budget Enforcement

```python
def enforce_token_budget(tier: Tier, actual_input_tokens: int) -> None:
    """Raise ValueError if input exceeds tier budget."""
    budgets = {Tier.T1_SIMPLE: 500, Tier.T2_MEDIUM: 2000, Tier.T3_COMPLEX: 8000}
    limit = budgets.get(tier)
    if limit and actual_input_tokens > limit:
        raise ValueError(
            f"Token budget exceeded for Tier {tier.name}: "
            f"{actual_input_tokens} > {limit}. Escalate to higher tier or trim context."
        )
```

## Cost Instrumentation

Always record per-call cost metrics:

```python
# Log to: Reports/llm_cost_log.jsonl (one JSON object per line)
{
  "timestamp": "2026-11-18T10:00:00Z",
  "task_id": "fact-forcing-gate-review-abc123",
  "tier": "T2_MEDIUM",
  "model": "gemini-flash",
  "input_tokens": 1240,
  "output_tokens": 380,
  "latency_ms": 820,
  "cost_usd": 0.0004
}
```

## Non-Goals

- Do not route security-critical tasks (AGS1-AGS4, P1, CRITICAL findings) to Tier 1 models.
- Do not use cost routing as a reason to skip the adversarial falsification step (AGENTS.md §2 Rule 3).
- Do not hardcode model names — always resolve through a routing config file.
