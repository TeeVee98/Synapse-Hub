# MIPROv2 Bayesian Prompt Optimization Walkthrough

> **Objective:** Transition from handcrafted prompt instructions to algorithmically tuned assertions achieving $\ge 90\%$ mutation kill rate under 600 tokens.

---

## 1. Input DSPy Signature Specification

```python
from tools.dspy_qa_signatures import AssertionGeneratorSignature

# Signature definition
signature = AssertionGeneratorSignature(
    input_fields=["page_class_context", "user_action", "expected_state"],
    output_fields=["defensive_assertions", "state_verification_code"]
)
```

---

## 2. Bayesian Search Configuration (`tools/mipro_assertion_tuner.py`)

```bash
python tools/mipro_assertion_tuner.py compile-module \
  --signature "AssertionGenerator" \
  --trials 25 \
  --min-mutation-kill-rate 85.0 \
  --max-tokens 650 \
  --out-module compiled/optimized_assertion_gen.json
```

---

## 3. Optimization Telemetry Log (Trial 1 vs Trial 22)

| Trial | Prompt Variant Phrasing | Demonst. Count | Kill Rate | Token Cost | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Trial 1 (Baseline)** | *"Write assertions that check if action succeeded"* | 1 demo | 61.2% | 420 tokens | ❌ REJECT (< 80%) |
| **Trial 8** | *"Validate return code and verify toast visibility"* | 2 demos | 78.4% | 510 tokens | ❌ REJECT (< 80%) |
| **Trial 22 (Optimal)** | *"Assert system invariants: check state mutation, verify error overlay detachment, and assert non-empty collection"* | 3 demos (from `skill_vault`) | **92.6%** | 585 tokens | ✅ COMPILED PASS |

---

## 4. Resulting Optimized Module

The compiled prompt module is frozen into `compiled/optimized_assertion_gen.json` for deterministic execution by `pom-crafter` without prompt drift.
