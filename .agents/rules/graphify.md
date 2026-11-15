---
trigger: on_demand
description: Consult the graphify knowledge graph at graphify-out/ for codebase and architecture questions (target spoke projects only).
---

# Graphify Knowledge Graph Protocol

> ⚠️ **Hub vs Spoke Boundary:** Graphify directives apply strictly to target client projects containing `graphify-out/`. Graphify CLI commands must **never** be executed on the Synapse Hub workspace (Anti-Pattern Rule 7).

When `graphify-out/graph.json` exists in target project:
- **Query Scoped Subgraph:** Run `graphify query "<question>"` (CLI) or `query_graph` (MCP). Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- **Navigate Wiki:** If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files.
- **Architecture Overview:** Read `graphify-out/GRAPH_REPORT.md` only for broad architecture reviews.
- **Sync AST:** After modifying code files in target project, run `graphify update .` to keep graph current.
