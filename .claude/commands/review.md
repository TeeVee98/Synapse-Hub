<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- [CACHE-ANCHOR: ROOT-PREFIX-v4.8]                                               -->
<!-- ============================================================================== -->

# /review — Closed-Loop Post-Code Adversarial Reviewer (v2.0)

> **Attribution:** Synapse Hub by Thế Vị (@TeeVee98) | MIT License
> **Canonical Skill:** `.agent/skills/review/SKILL.md`
> **Unified CLI:** `agent-qa review` (or `python3 tools/orchestration/senior_code_review.py`)

## Strict Read-Only Diagnostic Boundary
- Operate strictly in read-only DIAGNOSTIC mode. Never auto-edit user source code or tests during `/review`.
- Re-verify HMAC signatures, post-Red `test_tree_hash`, AST contracts, and downstream callers directly from disk truth.

## Workflow Steps
1. **Plan-vs-Solo Closed-Loop Audit:** Reconcile diffs and `/solo` forensic receipts against the approved Super-Plan:
   `agent-qa review --plan implementation_plan.md --strict-solo --json`
2. **Milestone-Scoped Audit:** Scope reconciliation to a single milestone write set and receipt:
   `agent-qa review --plan implementation_plan.md --milestone M1 --strict --json`
3. **Ad-Hoc Diff / PR Review (6-Pillar AST + 4-Angle `simplify`):**
   `agent-qa review --staged` (or `agent-qa review --branch main --output-md reports/code_review.md --verify-cove`)
4. **Verdict & Signed Receipt:** Inspect `reports/code_review_receipt.json` (`APPROVED` / `APPROVED_WITH_NOTES` / `CHANGES_REQUESTED`) and hand any `Must fix` blockers back to `/solo`.
