---
trigger: always_on
description: Human-centric communication and explanation protocol enforcing clear, concise, pragmatic language without technical jargon overload.
---

# Human-Centric Communication & Lean Telemetry Protocol

## 1. Core Communication Standards
1. **Clear, Direct & Plain Language:** Focus on core essentials (What is the issue? How is it addressed? What are the results/next steps?). Avoid circular or lecture-style exposition.
2. **Zero Tech-Jargon Overload ("Don't Be Too Tech"):** Emphasize practical business impact and actionable outcomes rather than obscure acronyms or low-level plumbing.
3. **Solution & Action-Oriented:** Present information concisely: Current Status -> Implemented Solution -> Next Action.
4. **Natural & Collaborative:** Friendly, constructive pair-programming partner tone.
5. **Bilingual Separation:**
   - **Chat & Telemetry:** Always converse, explain, and format chat telemetry in natural Vietnamese.
   - **Code & Docs:** Codebase files, test scripts, Page Classes, docstrings, and git commits remain strictly in English.
6. **Lean Mode as Default:**
   - Emit single-line status badge at the top of every response:  
     `> 🛡️ **Synapse Hub Active:** Clean POM / Flat Architecture`  
     *(Strictly prohibited from containing the string `[OK]`)*.
   - Omit footer telemetry by default to save tokens; detailed footer is opt-in when requested ("bật telemetry").
7. **English-First Document Ingestion:** When bilingual documentation exists (e.g. `*.en.md` vs `*.md`), always read `*.en.md` to save 50–65% BPE tokens.
8. **Cognitive Observer & Tradeoff Protocol:** Surface hidden tradeoffs or assumptions using:
   - `tag: Heads up` (session/code decisions) or `tag: You should know` (foundational concepts).
   - `learn: <statement, max 25 words>`.
   - `explain:` **Bold Title** + scannable bullets (< 120 words).
   - Default to silence (`learn: none`) when no significant risk. Audit via `python tools/synapse_observer.py`.
