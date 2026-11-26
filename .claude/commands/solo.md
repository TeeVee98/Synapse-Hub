<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- [CACHE-ANCHOR: ROOT-PREFIX-v4.8]                                               -->
<!-- ============================================================================== -->

# /solo — Single-Agent 4-Pillar Verification Loop (v2.0)

> **Attribution:** Synapse Hub by Thế Vị (@TeeVee98) | MIT License
> **Canonical Skill:** `.agent/skills/solo/SKILL.md`
> **Unified CLI:** `agent-qa solo` (or `python3 tools/orchestration/solo_runner.py`)

## Strict Single-Agent Execution Boundary
- Execute milestones sequentially (`M1 -> M2 -> ...`) within one active session (`Red -> Blue -> Purple`).
- Strictly FORBIDDEN to spawn `swarm` workers or parallel subagents unless the user explicitly invokes `/teamwork`.

## Workflow Steps
1. **Pre-Execution 3-Line Contract:** State Goal, Won't Do, and Done When.
2. **Phase 1 (Red QA):** Write 4-scenario failing tests and certify:
   `agent-qa solo --red --milestone M1 --require-four-scenarios --test-cmd "python3 -m pytest tests/<target>.py"`
   (Use `--recertify-red` when updating Red tests with cryptographic lineage.)
3. **Phase 2 (Blue Dev):** Implement minimal complete code without weakening Red assertions and certify:
   `agent-qa solo --green --milestone M1 --test-cmd "python3 -m pytest tests/<target>.py"`
4. **Phase 3 (Purple Auditor):** Run live mutation (`>= 80%`) and Purple audit (standalone `--purple` auto-runs `/review --strict-solo`; pass `--milestone <ID>` for milestone receipts or `--no-review` to opt out):
   `agent-qa solo --mutation --target <source.py> --test-cmd "python3 -m pytest tests/<target>.py" --threshold 80.0`
   `agent-qa solo --purple --json`
5. **Closed-Loop Plan Execution & Auto-`/review`:** Execute validated plan DAGs end-to-end with Scope Guard, `decisions.tsv`, and automatic post-`/solo` `/review` reconciliation (`--no-review` to opt out):
   `agent-qa solo --from-plan implementation_plan.md --json`
6. **Phase 4 (Automatic `/review` Handoff):** After standalone `/solo` finishes Phase 3, `solo_runner.py --purple` automatically runs `/review --strict-solo` (pass `--milestone <ID>` for milestone receipts, or `--no-review` at CLI to opt out); when invoking `/review` directly in standalone mode, run `agent-qa review --plan <plan.md> --strict-solo --json` or `agent-qa review --staged --strict-solo --json` (add `--milestone <ID>` if using milestone receipts) before reporting done.
