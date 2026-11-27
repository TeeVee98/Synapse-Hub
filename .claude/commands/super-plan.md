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
1. **Risk-Routing, Slugged Path & Worktree Check:** Read target files and run `agent-qa super-plan route --task "<task>" --files <files...> --json` to get a collision-free `suggested_plan_path` (`.synapse/plans/<slug>.md`). If `concurrency_status == "CONCURRENT_SESSION_DETECTED"`, isolate into a worktree via `agent-qa worktree create --agent-id <slug> --plan <plan_path>` before editing code.
2. **Ambiguity Gate:** Run `agent-qa super-plan ambiguity-check --task "<task>" --json` and resolve architectural forks before drafting.
3. **Execution DAG & Typed Manifests:** Export to the unique `.synapse/plans/<slug>.md` (`--output auto`) with `<= 3`-file atomic milestones, `depends_on`, `Write Set`, `Rollback Hook`, and `Pass Gate`. Default execution mode is Single-Agent sequential `/solo` (no `swarm` workers unless `/teamwork` is explicitly requested).
4. **Mechanical Validation & 12-Mutant Red-Teaming:** Run `agent-qa lint-plan --file <plan_path> --mode super` and `agent-qa plan-mutate --file <plan_path> --threshold 90.0`.
5. **Clean Handoff & Post-DoD Cleanup:** Hand off `<plan_path>` to `/solo` (`agent-qa solo --from-plan <plan_path>`), and remove the finished `.synapse/plans/<slug>.md` draft (plus any ephemeral worktree) after DoD harvest.
