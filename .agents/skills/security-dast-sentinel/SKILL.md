---
name: security-dast-sentinel
description: "Run dynamic security audits: OWASP Top 10, security headers, IDOR, and token leakage. Use when running or planning DAST and security scans against a target app."
---

# Security DAST Sentinel & Enterprise Security Audit Harness

> **Purpose:** Automated Dynamic Application Security Testing (DAST), defensive runtime verification, and mathematical security audit orchestration across enterprise web applications, APIs, and AI agent swarms. Bridges functional automated testing with OWASP Top 10 compliance gates and Cloudflare 6-Phase audit rigor.
>
> [!IMPORTANT] Authorization & Scope of Engagement
> Dynamic security testing and fuzzing must **ONLY** be conducted against environments, domains, and applications for which explicit written authorization and testing agreements are established. Never direct automated security payloads or fuzzers against third-party production infrastructure.

---

## 0. 6-Phase Security Audit FSM (Cloudflare Enterprise Pattern)

```text
Phase 1: Reconnaissance ──► Phase 2: Hunting Waves ──► Phase 3: Candidate Validation
         │                            │                               │
         ▼                            ▼                               ▼
  Coverage Ledger               Attack Classes                 Local Proof / POC
 (tools/security_coverage_ledger) (ATTACK-CLASSES.md)          (Zero Fake Passes)
         │                            │                               │
         ▼                            ▼                               ▼
Phase 6: Reporting      ◄── Phase 5: Verification  ◄── Phase 4: Structured Findings
```

1. **Phase 1: Reconnaissance & Attack Surface Mapping**:
   Enumerate attack surface boundaries, components, and subsystems:
   `Coverage Unit = Surface × Boundary × Subsystem × Attack Class [× Lifecycle]`
   Initialize and track mathematical coverage via `tools/security_coverage_ledger.py`:
   ```bash
   python tools/security_coverage_ledger.py init -f coverage-ledger.json
   python tools/security_coverage_ledger.py add -f coverage-ledger.json -s "web_api" -b "auth" --subsystem "billing" -a "idor"
   ```
2. **Phase 2: Coverage-Led Hunting Waves**:
   Organize hunting into structured waves (Wave 1: core boundaries, Wave 2: integrations, Wave 3: edge cases). Refer to [**Attack Classes Taxonomy (`references/ATTACK-CLASSES.md`)**](references/ATTACK-CLASSES.md).
3. **Phase 3: Candidate Validation**:
   Validate candidates through bounded local checks and source AST analysis. Never report a candidate without proving the broken code boundary and observable unauthorized consequence.
4. **Phase 4: Structured Findings Output**:
   Record findings in structured formats: `confirmed` (complete local proof), `needs_validation` (unobservable deployment/cloud configuration), or `rejected`.
5. **Phase 5: Record Verification**:
   Verify coverage state invariants: ensure every covered unit has assigned agent ownership, reviewed file paths, and local assertions.
   ```bash
   python tools/security_coverage_ledger.py validate coverage-ledger.json
   ```
6. **Phase 6: Target-Neutral Reporting**:
   Generate mathematical metrics and final risk summaries:
   ```bash
   python tools/security_coverage_ledger.py summary coverage-ledger.json
   ```

---

## 1. Core Defensive Scope & OWASP Top 10

| OWASP Category | Threat Vector | Automated Defensive Check | Assertion Target |
| :--- | :--- | :--- | :--- |
| **A01: Broken Access Control** | BOLA / IDOR | Swapping User A token into User B resource URI | HTTP `403` or `404` (Never `200`) |
| **A01: Broken Access Control** | CORS Misconfiguration | Sending untrusted `Origin` with `Credentials: include` | Must NOT reflect origin with `Credentials: true` |
| **A02: Cryptographic Failures** | Missing HSTS | Inspecting headers on HTTPS endpoints | `Strict-Transport-Security: max-age=...` |
| **A05: Security Misconfiguration** | Missing Security Headers | Passive audit on page navigations & API responses | CSP, X-Frame-Options, nosniff |
| **A05: Security Misconfiguration** | Verbose Error Disclosure | Fuzzing invalid inputs to trigger errors | Response must NOT contain `SQLException` or stacktrace |
| **A09: Logging & Secrets Leak** | Sensitive Data Leakage | Regex scan on responses and local storage | Zero plaintext passwords, API keys, or private keys |

---

## 2. Automated Security Headers Audit (Playwright TypeScript)

```typescript
import { test, expect } from '@playwright/test';

test('DAST: Verify mandatory HTTP security headers', async ({ page }) => {
  const response = await page.goto('/dashboard');
  expect(response).not.toBeNull();
  const headers = response!.headers();

  // 1. Clickjacking & MIME Sniffing
  expect(['DENY', 'SAMEORIGIN']).toContain(headers['x-frame-options']?.toUpperCase());
  expect(headers['x-content-type-options']).toBe('nosniff');

  // 2. Strict Transport Security & CSP
  if (page.url().startsWith('https://')) {
    expect(headers['strict-transport-security']).toContain('max-age=');
  }
  expect(headers['content-security-policy']).toBeTruthy();
});
```

---

## 3. BOLA / IDOR Defense Check

```typescript
test('DAST: Tenant B cannot access Tenant A entity', async ({ request }) => {
  // Tenant B attempts to read Tenant A resource
  const readAttempt = await request.get('/api/v1/invoices/10042', {
    headers: { 'Authorization': `Bearer ${tokenTenantB}` }
  });
  expect([403, 404], 'Cross-tenant resource must be forbidden').toContain(readAttempt.status());
});
```

---

## 4. Environment Allowlist Guard

- Automated security checks, fuzzing (`tools/api_fuzzer.py`), and DB sandboxing (`tools/db_sandbox.py`) enforce non-production allowlists (`localhost`, `staging`, `dev`, `qa`, `sandbox`).
- Fuzzing production hosts without `SYNAPSE_ALLOW_PROD_FUZZ=1` is automatically blocked.

---

## 5. Passive vs Active Scan Taxonomy & Severity Levels

> *Adapted from the OWASP ZAP scanning model (Apache-2.0, zaproxy/zaproxy).*

Structure every DAST engagement in two phases, and severity-tag every finding
so CI can gate on risk instead of raw counts:

| Phase | Traffic | Purpose | Hub Tooling |
| :--- | :--- | :--- | :--- |
| **Passive** | Zero traffic | Audit the OpenAPI/Swagger contract pre-flight: mutating endpoints without declared auth, unprotected admin paths, unbounded string props | `agent-qa fuzz-api --mode passive` |
| **Active** | Controlled attacks | Dispatch fuzz vectors against staging and evaluate the defect oracle | `agent-qa fuzz-api` (allowlist-guarded) |

Severity ladder: `CRITICAL` (stacktrace/DB leak, auth bypass) →
`HIGH` (server crash 5xx, unprotected sensitive path) → `MEDIUM` (connection
errors, unverified targets) → `LOW` (SLA breaches, unbounded input) → `INFO`.

Rules:
1. **Never skip passive** — a contract that leaks an admin route costs zero requests to find; active scan only after passive findings are triaged.
2. **Gate on CRITICAL alone** — a run with any CRITICAL alarm fails CI regardless of total counts.
3. **An untested endpoint must never PASS** — connection failures are `CONNECTION_ERROR` findings, not green results (Truth Anchor).
4. **OpenAPI-driven breadth** — ingest the spec (JSON) so every path/method is enumerated; combine with authentication scripts from `auth-session-and-cookie-manager` before active scanning.

---

## 6. AI, LLM & Agentic Security Hardening (Cloudflare Defense Pattern)

For systems with integrated LLMs, tool-calling agents, or MCP servers, inspect:
- [**Attack Classes Taxonomy (`references/ATTACK-CLASSES.md`)**](references/ATTACK-CLASSES.md): Core vulnerability categories across Injection, Access Control, File Handling, Cryptography, Business Logic, and Feature Abuse.
- [**AI & Agent Security Hunting Guide (`references/AI-AND-LLM.md`)**](references/AI-AND-LLM.md): Auditing indirect injection, persistent memory poisoning, tool-argument downstream sink execution, confused-deputy authorization, tool-schema disagreement, unbounded action loops, and MCP identity confusion.
