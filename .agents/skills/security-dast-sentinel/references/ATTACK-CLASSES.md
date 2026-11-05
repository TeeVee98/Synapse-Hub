<!--
SPDX-FileCopyrightText: Copyright (c) Cloudflare, Inc.
SPDX-License-Identifier: MIT
Adapted from cloudflare/security-audit-skill for Synapse-Hub Enterprise QA.
-->

# Core Attack Classes & Vulnerability Taxonomy

#### When to use this guide

Select attack classes relevant to the application type and architecture. Frame security audit work as finding, validating, fixing, and prioritizing vulnerabilities. Validation is strictly bounded to source review, AST inspection, local mock fixtures, and authorized headless execution. Never test availability against live production services or take destructive action.

Classification standard:
- `confirmed`: Source evidence and bounded local validation establish the complete trust boundary crossing and observable defect.
- `needs_validation`: A specific deployment, platform, provider, identity, or runtime fact is unavailable locally; state the exact missing fact and the owner-observed check needed to resolve it.

---

## 1. Injection
Trace untrusted input from entry point to dangerous sink:
- **Web apps & APIs**: SQL queries, HTML/DOM output, shell commands (`subprocess`, `exec`, `powershell`), template engines, file paths, HTTP redirects, unsafe deserialization.
- **Libraries & Page Classes**: Functions processing caller-supplied data without validation (buffer operations, parsers, XPath/CSS selector construction).
- **CLI tools & Hub Scripts**: Shell command construction, path traversal, environment variable interpolation.
- **Microservices**: Query construction, message serialization, log injection, LDAP/GraphQL/XPATH queries.
- **Client-side (Browser/JS)**: DOM XSS, prototype pollution, `postMessage`/origin trust, and insecure storage.

*Rule:* Trace both direct and indirect injection (e.g. data stored safely, then retrieved and passed into an unescaped sink by background workers or reporting modules).

---

## 2. Access Control & Authorization (BOLA / IDOR)
Verify that a caller cannot execute operations outside their explicit authority:
- **Missing Authorization**: Endpoints that authenticate a user but forget to check if they own or are permitted to access the specific target resource ID (BOLA/IDOR).
- **Permission Asymmetry**: Alternate paths or secondary endpoints (e.g. bulk export, batch update, mobile API) performing the same state change with weaker permission checks.
- **Request Parameter Override**: Body or query parameters (e.g. `tenant_id`, `role`, `is_admin`, `owner_id`) that override what the authorization middleware intended to restrict.
- **Multi-Tenant Isolation**: Ensuring every database query, cache key, and vector search includes hard tenant isolation filters.

---

## 3. Resource and File Handling
- **Path Traversal**: Reading or writing outside intended directories via `../`, encoded sequences (`%2e%2e%2f`), symlinks, or Windows device paths.
- **SSRF (Server-Side Request Forgery)**: Inducing backend services to fetch attacker-controlled URLs, bypassing firewalls to hit internal cloud metadata endpoints (e.g. AWS IMDS, GCP metadata), internal microservices, or loopback interfaces.
- **Unsafe Deserialization & Archive Extraction**: Python `pickle`, Java deserialization, YAML `unsafe_load`, zip slip during archive extraction.
- **File Race Conditions (TOCTOU)**: Time-of-check to time-of-use gaps between file permission verification and file reading/writing.

---

## 4. Cryptography and Secrets Hygiene
- **Weak Randomness**: Using non-cryptographic PRNGs (`random.random()`, `Math.random()`) for security-critical values (session tokens, reset nonces, UUIDs).
- **Exposed Secrets**: Hardcoded credentials, private keys, API keys, or plaintext passwords in git history, environment dumps, error responses, or test fixtures.
- **Broken Cryptographic Primitives**: Static IVs, ECB mode, broken hash algorithms (MD5/SHA1 for signatures), missing HMAC verification.
- **Timing Attacks**: Comparing sensitive tokens or HMACs with standard string equality (`==`) rather than constant-time comparison (`hmac.compare_digest`).

---

## 5. Business Logic & State Invariants
Hunt logic errors through manual AST and workflow analysis:
- **State Machine Violations**: Skipping intermediate checkout/verification steps, replaying completed flows, or partial rollback failures.
- **Concurrency & Race Conditions**: Check-then-act gaps producing double-spend, double-redemption, or lost updates.
- **Numeric & Quantity Tampering**: Negative quantities, zero values, integer overflow, precision loss, currency rounding exploitation.
- **Default & Fallback Insecurity**: System security posture when configuration is missing, feature flags are off, or external identity providers time out.

---

## 6. Feature Abuse & Data Exfiltration
Legitimate enterprise features turned into exfiltration or injection channels:
- **Export & Backup Exfiltration**: Low-privilege accounts triggering full database exports, tenant snapshots, or audit log dumps containing sensitive PII.
- **Import & Restore Injection**: Bulk CSV/Excel/JSON imports that bypass field validation, overwrite existing IDs, or trigger blind formula injection (`=cmd|' /C ...'`).
- **Search & Filter Oracles**: Boolean search filters or response timing differences revealing existence of private records.
- **Webhooks as SSRF**: User-configured webhooks or callbacks fetching internal cloud metadata or intranet services without IP allowlists.

---

## 7. Chained Vulnerabilities & Trust Boundary Gaps
- **Cross-Component Gaps**: Component A sanitizes input and passes it to Component B; Component B makes assumptions about normalization, length limits, or encoding that A did not enforce.
- **Second-Order Exploitation**: Data that was benign when stored becomes dangerous when ingested by asynchronous background queues, analytics, or administrative dashboards.
- **Scope & Capability Inflation**: Tokens or API keys whose scopes inadvertently expand across delegation hops or background refreshes.

---

## 8. Obvious Exposures & Baseline Hygiene
Deterministic checklist of common exposures:
- Hardcoded secrets, API tokens, passwords (`TODO: remove secret`).
- Gated debug/admin endpoints accessible without authentication (`/debug`, `/admin`, `/metrics`, `/.env`).
- Missing security headers (`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`).
- Insecure cookies missing `HttpOnly`, `Secure`, or `SameSite` flags.
- Wildcard CORS with credentials (`Access-Control-Allow-Origin: *` + `Access-Control-Allow-Credentials: true`).
- Open redirects passing unvalidated user inputs into HTTP `302` redirect targets.
- Unpinned or vulnerable dependencies with known high-severity CVEs in lockfiles.
