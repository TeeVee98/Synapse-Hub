# Side-Effecting Tools Inventory & Consent Boundary Specification

> **Status:** Active (Milestone 1 Remediation — P0 Granular Authorization, Consent Boundary & Path Containment)  
> **Repository:** Synapse-Hub Enterprise QA Hub  
> **Audience:** AI Agents, QA Automation Engineers, Security Auditors

---

## 1. Executive Summary & Security Mandate

In enterprise test automation and autonomous AI workflows, tools frequently execute active security probes, filesystem modifications, database wipe/restore routines, and external network egress. Without rigorous authorization and containment boundaries, autonomous execution poses significant operational and security risks:

1. **Unbounded Network Egress:** Fuzzing probes, accessibility scanners, or issue-tracking bridges dispatching unauthorized HTTP/TCP traffic across intranet or external networks.
2. **State Destruction & Pollution:** Database snapshot restoration or pollution purges overwriting production databases or uncontained SQLite files.
3. **Filesystem Escape & Traversal:** Sandbox rollback handlers or mutation testing routines deleting or modifying files outside designated sandbox boundaries via directory traversal (`..`) or symlink escapes.
4. **Stale or Replayed Authorization:** Operations executing under generic boolean flags (`consent=True`) or unauthenticated shared environment variables without cryptographic replay protection or expiration bounds.

### Core Security Invariants
- **Default Deny:** Every side-effecting action is rejected unless an unexpired, unconsumed, cryptographically bounded `ConsentGrant` is provided.
- **Granular Binding:** Grants bind tightly to `action`, canonical `target`, `caller_session`, single-use `nonce`, and UTC `expiry`. HTTP operations must bind HTTP method and path patterns; database operations must bind canonical database identities.
- **Strict Path Containment:** All filesystem paths and database files must strictly reside within designated sandbox roots via `resolve_contained_path`, rejecting relative traversal, absolute escapes, and symlink redirects.
- **Offline Dry-Run Isolation:** When `dry_run=True`, tools are strictly prohibited from opening network sockets, performing DNS resolution, modifying files, or issuing database writes.

---

## 2. Comprehensive Inventory Matrix

The following table catalogs all 10 side-effecting tools, entry points, egress destinations, mutated entities, legacy mechanisms, and remediated granular scopes within Synapse-Hub.

| # | Tool Path | Boundary Category | Side-Effect Action | Egress Target / Mutated Entity | Legacy Authorization (Vulnerable) | Remediated Granular Scope |
|---|---|---|---|---|---|---|
| **1** | `tools/api_fuzzer.py` | Network Egress (HTTP) | Dispatches HTTP fuzz vectors (SQLi, XSS, headers, path traversal) | Target Base URL & API Endpoints | `bool(consent)`, `PENTEST_CONSENT_ACKNOWLEDGED`, `--confirm-pentest-scope` | `action="http:fuzz"`, `target=canonical_url`, `method=HTTP_METHOD`, `path_pattern=PATH`, `caller_session`, `nonce`, `expiry` |
| **2** | `tools/db_sandbox.py` | Database Mutation | `restore_snapshot` (file overwrite / table wipe / schema rollback) | Target SQLite / RDBMS file | `bool(consent)`, `SYNAPSE_FORCE_RESTORE`, `PENTEST_CONSENT_ACKNOWLEDGED` | `action="db:restore"`, `db_identity=canonical_path`, `caller_session`, `nonce`, `expiry` |
| **3** | `tools/db_sandbox.py` | Database Mutation | `audit_and_purge_pollution` (`DELETE FROM ...` query execution) | Target SQLite database | `bool(consent)`, `SYNAPSE_FORCE_PURGE`, `PENTEST_CONSENT_ACKNOWLEDGED` | `action="db:purge"`, `db_identity=canonical_path`, `caller_session`, `nonce`, `expiry` |
| **4** | `tools/db_sandbox.py` (`wait-ready`) | Network Socket | TCP port connect & HTTP GET readiness probe | `host:port`, URL endpoint | None (unauthenticated socket probe) | `action="net:probe"`, `target=host:port`, `caller_session`, `nonce`, `expiry` |
| **5** | `tools/reversible_sandbox.py` | Filesystem Mutation & Subprocess | `FILE_DELETE`, `DIR_DELETE`, undo shell command execution | Target file / directory / shell execution | None (direct execution of logged undo strings) | Path containment (`resolve_contained_path`), rejection of traversal / symlinks escaping `sandbox_root` |
| **6** | `tools/micro_mutator.py` | Filesystem Mutation & Subprocess | Mutates source code on disk, creates `.synapse_mutator_bak`, runs `test_cmd` | Target source files (`.py`, `.ts`, `.groovy`, `.js`) | None (direct disk write & subprocess execution) | `action="fs:mutate"`, `target=canonical_file_path`, `caller_session`, `nonce`, `expiry` |
| **7** | `tools/wcag_audit.py` | Network Egress (HTTP) | Fetches HTML DOM for accessibility compliance audit | Target web URL | None (`urllib.request.urlopen` direct call) | `action="http:wcag_scan"`, `target=canonical_url`, `caller_session`, `nonce`, `expiry` |
| **8** | `tools/jira_sync.py` | Network Egress (HTTP) | Creates, updates, and transitions Jira issues | Jira Server/Cloud REST API URL | Jira token in env vars (no execution boundary) | `action="jira:sync"`, `target=canonical_jira_url`, `caller_session`, `nonce`, `expiry` |
| **9** | `tools/tms_sync_bridge.py` | Network Egress (HTTP) | Synchronizes test cases & results to TestRail/Zephyr | TMS Server REST API URL | TMS token in env vars (no execution boundary) | `action="tms:sync"`, `target=canonical_tms_url`, `caller_session`, `nonce`, `expiry` |
| **10** | `tools/hub_publisher.py` | Network Egress (HTTP) & Git | Creates tags, releases, inspects CI, publishes NPM package | GitHub API & NPM Registry | GitHub/NPM tokens, CLI `-y` flag | `action="release:publish"`, `target=github_npm_registry`, `caller_session`, `nonce`, `expiry` |

---

## 3. Granular Authorization Architecture (`ConsentGrant`)

### 3.1 Grant Schema
The foundational authorization model resides in `tools/pentest_scope_guard.py` as an immutable dataclass:

```python
@dataclass(frozen=True)
class ConsentGrant:
    action: str              # e.g., "http:fuzz", "db:restore", "db:purge", "fs:undo"
    target: str              # Canonical target (URL, host:port, or directory)
    caller_session: str      # Caller identity or conversation/session UUID
    nonce: str               # Cryptographic single-use nonce (hex/uuid)
    expiry: float            # Unix epoch timestamp in UTC
    method: Optional[str] = None        # e.g., "GET", "POST", "PUT", "DELETE"
    path_pattern: Optional[str] = None  # e.g., "/api/v1/users/*"
    db_identity: Optional[str] = None   # Canonical path to database file
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 3.2 Verification Protocol
When evaluating a `ConsentGrant`, `verify_granular_grant` applies strict multi-point validation:
1. **Type & Structural Integrity:** The object must satisfy `is_consent_grant(...)`, validating structural field existence and non-empty values.
2. **Action Matching:** `grant.action` must exactly match the requested operation (e.g., `"http:fuzz"` vs `"db:restore"`).
3. **Target Binding:** Canonical target normalization must match the operational destination (exact match or path containment).
4. **Temporal Validity:** Current UTC timestamp must be strictly less than `grant.expiry`.
5. **Single-Use Replay Prevention:** `grant.nonce` is checked against an in-memory consumed-nonce registry (`_GLOBAL_CONSUMED_NONCES`). If the nonce was previously registered, execution is denied with a `PermissionError("Replay detected: nonce ... already consumed")`.
6. **Method & Path Pattern Matching:** If the action represents HTTP communication, `grant.method` must match the outgoing HTTP verb, and `grant.path_pattern` must match the URL path (supporting glob patterns via `fnmatch`).
7. **Database Identity Matching:** For database actions (`db:restore`, `db:purge`), `grant.db_identity` must match the canonicalized database filepath.

---

## 4. Path Containment Architecture (`resolve_contained_path`)

### 4.1 Threat Model
Filesystem and database tooling frequently operate with path parameters supplied by configuration files, test scripts, CLI arguments, or AI agent prompts. Attack vectors include:
- **Relative Traversal:** Path strings utilizing `../` or `..\\` sequences to break out of temporary directories.
- **Absolute Path Escapes:** Providing absolute paths (e.g., `/etc/passwd`, `/data/prod.db`, or system directories).
- **Symlink Escapes:** Utilizing directory or file symlinks pointing to sensitive locations outside the designated sandbox root.

### 4.2 Resolution Algorithm
`resolve_contained_path(sandbox_root, target_path)` enforces containment via canonical realpath resolution:

```python
def resolve_contained_path(sandbox_root: str, target_path: str) -> str:
    """Normalize and resolve target_path, ensuring it strictly resides within sandbox_root.
    
    Rejects:
    - Relative traversal ('..') escaping the root
    - Symlinks pointing outside the sandbox root
    - Absolute paths residing outside sandbox root
    """
    if not sandbox_root or not str(sandbox_root).strip():
        raise PathContainmentError("Sandbox root cannot be empty.")
    if not target_path or not str(target_path).strip():
        raise PathContainmentError("Target path cannot be empty.")

    canon_root = os.path.realpath(os.path.abspath(sandbox_root))
    
    # Resolve absolute candidate relative to sandbox_root if relative
    if os.path.isabs(target_path):
        candidate = os.path.abspath(target_path)
    else:
        candidate = os.path.abspath(os.path.join(canon_root, target_path))
        
    canon_target = os.path.realpath(candidate)
    
    # Path containment check via os.path.commonpath
    try:
        common = os.path.commonpath([canon_root, canon_target])
    except ValueError as exc:
        raise PathContainmentError(f"Path containment check failed across distinct drive roots: {exc}")
        
    if common != canon_root:
        raise PathContainmentError(
            f"Path containment violation: '{target_path}' resolves to '{canon_target}', "
            f"which escapes designated sandbox root '{canon_root}'."
        )
        
    return canon_target
```

---

## 5. Offline Dry-Run Isolation Semantics

In autonomous multi-agent environments, dry-run modes are frequently executed for planning, simulation, test discovery, and code review. 

### Invariants for `dry_run=True`:
1. **Zero Socket Creation:** Direct TCP/UDP socket opening (`socket.socket`, `socket.create_connection`) is strictly prohibited.
2. **Zero DNS Queries:** Remote hostname lookups via `socket.getaddrinfo` or `urllib.request` must not occur during dry-run instantiation or plan generation.
3. **Zero Remote HTTP Requests:** Outgoing HTTP/HTTPS client requests are prohibited. Any mocked execution must return simulated offline payloads with simulated status code `0` or `200` without dispatching network packets.
4. **Zero Filesystem Mutation:** Files on disk must not be created, edited, moved, or deleted. Temporary backup copies must not be written during dry-run evaluations.
5. **Zero Database Mutation:** Neither table schema updates, snapshot file overwrites, nor `DELETE` / `DROP` queries may be executed against databases.

---

## 6. Tool-by-Tool Detailed Profiles

### 6.1 `tools/api_fuzzer.py`
- **Boundary Category:** Network Egress (HTTP / REST APIs).
- **Entry Points:** `ApiFuzzer.__init__`, `ApiFuzzer.load_spec`, `ApiFuzzer.execute_request`, `main()`.
- **Side Effects:** Transmits adversarial HTTP mutation payloads (SQL injection, XSS vectors, oversized headers, boundary mutations) to target endpoints.
- **Legacy Defects:** Bypassed authorization checks if `consent=True` was passed as a boolean, if the unauthenticated environment variable `PENTEST_CONSENT_ACKNOWLEDGED=1` was present, or if `--confirm-pentest-scope` CLI flag was set. Dispatched DNS requests and remote spec fetches even when dry-run was desired.
- **Remediated State:**
  - Instantiation and `load_spec` accept `dry_run=True`; bypasses network spec fetches and remote DNS lookups when offline.
  - `execute_request` requires a valid `ConsentGrant`. Validates expiry, nonce single-use, canonical base URL, HTTP method, and endpoint path match (supporting fnmatch globbing).
  - Dry-run execution generates simulated `is_fuzzed=True` records with zero network packet transmission.

### 6.2 `tools/db_sandbox.py` (Snapshot Restore & Pollution Purge)
- **Boundary Category:** Database Mutation (SQLite / RDBMS).
- **Entry Points:** `DatabaseSandbox.restore_snapshot`, `DatabaseSandbox.audit_and_purge_pollution`, `main()`.
- **Side Effects:** Overwrites database file with baseline snapshot binary, drops tables, or issues `DELETE FROM <table> WHERE ...` statements to eliminate test junk.
- **Legacy Defects:** Accepted boolean `consent=True`, or shared environment variables `SYNAPSE_FORCE_RESTORE=1`, `SYNAPSE_FORCE_PURGE=1`, and `PENTEST_CONSENT_ACKNOWLEDGED=1`. Did not constrain `self.db_path` within a designated sandbox root, allowing traversal to arbitrary host databases.
- **Remediated State:**
  - `DatabaseSandbox.__init__` requires `sandbox_root` and validates `self.db_path` using `resolve_contained_path`.
  - `restore_snapshot` and `audit_and_purge_pollution` reject boolean flags and environment variables. Both operations strictly mandate a valid `ConsentGrant` binding `action="db:restore"` or `action="db:purge"` and matching `db_identity`.
  - When `dry_run=True`, database mutation routines exit immediately with zero disk writes and zero database queries.

### 6.3 `tools/db_sandbox.py` (`wait-ready` Socket Probe)
- **Boundary Category:** Network Socket Probing (TCP / HTTP).
- **Entry Points:** `DatabaseSandbox.wait_ready`, `_probe_port`, `_probe_http`.
- **Side Effects:** Connects to TCP ports and sends HTTP GET requests to evaluate database container or service readiness.
- **Remediated State:**
  - Validates `action="net:probe"` and target host/port bounds via `PentestScopeGuard`.
  - Dry-run mode skips live socket binding and returns simulated readiness status.

### 6.4 `tools/reversible_sandbox.py`
- **Boundary Category:** Filesystem Mutation & Subprocess Execution.
- **Entry Points:** `ReversibleSandbox.rollback_all`, `ReversibleSandbox.record_change`.
- **Side Effects:** Parses logged undo commands (`FILE_DELETE: <path>`, `DIR_DELETE: <path>`, or arbitrary shell command strings) and executes deletions or rollback subprocesses.
- **Legacy Defects:** Arbitrary paths were passed directly to `os.remove()` and `shutil.rmtree()`; non-prefixed undo commands were passed to `subprocess.run()`. No validation prevented directory traversal outside the project directory.
- **Remediated State:**
  - Enforces `sandbox_root` containment via `resolve_contained_path` for all `FILE_DELETE` and `DIR_DELETE` targets.
  - Rejects traversal attempts (`..`), symlinks escaping root, and absolute paths outside the designated sandbox root.

### 6.5 `tools/micro_mutator.py`
- **Boundary Category:** Filesystem Mutation & Subprocess Execution.
- **Entry Points:** `MicroMutator.evaluate_mutants_dynamically`, `evaluate_target`.
- **Side Effects:** Mutates source code AST on disk, creates temporary backup files (`.synapse_mutator_bak`), and executes automated test runners via subprocess.
- **Remediated State:**
  - Validates target source files against project repository containment.
  - Ensures clean teardown and restoration of backup files even on runner interruptions.
  - Operates in static AST analysis mode by default to prevent unwanted disk modifications during static audits.

### 6.6 `tools/wcag_audit.py`
- **Boundary Category:** Network Egress (HTTP / DOM Scraper).
- **Entry Points:** `WcagAuditor.audit_url`, `main()`.
- **Side Effects:** Dispatches HTTP GET requests via `urllib.request.urlopen` to retrieve remote HTML pages for accessibility analysis.
- **Remediated State:**
  - Integrates target validation through `PentestScopeGuard.validate_target` to prevent SSRF against loopback addresses, link-local metadata (e.g., `169.254.169.254`), and unauthorized internal networks.
  - Requires `action="http:wcag_scan"` grant for active external scans.

### 6.7 `tools/jira_sync.py` & `tools/tms_sync_bridge.py`
- **Boundary Category:** Network Egress & Remote State Mutation (External SaaS APIs).
- **Entry Points:** `JiraSync.create_issue`, `TmsSyncBridge.push_results`.
- **Side Effects:** Submits automated defect tickets or synchronizes test execution runs to enterprise management platforms (Jira, TestRail, Zephyr).
- **Remediated State:**
  - Requires explicit session grants (`action="jira:sync"`, `action="tms:sync"`) before dispatching mutating REST calls (`POST`, `PUT`, `DELETE`).
  - Restricts remote destination URLs to corporate Jira/TMS allowlists.

### 6.8 `tools/hub_publisher.py`
- **Boundary Category:** Network Egress, Remote Git Mutation & Package Release.
- **Entry Points:** `HubPublisher.publish_release`, `main()`.
- **Side Effects:** Pushes git tags to remote origin, triggers GitHub Release API endpoints, and publishes packages to public or internal NPM registries.
- **Remediated State:**
  - Enforces strict CLI interactive confirmation (or explicit `--yes` with validated environment variables).
  - Governed by Git Push Protocol and `action="release:publish"` grant binding.

---

## 7. Audit Trail, Nonce Management & Telemetry

1. **Consumed Nonce Registry:** In-memory registry `_GLOBAL_CONSUMED_NONCES` prevents replay attacks during long-running agent workflows. A helper `clear_consumed_nonces()` is provided for test teardowns.
2. **Audit Logging:** Every grant creation, grant verification failure, path containment violation, and authorization denial is recorded with structured security logs (`SECURITY: ...`, `PathContainmentError`, `PermissionError`).
3. **Fast-Fail on Authorization Mismatch:** Failure to provide a valid grant fails closed immediately (raising `PermissionError` or returning structured error codes) without executing partial or exploratory side effects.

---

## 8. Compliance Checklist for Future Side-Effecting Tools

When adding new tools to Synapse-Hub that interact with external networks, filesystems, or databases, developers and AI agents must comply with the following checklist:

- [ ] **No Generic Boolean Consent:** Do not accept `consent: bool = True` or unauthenticated environment variables (`FORCE_*`, `PENTEST_*`) as an authorization bypass.
- [ ] **Enforce `ConsentGrant`:** Require a `ConsentGrant` object verifying `action`, `target`, `nonce`, and `expiry` via `verify_granular_grant`.
- [ ] **Path Containment:** Validate all input and output filesystem paths using `resolve_contained_path(sandbox_root, path)`.
- [ ] **Offline Dry-Run:** Implement `dry_run: bool = False`. Guarantee zero socket creation, zero DNS resolution, zero file writes, and zero database mutations when `dry_run=True`.
- [ ] **SSRF & Network Guard:** Route all HTTP/TCP destinations through `PentestScopeGuard.validate_target` to prevent loopback, link-local, and metadata service probing.
- [ ] **Idempotent Teardown:** Ensure any state modified during execution is recorded for rollback or cleaned up in an automated teardown block.
- [ ] **Inventory Update:** Add the new tool and its required granular scope to this inventory document.
