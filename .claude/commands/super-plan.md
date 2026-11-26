<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/core/sync_agent_rules.py                                     -->
<!-- [CACHE-ANCHOR: ROOT-PREFIX-v4.8]                                               -->
<!-- ============================================================================== -->

# /super-plan — Spec-Driven Planning Pipeline (v2.0)

> **Attribution:** Synapse Hub by Thế Vị (@TeeVee98) | MIT License
> **Canonical Skill:** `.agent/skills/super-plan/SKILL.md`
> **Unified CLI:** `agent-qa super-plan` (or `python3 tools/design/super_plan_engine.py`)

## Workflow Steps
1. **Risk-Routing & AST Grounding:** Read target files and run `agent-qa super-plan route --task "<task>" --files <files...> --json`.
2. **Ambiguity Gate:** Run `agent-qa super-plan ambiguity-check --task "<task>" --json` and resolve architectural forks before drafting.
3. **Execution DAG & Typed Manifests:** Generate `implementation_plan.md` with `<= 3`-file atomic milestones, `depends_on`, `Write Set`, `Rollback Hook`, and `Pass Gate`. Default execution mode is Single-Agent sequential `/solo` (no `swarm` workers unless `/teamwork` is explicitly requested).
4. **Mechanical Validation & 12-Mutant Red-Teaming:** Run `agent-qa lint-plan --file implementation_plan.md --mode super` and `agent-qa plan-mutate --file implementation_plan.md --threshold 90.0`.
5. **Clean Handoff:** Hand off `implementation_plan.md` to `/solo` (`agent-qa solo --from-plan implementation_plan.md`).
