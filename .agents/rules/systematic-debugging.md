---
trigger: always_on
description: Enforce rigorous engineering discipline, systematic debugging without guesswork, and verification before completion.
---

# Systematic Debugging & Verification Discipline (Superpowers Standard)

*(Inherited from `obra/superpowers`)*

This rule governs all AI Agents operating on the repository. It mandates strict engineering rigor, prohibiting intuitive guesswork and unverified declarations of completion.

---

## 1. Iron Discipline: Zero Guesswork Debugging

1. **Evidence Before Action:**
   - Never modify code based on a hunch or assumption.
   - Every bug fix or locator update must be preceded by concrete ground-truth evidence:
     - Log excerpt showing the exact failing line and exception.
     - Visual inspection of `Screenshots/FAILED_*.png`.
     - Live DOM element state verified via Playwright Live Interaction.
2. **Preserve Working Code:**
   - When fixing an issue in a Page Class or script, touch only the minimal lines required. Never rewrite working methods speculatively.

---

## 2. Verification-First & Zero False Completion

1. **Never Declare Complete Without Running Verification:**
   - Any agent claiming a fix or refactoring is finished MUST run:
     ```bash
     python3 tools/verify_all.py
     ```
   - All 10 Gates must return `PASS`. If any gate fails, the task is NOT complete.
2. **Targeted Re-Test:**
   - After modifying Page Classes, check impacted Test Cases with:
     ```bash
     python3 tools/test_impact.py --git-diff
     ```
   - Verify the affected test cases pass before handoff.
3. **Synchronize Knowledge Graph & Repo Map:**
   - Run `graphify update .` to keep the AST knowledge graph updated.
   - Run `python3 tools/repo_map.py` if any Page Class or Helper was modified.

---

## 3. Situational Tool Dispatch Matrix & Zero-Command Autonomy

> 🚀 **Zero-Command Autonomous Invariant:** The user **NEVER** needs to manually type tool commands. The AI Agent **MUST AUTONOMOUSLY recognize context and trigger** the corresponding tools on-demand. Never run tools blindly; invoke only when the concrete situation arises.

- **Setup & Audit:** New project -> `tools/setup_project.py`; Project audit -> `tools/analyze_project.py`; Code review -> `tools/senior_code_review.py`; Debt scan -> `tools/debt_harvester.py`.
- **Quality Gates & DoD:** Pre-commit/Handoff -> `tools/verify_all.py` (10 Gates DoD); Script lint -> `tools/infer_linter.py`; Mutation testing -> `tools/micro_mutator.py --min-score 80`.
- **Failure Autopsy & Healing:** Test failure -> `tools/pinpoint_failure.py` (parse JUnit XML in 0.1s); Iterative repair -> `tools/auto_heal_reflexion.py`; Reversible rollback -> `tools/reversible_sandbox.py`.
- **Context & Safety:** Verbose logs -> `tools/distill_log.py`; Destructive browser actions -> `tools/safety_firewall.py`; Method signatures -> `tools/repo_map.txt`.
- **Memory & Reflexion:** UI exceptions -> `tools/cache_resolver.py query "<error>"`; Query/Save proven patterns -> `tools/skill_vault.py`.

*(For the complete CLI parameters and full tools catalog, refer to [tools/TOOLS_RUNBOOK.md](file://tools/TOOLS_RUNBOOK.md)).*

---

## 4. Cognitive Forcing Functions (Structured Reasoning Pipeline)

> **Core Principle:** Autocomplete mode generates weak, tautological tests. Before outputting any test script, Universal IR, or Page Class, the agent **MUST** pass through a 4-step System-2 reasoning pipeline:

```markdown
<reasoning_protocol>
Step 1 - Boundary & Invariant Extraction: Define system invariants. What must strictly NEVER happen under any circumstances?
Step 2 - Falsification Hypotheses (Popper's Falsification): Propose 3 realistic scenarios where a developer could break functionality while conventional tests still pass (False Negatives).
Step 3 - Self-Debate: Explain why the proposed assertion will catch and fail all 3 destructive scenarios in Step 2.
Step 4 - Emit Code / Universal IR: Only synthesize code once the 3 steps above are completed.
</reasoning_protocol>
```

---

## 5. Adversarial Self-Play: Red-Team vs Blue-Team

- **Agent Blue (`pom-crafter`):** Synthesizes Clean POM code and defensive assertions.
- **Agent Red (`failure-analyst`):** Acts as the rogue developer, actively injecting AST mutants via `tools/micro_mutator.py` into source/mocks.
- **Evaluation Loop:**
  - If Blue's tests let mutants survive (Mutation Score $< 80\%$), Red-Team **REJECTS** the code and commands Blue to strengthen assertions.
  - Test suites are only Approved when Mutation Score reaches $\ge 80\%$.
