---
type: decision-log
project: Synapse-Hub
updated_at: '2026-11-24T10:47:57.701671'
total_decisions: 1
tags: [decisions, pkm, synapse-hub, architecture]
---

# Architectural Decision Journal (Obsidian PKM View)

> **Notice:** This view is compiled from the immutable `docs/decisions.jsonl` ledger.
> For human and team knowledge synthesis. AI agents query raw `.jsonl` directly to conserve token budget.

## Related Context Links
- [[PROJECT_STATE]] — Active session state anchor
- [[docs/INVARIANTS]] — Universal operating standards & rules
- [[docs/adr/README]] — Formal Architectural Decision Records

---

## Decision History

### dec-1 — 2026-11-24 10:47:38
> [!NOTE] Adopt Append-Only Decision Ledger & Fast Search
> - **Why:** Ensure zero-token decision traceability and provenance
> - **Cost if wrong:** Minimal I/O overhead on record_decision
> - **Scope:** `general` | **Author:** `agent` 

