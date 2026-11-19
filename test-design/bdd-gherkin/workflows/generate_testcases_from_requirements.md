---
description: Rapid single-pass generation of structured test cases from requirements.
skills:
  - rbt-manual-testing
---

# /generate_testcases_from_requirements — Rapid Single-Pass Test Generation

Generates structured test cases in a single pass without pausing for multi-stage checkpoints. Best for isolated forms, standalone dialogs, or well-defined user stories.

## Workflow Pipeline

1. **Ingest Requirements & Boundary Mapping:** Read the provided requirement text, user story, or acceptance criteria. Map Happy Paths, Negative Paths, Boundary Conditions, and Edge Cases.
2. **Mandatory Ambiguity Checkpoint & Assumptions Log:** Scan requirements for ambiguities, omissions, unspecified boundary lengths, undefined error messages, missing timeouts, and implicit system assumptions. Format and emit a dedicated `## Ambiguity & Assumptions Log` table (`ID | Requirement Reference / Statement | Ambiguity / Gap Detected | Working Assumption / Resolution | Impact / Risk`). If critical blocking contradictions exist, halt and query the user.
3. **Test Design Techniques Application:** Apply Equivalence Partitioning (EP), 2-value/3-value Boundary Value Analysis (BVA), Decision Tables, and State Transition models.
4. **Field-Level Validation (25-Field Validation Checklist):** Identify all form input fields and apply the **25-Field Validation Checklist** referencing `rbt-manual-testing` (`references/field_validation_checklist.md`), covering:
   - 1. Text • 2. Email • 3. Phone • 4. Password • 5. Number • 6. Date • 7. Date Range • 8. Dropdown • 9. Multi-Select • 10. Checkbox/Radio • 11. Textarea • 12. File Upload • 13. OTP/MFA • 14. Range Slider • 15. Rich Text Editor • 16. Geo Location & Address Autocomplete • 17. Digital Signature Pad (Canvas) • 18. Biometric / WebAuthn • 19. Camera / Barcode / QR Scanner • 20. Currency & FX (Multi-Currency & Dynamic FX) • 21. Credit Card / IBAN / Masked Input • 22. Async Autocomplete / Typeahead • 23. Cron Expression & Recurring Schedule • 24. JSON / Code / Formula Editor • 25. Inline Editable Data Grid.
5. **Standard 12-Column Output & Metadata Export:** Emit complete test cases formatted in the standard 12-column Markdown table conforming to ISO/IEC/IEEE 29119-3 with automation metadata (`Automatable`, `Auto Type`, `@Tags`) and include the mandatory `## Ambiguity & Assumptions Log` section.
6. **Excel Export Command:** Recommend the user convert the markdown table to Excel via:
   ```bash
   agent-qa export-excel path/to/cases.md -o cases.xlsx
   ```
