# Pocock Grilling Spec Review & Decision-Frontier Rubric

> **Paradigm Attribution:** Inspired by **Pocock Grilling Primitive** — resolves ambiguous story requirements upfront through structured, multiple-choice decision frontiers with recommended defaults, preventing code rework.

---

## 1. The 5-Vector Completeness Review

Before handing any user story to `pom-crafter`, `review-spec` audits:

1. **State Invariants:** What state must NEVER exist under any circumstance?
2. **Boundary Values:** Are 0, max limits, empty inputs, and special characters defined?
3. **Async / Timing Bounds:** What is the maximum timeout before fallback UI displays?
4. **Error UX & Feedback:** Are exact toast messages, HTTP codes, and retry buttons specified?
5. **Data Cleanup (Teardown):** Is there an automated deletion or rollback strategy?

---

## 2. Decision-Frontier Interview Matrix

When requirements are underspecified, trigger `tools/interview_story.py` with batched choices:

```markdown
### Decision Frontier 1: Concurrent Session Handling
- [x] (Recommended) Invalidate older session and notify user with dismissible banner.
- [ ] Allow concurrent multi-tab browsing without state sharing.
- [ ] Block new login until active session logs out.

### Decision Frontier 2: Payment Gateway 3DS Timeout
- [x] (Recommended) Auto-poll transaction status for 60s, then display manual status check button.
- [ ] Immediately fail order after 30s and restore cart items.
```

---

## 3. Spec Approval Gate

A test specification is approved for code synthesis ONLY when:
- All 5 completeness vectors score $\ge 80\%$.
- Zero unresolved decision frontiers remain.
