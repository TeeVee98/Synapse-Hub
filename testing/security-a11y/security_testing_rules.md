---
trigger: on_demand
description: Mandatory 5-layer safety gate and invariants for DAST, fuzzing, and security testing enforced via PentestScopeGuard.
profiles: [api-security, full]
---

# Security & Pentest Testing Invariants (5-Layer Safety Gate)

> Mandatory enforcement rule when executing security testing, DAST, or vulnerability scanning in Synapse-Hub.  
> **Runtime Enforcement Engine:** Layers 1 & 2 are strictly governed and enforced via `tools/pentest_scope_guard.py` (`PentestScopeGuard`).

## 1. Layer 1 — Scope & Production Blocklist (Allowlist Gate)
* All DAST/Fuzzing/Pentest scripts (Burp Suite, OWASP ZAP, Nuclei, Python) must integrate `PentestScopeGuard` (`tools/pentest_scope_guard.py`), read `TARGET_BASE_URL`, and verify that it strictly matches `ALLOWED_PENTEST_HOSTS`.
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

## Layer 6 — Security Test Case, Web Client-Side & Mobile MASVS (Gap Add-on)

### A. Negative Security Test Case Design (OWASP ASVS & API Top 10)
Khi sinh test case cho tính năng có Auth/API/Giao dịch, bổ sung nhóm `TC_SEC_XXX`:
- **Mass Assignment (API3 BOPLA):** Gửi thừa field nhạy cảm (`role`, `isVerified`, `discount`) trong payload `POST/PUT/PATCH`. Expected: Server bỏ qua hoặc reject `400/422`.
- **Business Logic & Rate Limit (API4 / API6):** Spam OTP/Login vượt ngưỡng, gửi số lượng/giá âm, áp mã giảm giá nhiều lần, hoặc bỏ qua bước xác thực ở luồng nhiều bước.

### B. Web Client-Side & Supply Chain (OWASP WSTG)
- **Session & Storage:** Kiểm tra JWT/Session không lưu plain-text trong `localStorage`/`sessionStorage`; Cookie phiên bật đủ `HttpOnly`, `Secure`, `SameSite=Lax/Strict`.
- **DOM XSS & Open Redirect:** Kiểm tra output encoding bằng canary DOM-XSS probe vô hại ở URL hash/query params và xác minh redirect URL (`?next=...`) bị chặn ngoài allowlist.
- **File Upload Bypass:** Kiểm tra upload file giả mạo MIME type hoặc double extension.
- **Supply Chain (SCA):** Chạy `npm audit` / `pip-audit` trong CI; chặn build nếu có CVE Critical/High chưa vá.

### C. Mobile App Security (OWASP MASVS & MASTG)
- **MASVS-STORAGE:** SharedPreferences / UserDefaults / SQLite / Cache / Logcat không lưu token, password, PII dạng clear-text (bắt buộc dùng Android Keystore / iOS Keychain).
- **MASVS-NETWORK:** Chặn HTTP clear-text (`cleartextTrafficPermitted=false`); kiểm tra **SSL/TLS Certificate Pinning** bằng proxy — app phải từ chối kết nối khi cert không hợp lệ.
- **MASVS-PLATFORM:** Kiểm tra **Deep Link / URL Scheme** không mở màn hình nội bộ trái phép; tắt JS interface dư thừa và vô hiệu hóa truy cập file cục bộ trong WebView.
- **MASVS-RESILIENCE:** Kiểm tra hành vi app trên thiết bị **Root/Jailbreak** hoặc khi gắn debugger/Frida; che màn hình nhạy cảm khi app xuống background.
