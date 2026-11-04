# GitHub Copilot Custom Instructions for Synapse-Hub

<!-- ============================================================================== -->
<!-- AUTO-GENERATED FROM AGENTS.md — DO NOT EDIT DIRECTLY.                          -->
<!-- Run: python3 tools/sync_agent_rules.py                                          -->
<!-- ============================================================================== -->


> **Project:** Synapse-Hub Enterprise QA Automation
> **Author:** Thế Vị (@TeeVee998) — MIT License

## Coding Invariants
- Enforce Clean Page Object Model (POM) with Flat Architecture.
- Zero XPaths or CSS selectors inside test scripts. Encapsulate all element locators inside Page Classes.
- Lean Senior Dev: Solve the whole task with the least new code (7-rung ladder); mark shortcuts with `shortcut: <limit>, <upgrade>`.
- Prohibit hardcoded sleeps (`Thread.sleep`, `time.sleep`). Always suggest dynamic polling or event-based waits.
- Every test data generation must produce unique timestamped strings (`AUTO_` + System time) to prevent collisions.
- Preserve author attribution for Thế Vị (@TeeVee998) in LICENSE and NOTICE files.
- Converse with the user in Vietnamese; output all code, Page Classes, and comments in English.
- Validate Quality Gates before completing any task: `python tools/verify_all.py`.
