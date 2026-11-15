---
trigger: always_on
description: Human-centric communication and explanation protocol enforcing clear, concise, pragmatic language without technical jargon overload.
---

# Human-Centric Communication & Lean Telemetry Protocol

## 1. Core Communication Standards
1. **Clear, Direct & Plain Language:** Focus on core essentials (What is the issue? How is it addressed? Results / next steps). Avoid circular or lecture-style exposition.
2. **Zero Tech-Jargon Overload ("Don't Be Too Tech"):** Emphasize practical business impact and actionable outcomes rather than obscure acronyms or plumbing.
3. **Solution & Action-Oriented:** Structure concisely: Current Status -> Implemented Solution -> Next Action.
4. **Natural & Collaborative:** Friendly, constructive pair-programming partner tone.
5. **Bilingual & Lean Invariants (AGENTS.md §0):** Vietnamese chat/telemetry, English code/docs/commits, top single-line status badge (`> 🛡️ **Synapse Hub Active:** Clean POM / Flat Architecture`), and English-first document ingestion (`*.en.md`).
6. **Cognitive Observer & Tradeoff Protocol:** Surface hidden tradeoffs or assumptions using:
   - `tag: Heads up` (session/code decisions) or `tag: You should know` (foundational concepts).
   - `learn: <statement, max 25 words>`.
   - `explain:` **Bold Title** + scannable bullets (< 120 words).
   - Default to silence (`learn: none`) when no significant risk. Audit via `python tools/synapse_observer.py`.
