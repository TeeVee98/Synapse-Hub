---
name: security-dast-sentinel
description: "Run dynamic security audits: OWASP Top 10, security headers, BOLA/IDOR, and token leakage. Use when running or planning DAST and security scans against a target app."
category: verification_and_resilience
version: "1.0.0"
policies:
  network: sandbox-only
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Security DAST Sentinel & Enterprise Security Audit Harness

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Run dynamic security audits: OWASP Top 10, security headers, BOLA/IDOR, and token leakage. Use when running or planning DAST and security scans against a target app.
- **Activation Scope:** Domain workflows for `05-security-and-compliance` involving `security-dast-sentinel`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT perform destructive DAST fuzzing or injection against unapproved production endpoints.
- Do NOT bypass the 5-layer authorization and consent guardrails.
- Do NOT report false-positive vulnerability warnings without verifying reproducible evidence.
- **Sibling Skill Boundaries:**
  - skillspector-security-guard audits skill and script security; security-dast-sentinel conducts dynamic application security testing (OWASP Top 10).

---

## 3. Ordered Execution Workflow

> **Purpose:** Automated Dynamic Application Security Testing (DAST), defensive runtime verification, and mathematical security audit orchestration across enterprise web applications, APIs, and AI agent swarms. Bridges functional automated testing with OWASP Top 10 compliance gates and Cloudflare 6-Phase audit rigor.
>
> [!IMPORTANT] Authorization & Scope of Engagement
> Dynamic security testing and fuzzing must **ONLY** be conducted against environments, domains, and applications for which explicit written authorization and testing agreements are established. Never direct automated security payloads or fuzzers against third-party production infrastructure.

---

### 6-Phase Security Audit FSM (Cloudflare Enterprise Pattern)

<!-- classification: illustrative -->
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
<!-- classification: illustrative -->
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
<!-- classification: illustrative -->
```bash
   python tools/security_coverage_ledger.py validate coverage-ledger.json
```
6. **Phase 6: Target-Neutral Reporting**:
   Generate mathematical metrics and final risk summaries:
<!-- classification: illustrative -->
```bash
   python tools/security_coverage_ledger.py summary coverage-ledger.json
```

---

### Core Defensive Scope & OWASP Top 10

| OWASP Category | Threat Vector | Automated Defensive Check | Assertion Target |
| :--- | :--- | :--- | :--- |
| **A01: Broken Access Control** | BOLA / IDOR | Swapping User A token into User B resource URI | HTTP `403` or `404` (Never `200`) |
| **A01: Broken Access Control** | CORS Misconfiguration | Sending untrusted `Origin` with `Credentials: include` | Must NOT reflect origin with `Credentials: true` |
| **A02: Cryptographic Failures** | Missing HSTS | Inspecting headers on HTTPS endpoints | `Strict-Transport-Security: max-age=...` |
| **A05: Security Misconfiguration** | Missing Security Headers | Passive audit on page navigations & API responses | CSP, X-Frame-Options, nosniff |
| **A05: Security Misconfiguration** | Verbose Error Disclosure | Fuzzing invalid inputs to trigger errors | Response must NOT contain `SQLException` or stacktrace |
| **A09: Logging & Secrets Leak** | Sensitive Data Leakage | Regex scan on responses and local storage | Zero plaintext passwords, API keys, or private keys |

---

### Automated Security Headers Audit

Automated DAST verification enforces mandatory HTTP security headers (`Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`) to prevent clickjacking, MIME sniffing, and insecure transport.

👉 **Executable Recipes:** Full Playwright TypeScript test cases are maintained in [**DAST Recipes (`references/dast_recipes.ts`)**](references/dast_recipes.ts).

---

### BOLA / IDOR Defense Check

Automated cross-tenant authorization checks verify that Tenant B cannot access Tenant A resources (returning `403` or `404`, never `200`).

👉 **Executable Recipes:** Full Playwright TypeScript test cases are maintained in [**DAST Recipes (`references/dast_recipes.ts`)**](references/dast_recipes.ts).

---

### Environment Allowlist Guard

- Automated security checks, fuzzing (`tools/api_fuzzer.py`), and DB sandboxing (`tools/db_sandbox.py`) enforce non-production allowlists (`localhost`, `staging`, `dev`, `qa`, `sandbox`).
- Fuzzing production hosts without `SYNAPSE_ALLOW_PROD_FUZZ=1` is automatically blocked.

---

### Passive vs Active Scan Taxonomy & Severity Levels

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

### AI, LLM & Agentic Security Hardening (Cloudflare Defense Pattern)

For systems with integrated LLMs, tool-calling agents, or MCP servers, inspect:
- [**Attack Classes Taxonomy (`references/ATTACK-CLASSES.md`)**](references/ATTACK-CLASSES.md): Core vulnerability categories across Injection, Access Control, File Handling, Cryptography, Business Logic, and Feature Abuse.
- [**AI & Agent Security Hunting Guide (`references/AI-AND-LLM.md`)**](references/AI-AND-LLM.md): Auditing indirect injection, persistent memory poisoning, tool-argument downstream sink execution, confused-deputy authorization, tool-schema disagreement, unbounded action loops, and MCP identity confusion.

---

## 4. Verification Points & DoD

1. Target endpoints verified against authorization whitelist and consent grant.
2. Security scan covers OWASP Top 10 vulnerabilities (SQLi, XSS, SSRF, broken auth, security headers).
3. Findings categorized by CVSS severity with reproduction steps and remediation guidance.

---

## 5. Handoff Protocol

- **Deliverables:** DAST vulnerability audit reports, security header scorecards, and reproduction curl commands.
- **Next Subagent:** quality-gatekeeper
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
