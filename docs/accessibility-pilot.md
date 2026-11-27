# Accessibility Pilot Protocol (Keyboard + Screen-Reader Supervision)

This document defines the release-candidate accessibility verification protocol pairing automated Playwright keyboard checks (`examples/playwright-crm-suite/tests/accessibility.spec.ts`) with supervised human screen-reader verification.

## 1. Scope & Governance Rule

- **Automated Gate:** `examples/playwright-crm-suite/tests/accessibility.spec.ts` runs against `chromium` on every CI release-candidate dispatch (`.github/workflows/ci_quality_gates.yml`) and emits `reports/a11y_receipt.json`.
- **Pending Support Rule:** Automated keyboard checks alone certify `automated_passed`. Any accessibility support claim **remains `pending`** until a human reviewer executes the supervised screen-reader checklist below and records `reader_version` + `human_reviewer` + `build_id`.

## 2. Critical Journeys & Supervised Screen-Reader Checklist

| Journey ID | Screen / POM | Keyboard Expectation | Supervised Screen-Reader Expectation | Reviewer Sign-Off |
| :--- | :--- | :--- | :--- | :--- |
| `keyboard-sign-in-and-validation` | `LoginPage` (`/admin/authentication`) | `Tab` cycles `Email -> Password -> Remember me -> Login`; `Enter` submits empty form & valid login without mouse | Screen reader announces `<label>` names (`Email Address`, `Password`), masked state, and `role="alert"` / `aria-live="assertive"` validation message on error | `[ ] Verified (VoiceOver/NVDA version + date + build)` |
| `customer-dialog-focus-restore` | `CustomerPage` (`/admin/clients` -> `#contact` dialog) | `Enter` opens modal dialog and moves focus into `First Name`; `Tab` reaches `Save` and `Close`; `Escape` dismisses dialog and restores focus to `New Contact` trigger | Screen reader announces `dialog`, modal title (`Add New Contact`), form field labels, and focus return context after dismissal | `[ ] Verified (VoiceOver/NVDA version + date + build)` |

## 3. Evidence Receipt Contract (`reports/a11y_receipt.json`)

Every pilot run uploads a structured receipt keyed by:

- `build_id`: Candidate commit SHA or explicit package build identifier
- `browser`: Playwright browser project (`chromium` for pilot baseline)
- `journeys`: Executed journey identifiers
- `reader_version`: Verified screen reader + OS version (e.g. `macOS VoiceOver 15.x` / `NVDA 2024.4`), or `pending-human-observation` if unsupervised
- `human_reviewer`: Named reviewer handle when supervised; `null` when unsupervised
- `human_evidence_status`: `verified` only when both `reader_version` and `human_reviewer` are recorded; otherwise `pending`
