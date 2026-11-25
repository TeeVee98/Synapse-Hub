---
trigger: on_demand
description: Mandatory 5-layer safety gate and invariants for DAST, fuzzing, and security testing enforced via PentestScopeGuard.
profiles: [api-security, full]
---

# Security & Pentest Testing Invariants (5-Layer Safety Gate)

> Mandatory enforcement rule when executing security testing, DAST, or vulnerability scanning in Synapse-Hub.  
> **Runtime Enforcement Engine:** Layers 1 & 2 are strictly governed and enforced via `tools/security/pentest_scope_guard.py` (`PentestScopeGuard`).

## 1. Layer 1 — Scope & Production Blocklist (Allowlist Gate)
* All DAST/Fuzzing/Pentest scripts (Burp Suite, OWASP ZAP, Nuclei, Python) must integrate `PentestScopeGuard` (`tools/security/pentest_scope_guard.py`), read `TARGET_BASE_URL`, and verify that it strictly matches `ALLOWED_PENTEST_HOSTS`.
* **Fail-Closed / Default-Deny Mechanism:** If `ALLOWED_PENTEST_HOSTS` is empty or undefined, all active scans are terminated immediately.
* **Immediate Rejection:** Instantly reject execution if the target URL resolves to a Production environment (`prod`, `live`, or official domains not explicitly present in `ALLOWED_PENTEST_HOSTS`), or points to AWS Metadata (`169.254.169.254`) / unauthorized RFC1918 internal IP ranges.
* All HTTP redirects (301/302) must be validated via `validate_redirect` to prevent SSRF bounce attacks.
* Explicit confirmation via `--confirm-pentest-scope` CLI flag or `PENTEST_CONSENT_ACKNOWLEDGED=1` environment variable is mandatory prior to initiating active scans. All verification events are recorded in the audit trail `.synapse/pentest_audit.log`.

## 2. Layer 2 — Rate-Limit & Concurrency Cap
* Enforced via `PentestRateLimiter`: Hard limit on request dispatch rate of maximum `5–10 req/s` and maximum `3–5` concurrent threads (except for dedicated, explicitly authorized rate-limit stress tests).
* Set `timeout <= 10s` for every HTTP request and automatically trip the Circuit Breaker to abort the script when consecutive `5xx` or `429` responses exceed threshold limits.

## 3. Layer 3 — Non-Destructive PoC & Account Isolation
* Use only harmless vulnerability demonstration payloads (e.g., safe read-only SQL injection, canary strings, bounded micro-delays). Strictly prohibit data mutation/deletion payloads (e.g., unconditional `DROP`, `DELETE`, `UPDATE`) or payloads inducing Denial of Service (DoS).
* Cross-authorization / access-control testing (BOLA/IDOR) must strictly utilize designated test account pairs (`PENTEST_USER_A`, `PENTEST_USER_B`), never accessing or modifying real user data.

## 4. Layer 4 — Script Secret Protection & SAST Check
* Strictly prohibit hardcoding target Auth Tokens, Session Cookies, or API Keys in pentest scripts; inject all secrets from `.env` (guaranteed excluded in `.gitignore`).
* Perform complementary static security reviews (e.g., wildcard `CORS *`, missing CSP/HSTS headers, exposed credentials) across source repositories when read access is granted.

## 5. Layer 5 — Sanitized Evidence Standard
* Every reported vulnerability must include: Severity (Critical / High / Medium / Low), reproducible HTTP Request/Response pairs (or verifiable `curl` commands), and concrete remediation guidance.
* Mandatory sanitization: Mask all JWTs, session cookies, passwords, API tokens, and PII before writing logs, generating summaries, or exporting artifacts.

## 6. Layer 6 — Security Test Case Design, Web Client-Side & Mobile MASVS

### A. Negative Security Test Case Design (OWASP ASVS & API Top 10)
When generating test cases for Auth, API, or transactional features, include `TC_SEC_XXX` scenarios covering:
- **Mass Assignment (API3 BOPLA):** Inject unauthorized privileged fields (`role`, `isVerified`, `discount`) into `POST/PUT/PATCH` payloads. Expected: Server ignores unmapped attributes or rejects with HTTP `400/422`.
- **Business Logic & Rate Limit (API4 / API6):** Exceed OTP/Login rate thresholds, submit negative quantities/prices, replay single-use coupons concurrently, or attempt step-skipping across multi-stage workflows.

### B. Web Client-Side & Supply Chain (OWASP WSTG)
- **Session & Storage:** Verify JWTs and session tokens are never stored in plaintext `localStorage`/`sessionStorage`; session cookies enforce `HttpOnly`, `Secure`, and `SameSite=Lax/Strict`.
- **DOM XSS & Open Redirect:** Verify output encoding with harmless canary DOM-XSS probes in URL hash/query params and confirm redirect parameters (`?next=...`) reject external non-allowlisted domains.
- **File Upload Bypass:** Test spoofed MIME types, polyglot headers, and double extensions (`.jpg.php`, `.svg` script payloads).
- **Supply Chain (SCA):** Run `npm audit` / `pip-audit` in CI and block builds on unpatched Critical/High CVEs.

### C. Mobile App Security (OWASP MASVS & MASTG)
- **MASVS-STORAGE:** Verify SharedPreferences, UserDefaults, SQLite, Cache, and Logcat store zero cleartext tokens, passwords, or PII (mandate Android Keystore / iOS Keychain).
- **MASVS-NETWORK:** Enforce `cleartextTrafficPermitted=false` and verify **SSL/TLS Certificate Pinning** via MITM proxy inspection — the app must reject untrusted certificates.
- **MASVS-PLATFORM:** Audit **Deep Links / URL Schemes** against unauthorized internal screen access; disable unused WebView JS bridges and local file access.
- **MASVS-RESILIENCE:** Verify tamper/debugger detection on **Rooted/Jailbroken** devices or Frida attachment, and mask sensitive screens when backgrounded.
