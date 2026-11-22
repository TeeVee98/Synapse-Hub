---
name: entropy-context-pruning
description: Use when compressing context, pruning low-information tokens, eliminating redundant syntax or boilerplate while strictly preserving code identifiers, signatures, and logic branching.
category: context_and_optimization
version: "1.0.0"
policies:
  network: none
  shell: read-only
  filesystem: workspace-sandbox
---

<!--
Copyright (c) 2026 Thế Vị (@TeeVee98)
Synapse Hub — Standards & Protocols
-->

# Information-Theoretic Entropy Context Pruning Standard

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Use when compressing context, pruning low-information tokens, eliminating redundant syntax or boilerplate while strictly preserving code identifiers, signatures, and logic branching.
- **Activation Scope:** Active during multi-agent context window management, long prompt construction, log compression, and context budget optimization in `tools/reasoning/entropy_pruning.py`.
- **Keywords:** `entropy`, `pruning`, `context compression`, `LLMLingua-2`, `surprisal`, `information theory`, `token budget`.

---

## 2. Non-Goals & Boundary Constraints (Inputs & Prerequisites)

### Non-Goals
- Do NOT prune variable names, function signatures, class definitions, branching statements (`if`, `elif`, `else`, `try`, `except`, `finally`, `for`, `while`), or assertions (`assert`) when `preserve_identifiers=True`.
- Do NOT introduce external heavy machine learning or neural network dependencies; all entropy computations use standard information theory via Python Standard Library (`ast`, `tokenize`, `math`, `collections`).
- Do NOT produce syntactically broken Python code; empty function or class bodies resulting from docstring removal must be safely populated with `pass`.

### Inputs & Prerequisites
- **Source Input:** A valid file path (`--file`) or raw text string (`--text`) representing source code, markdown, or prompt content.
- **Target Ratio:** Float between `0.0` and `1.0` representing the target retained token proportion (default: `0.50`).
- **Token Budget:** Optional integer (`--budget-tokens`) defining an absolute upper bound on token count.
- **Preservation Flag:** Boolean (`--preserve-identifiers`, default `True`) guaranteeing hard-pinning of code invariants.

---

## 3. Ordered Execution Workflow (Workflow & Execution Lifecycle)

The entropy pruning lifecycle follows a 4-phase information-theoretic reduction process:

### Phase 1: AST Role Tagging & Invariant Pinning
The pruner parses the source input using Python AST (`ast.parse`) or lexical token analysis to categorize each syntactic element:
1. **Invariant Identifiers:** Variable names, function names, class names, argument names.
2. **Invariant Control Flow:** Branching structures (`if`, `elif`, `else`, `for`, `while`, `try`, `except`, `finally`, `match`, `case`).
3. **Invariant Assertions:** Integrity assertions (`assert`) and testing checks.
4. **Pruning Candidates:** Comments, docstrings, redundant type hints, decorative dividers, repetitive filler words.

### Phase 2: Surprisal Calculation ($I(t) = -\log_2 P(t)$)
Computes token frequency distribution $P(t) = \frac{\text{count}(t)}{N}$ and Shannon self-information (surprisal in bits):

<!-- classification: illustrative -->
```python
# Shannon surprisal computation
import math

def calculate_surprisal(token_count: int, total_tokens: int) -> float:
    prob = token_count / max(1, total_tokens)
    return -math.log2(prob) if prob > 0 else 0.0
```

Low-surprisal tokens (repetitive comments, generic boilerplate) are scored lower and scheduled for earliest removal.

### Phase 3: Multi-Stage Pruning
Pruning proceeds monotonically down toward `target_ratio` or `budget_tokens`:
1. **Stage 1 (Comments):** Remove comments in order of ascending surprisal (lowest information content pruned first).
2. **Stage 2 (Docstrings):** Remove verbose docstrings in order of ascending surprisal; insert `pass` if block body becomes empty.
3. **Stage 3 (Type Annotations):** Strip redundant parameter type hints and return signatures.
4. **Stage 4 (Formatting):** Collapse consecutive blank lines and trailing whitespace.
5. **Stage 5 (Invariant Floor):** When `preserve_identifiers=True`, stop pruning immediately at the invariant boundary to guarantee 100% preservation of logic.

### Phase 4: Output Synthesis & Verification
Execute via command line:

<!-- classification: illustrative -->
```bash
python tools/reasoning/entropy_pruning.py --file input_code.py --target-ratio 0.50 --json
```

Example JSON output structure:

<!-- classification: illustrative -->
```json
{
  "original_token_count": 106,
  "pruned_token_count": 35,
  "compression_ratio": 0.3302,
  "preserved_identifiers_pct": 100.0,
  "compressed_text": "def process_payment(account_id, amount, currency = \"USD\"):\n...",
  "status": "ok"
}
```

---

## 4. Verification Points & DoD (Quality Gates & Verification)

- **Invariant Retention Gate:** `preserved_identifiers_pct` must equal `100.0` when `preserve_identifiers=True`.
- **Syntax Integrity Gate:** Compressed Python code must be valid syntax verifiable by `ast.parse(compressed_text)`.
- **Budget Compliance Gate:** Token count of `compressed_text` must be $\le \text{budget\_tokens}$ (or bounded by invariant floor).
- **Error Handling Gate:** Invalid arguments (`target_ratio < 0.0`, missing files) must terminate cleanly with exit code 1.
- **Unit Test Coverage:** All 4 test battery scenarios in `tests/test_entropy_pruning.py` must pass with zero fake passes.

---

## 5. Handoff Protocol

1. **Structured Metadata Delivery:** Downstream agents consume the pruned context alongside telemetry (`compression_ratio`, `preserved_identifiers_pct`).
2. **Context Window Injection:** The `compressed_text` is injected directly into prompt scratchpads or LLM context windows.
3. **Reference Artifact:** Example configuration and output are recorded in `standards/reasoning/entropy-context-pruning/examples/pruning_example.json`.
