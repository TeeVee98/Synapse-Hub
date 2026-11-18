#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
Enterprise Autonomous API Fuzzing & Chaos Breaker
-------------------------------------------------
Zero-dependency, active runtime API mutator and resilience tester.
Ingests OpenAPI 3.x / Swagger 2.0 specifications (or endpoint catalogs),
generates dynamic boundary, type-inverted, and adversarial fuzzing payloads,
and executes live HTTP/S requests against staging/test APIs.

Three-Alarm Oracle Detection:
  1. HTTP 500 / 502 / 503 Internal Server Error (Backend crash / unhandled fault)
  2. Database & Framework Stacktrace Leaks (SQL injection reflection, Django/Spring/Postgres traces)
  3. SLA Latency Breach (> 3000ms response time - potential ReDoS or lock contention)
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

import os
import sys
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_TOOLS_ROOT, ".."))
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import os
import re
import sys
import json
import time
import ssl
import tempfile
import urllib.request
import urllib.error
import urllib.parse
import argparse
import fnmatch
import uuid
import secrets
from typing import Dict, Any, List, Optional

from pentest_scope_guard import (
    PentestScopeGuard,
    PentestRateLimiter,
    PentestScopeError,
    PathContainmentError,
    ConsentGrant,
    create_consent_grant,
    is_consent_grant,
    resolve_contained_path,
    mask_secrets,
    _GLOBAL_CONSUMED_NONCES,
)

# Enforce UTF-8 stdout encoding for Windows/macOS/Linux compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
QA_HUB_ROOT = HUB_ROOT
REPORTS_DIR = os.path.join(HUB_ROOT, "reports")

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from fuzz_payloads import get_fuzz_payloads, get_field_fuzz_scenarios
except ImportError:
    get_fuzz_payloads = None
    get_field_fuzz_scenarios = None

# Stacktrace and DB leak pattern signatures
STACKTRACE_LEAK_PATTERNS = [
    re.compile(r'Traceback \(most recent call last\):', re.IGNORECASE),
    re.compile(r'Exception in thread "[^"]+"', re.IGNORECASE),
    re.compile(r'\b(org\.springframework|org\.hibernate|java\.lang\.NullPointerException)\b', re.IGNORECASE),
    re.compile(r'\b(psycopg2\.(OperationalError|ProgrammingError)|PSQLException)\b', re.IGNORECASE),
    re.compile(r'\b(mysql_error|mysqli_sql_exception|pymysql\.err)\b', re.IGNORECASE),
    re.compile(r'\b(sqlite3\.OperationalError|SQLiteException)\b', re.IGNORECASE),
    re.compile(r'\b(django\.db\.utils|sqlalchemy\.exc)\b', re.IGNORECASE),
    re.compile(r'SQLSTATE\[[0-9A-Z]{5}\]', re.IGNORECASE),
    re.compile(r'syntax error at or near\s+"', re.IGNORECASE),
    re.compile(r'ODBC SQL Server Driver', re.IGNORECASE),
]

# Severity taxonomy (concept borrowed from OWASP ZAP's alert risk levels,
# Apache-2.0 - re-expressed for the fuzz oracle). Each alarm class maps to a
# fixed risk level so CI can gate on CRITICAL findings alone.
ALARM_SEVERITY = {
    "HTTP_": "HIGH",            # HTTP_500/502/503_SERVER_CRASH
    "STACKTRACE_LEAK": "CRITICAL",
    "SLA_TIMEOUT": "LOW",
    "AUTH_BYPASS": "CRITICAL",
    "CONNECTION_ERROR": "MEDIUM",
    "DANGEROUS_REDIRECT_BLOCKED": "CRITICAL",
    "SCOPE_BLOCKED": "CRITICAL",
}
SEVERITY_LEVELS = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


def classify_alarm_severity(alarm: str) -> str:
    """Maps an alarm string onto the ZAP-style severity taxonomy."""
    for prefix, severity in ALARM_SEVERITY.items():
        if alarm.startswith(prefix):
            return severity
    return "INFO"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class ApiFuzzer:
    """Autonomous runtime API fuzzer with three-alarm defect Oracle."""

    def __init__(
        self,
        base_url: str,
        spec_path_or_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout_sec: float = 10.0,
        sla_ms: float = 3000.0,
        verify_ssl: bool = True,
        insecure: bool = False,
        scope_guard: Optional[PentestScopeGuard] = None,
        rate_limiter: Optional[PentestRateLimiter] = None,
        max_requests: int = 500,
        allow_internal: bool = False,
        allow_loopback: bool = True,
        consent: Any = False,
        dry_run: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.spec_path = spec_path_or_url
        self.custom_headers = headers or {"Content-Type": "application/json", "User-Agent": "AgentQA-Fuzzer/2.0"}
        self.timeout_sec = timeout_sec
        self.sla_ms = sla_ms
        self.insecure = insecure or (not verify_ssl)
        self.verify_ssl = not self.insecure
        self.max_requests = max(1, int(max_requests))
        self.consent = consent
        self.dry_run = bool(dry_run)

        # Wire unified scope guard and rate limiter (narrow loopback opt-in for local test harnesses)
        self.scope_guard = scope_guard or PentestScopeGuard(
            allow_internal=allow_internal,
            allow_loopback=allow_loopback
        )
        self.rate_limiter = rate_limiter or self.scope_guard.rate_limiter

        # Prepare SSL context (support self-signed staging certificates via explicit --insecure flag)
        self.ssl_context = ssl.create_default_context()
        if self.insecure:
            print("  ⚠️ [SECURITY NOTICE] TLS certificate verification is explicitly disabled (--insecure).")
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

        # Hardened transport opener with SafeRedirectHandler
        self.opener = self.scope_guard.create_safe_opener(
            timeout_sec=self.timeout_sec,
            ssl_context=self.ssl_context
        )

        # Validate target base_url before proceeding (Fail-closed)
        # When dry_run=True, skip live DNS lookups and network validation
        if not self.dry_run:
            ok, reason = self.scope_guard.validate_target(self.base_url, actor="ApiFuzzer.__init__")
            if not ok:
                raise PermissionError(
                    f"[SAFETY FIREWALL - REJECTED] Target base URL '{self.base_url}' is not permitted by pentest scope guard: {reason}"
                )

    @staticmethod
    def _is_safe_non_prod_host(host: str) -> bool:
        """
        Deprecated: Replaced by PentestScopeGuard. Enforces strict allowlist validation
        without loose subdomain heuristics.
        """
        guard = PentestScopeGuard(allow_internal=True)
        ok, _ = guard.validate_target(f"http://{host}")
        return ok

    def load_spec(self) -> Dict[str, Any]:
        """Loads OpenAPI or Swagger specification from file or URL."""
        if not self.spec_path:
            # Fallback default health and mock endpoints
            return {
                "paths": {
                    "/api/v1/users": {
                        "post": {
                            "summary": "Create user",
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "username": {"type": "string", "maxLength": 50},
                                                "age": {"type": "integer", "minimum": 1, "maximum": 120},
                                                "email": {"type": "string"}
                                            },
                                            "required": ["username"]
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

        if self.spec_path.startswith(("http://", "https://")):
            if self.dry_run:
                # Offline mock spec when dry_run=True: zero network and DNS requests
                return {
                    "paths": {
                        "/api/v1/dry_run_endpoint": {
                            "get": {
                                "summary": "Dry run offline endpoint",
                                "responses": {"200": {"description": "OK"}}
                            }
                        }
                    }
                }
            # Validate spec URL with scope guard before network dispatch
            ok, reason = self.scope_guard.validate_target(self.spec_path, actor="ApiFuzzer.load_spec")
            if not ok:
                raise PermissionError(f"[PENTEST SCOPE GUARD] Disallowed OpenAPI spec URL '{self.spec_path}': {reason}")
            req = urllib.request.Request(self.spec_path, headers={"User-Agent": "AgentQA-Fuzzer/2.0"})
            try:
                with self.opener.open(req, timeout=10.0) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)
            except PentestScopeError as pse:
                raise PermissionError(f"[PENTEST SCOPE GUARD] Redirect blocked during load_spec: {pse}")
        else:
            # Validate that local spec path does not traverse outside workspace or temporary directories
            allowed_roots = [os.path.abspath(os.getcwd()), QA_HUB_ROOT, tempfile.gettempdir()]

            contained_path = None
            for root in allowed_roots:
                try:
                    contained_path = resolve_contained_path(root, self.spec_path)
                    break
                except PathContainmentError:
                    continue

            if contained_path is None:
                raise PathContainmentError(f"OpenAPI spec path '{self.spec_path}' escapes designated containment roots.")

            if not os.path.exists(contained_path):
                raise FileNotFoundError(f"OpenAPI spec not found: {self.spec_path}")
            with open(contained_path, "r", encoding="utf-8") as f:
                return json.load(f)

    def extract_fuzz_targets(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts actionable API routes and property schemas from spec."""
        targets = []
        paths = spec.get("paths", {})
        for path, path_item in paths.items():
            for method, details in path_item.items():
                if method.lower() not in ("get", "post", "put", "patch", "delete"):
                    continue

                req_body = details.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
                props = req_body.get("properties", {})
                required = req_body.get("required", [])

                targets.append({
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", f"{method.upper()} {path}"),
                    "parameters": details.get("parameters", []),
                    "properties": props,
                    "required": required
                })
        return targets

    def generate_mutations(self, target: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generates dynamic mutation vectors for query params and request body."""
        mutations = []
        props = target.get("properties", {})
        method = target["method"]
        path = target["path"]

        # Base valid skeleton
        valid_body: Dict[str, Any] = {}
        for p_name, p_schema in props.items():
            t = p_schema.get("type", "string")
            if t == "string":
                valid_body[p_name] = f"valid_{p_name}"
            elif t in ("integer", "number"):
                valid_body[p_name] = 10
            elif t == "boolean":
                valid_body[p_name] = True
            else:
                valid_body[p_name] = "test"

        # 1. Baseline Happy-Path
        mutations.append({
            "name": f"{method} {path} - Baseline Happy-Path",
            "type": "BASELINE",
            "path": path,
            "method": method,
            "body": valid_body,
            "headers": self.custom_headers
        })

        # 2. Field Fuzzing Payloads
        for p_name, p_schema in props.items():
            p_type = p_schema.get("type", "string")

            # A. Extreme Buffer Stress (10,000 chars)
            mut_body = dict(valid_body)
            mut_body[p_name] = "A" * 10000
            mutations.append({
                "name": f"{method} {path} - Buffer Stress on '{p_name}'",
                "type": "BUFFER_STRESS",
                "path": path,
                "method": method,
                "body": mut_body,
                "headers": self.custom_headers
            })

            # B. SQLi Polyglot Probe
            mut_body = dict(valid_body)
            mut_body[p_name] = "' OR '1'='1' -- /* injected */"
            mutations.append({
                "name": f"{method} {path} - SQLi Polyglot Probe on '{p_name}'",
                "type": "SQLI_INJECTION",
                "path": path,
                "method": method,
                "body": mut_body,
                "headers": self.custom_headers
            })

            # C. Unicode BiDi / RTL Trojan Source
            mut_body = dict(valid_body)
            mut_body[p_name] = "\u202E\u0041\u0042\u0043_AUTO_TX"
            mutations.append({
                "name": f"{method} {path} - Unicode BiDi RTL Override on '{p_name}'",
                "type": "BIDI_UNICODE",
                "path": path,
                "method": method,
                "body": mut_body,
                "headers": self.custom_headers
            })

            # D. Null Byte Injection
            mut_body = dict(valid_body)
            mut_body[p_name] = f"data\x00{p_name}.json"
            mutations.append({
                "name": f"{method} {path} - Null Byte Injection on '{p_name}'",
                "type": "NULL_BYTE",
                "path": path,
                "method": method,
                "body": mut_body,
                "headers": self.custom_headers
            })

            # E. Numeric Boundaries (if integer)
            if p_type in ("integer", "number"):
                mut_body = dict(valid_body)
                mut_body[p_name] = 2147483648  # 32-bit overflow
                mutations.append({
                    "name": f"{method} {path} - 32-bit Integer Overflow on '{p_name}'",
                    "type": "NUMERIC_OVERFLOW",
                    "path": path,
                    "method": method,
                    "body": mut_body,
                    "headers": self.custom_headers
                })

            # F. Type Inversion (String where integer expected or vice versa)
            mut_body = dict(valid_body)
            mut_body[p_name] = 99999 if p_type == "string" else "NOT_A_NUMBER"
            mutations.append({
                "name": f"{method} {path} - Type Mutation on '{p_name}'",
                "type": "TYPE_MUTATION",
                "path": path,
                "method": method,
                "body": mut_body,
                "headers": self.custom_headers
            })

        # 3. Auth Bypass Vector (Remove Authorization Header)
        mut_headers = {k: v for k, v in self.custom_headers.items() if k.lower() != "authorization"}
        mutations.append({
            "name": f"{method} {path} - Auth Token Omission Probe",
            "type": "AUTH_OMISSION",
            "path": path,
            "method": method,
            "body": valid_body,
            "headers": mut_headers
        })

        # 4. Catalog-Driven Vectors via tools/fuzz_payloads.py (XSS polyglots,
        #    emoji surrogates, numeric boundaries). Formerly a dead import -
        #    now wired into generation so the catalog actually fires.
        if get_field_fuzz_scenarios is not None:
            existing_names = {m["name"] for m in mutations}
            for p_name, p_schema in props.items():
                p_type = p_schema.get("type", "string")
                for scen in get_field_fuzz_scenarios(p_name, p_type):
                    mut_body = dict(valid_body)
                    mut_body[p_name] = scen["value"]
                    name = f"{method} {path} - {scen['scenario']}"
                    if name in existing_names:
                        continue
                    existing_names.add(name)
                    mutations.append({
                        "name": name,
                        "type": scen["category"],
                        "path": path,
                        "method": method,
                        "body": mut_body,
                        "headers": self.custom_headers
                    })

        return mutations

    def execute_request(self, mutation: Dict[str, Any], dry_run: bool = False, consent: Optional[Any] = None) -> Dict[str, Any]:
        """Dispatches HTTP mutation and evaluates the three-alarm Oracle."""
        url = f"{self.base_url}{mutation['path']}"
        method = mutation["method"]
        body_data = None
        if method in ("POST", "PUT", "PATCH") and mutation.get("body") is not None:
            body_data = json.dumps(mutation["body"]).encode("utf-8")

        if dry_run or self.dry_run:
            # Deterministic offline mock for CI & local checks
            return {
                "name": mutation["name"],
                "type": mutation["type"],
                "url": mask_secrets(url),
                "method": method,
                "status_code": 400 if mutation["type"] != "BASELINE" else 200,
                "duration_ms": 42.5,
                "verdict": "PASS",
                "severity": "INFO",
                "alarms": [],
                "response_preview": '{"status": "handled_by_dry_run"}'
            }

        # Consent verification: active live testing requires explicit granular consent before network dispatch
        effective_consent = self.consent if consent is None else consent

        # 1. Reject missing or generic boolean consent
        if effective_consent is None or isinstance(effective_consent, bool) or not effective_consent:
            return {
                "name": mutation.get("name", "unnamed"),
                "type": mutation.get("type", "UNKNOWN"),
                "url": mask_secrets(url),
                "method": method,
                "status_code": -5,
                "duration_ms": 0.0,
                "verdict": "FAIL",
                "severity": "CRITICAL",
                "alarms": ["CONSENT_REQUIRED: Active API request rejected. Granular ConsentGrant required (binding action='http:fuzz', canonical target, caller_session, nonce, expiry)."],
                "response_preview": "Active request blocked: missing consent."
            }

        # 2. Extract attributes from ConsentGrant or scoped dict
        if is_consent_grant(effective_consent):
            c_target = effective_consent.target
            c_method = effective_consent.method
            c_path = effective_consent.path_pattern
            c_expiry = effective_consent.expiry
            c_nonce = effective_consent.nonce
        elif isinstance(effective_consent, dict):
            c_target = effective_consent.get("target") or effective_consent.get("target_sandbox") or effective_consent.get("base_url")
            c_method = effective_consent.get("method")
            c_path = effective_consent.get("path") or effective_consent.get("path_pattern")
            c_expiry = effective_consent.get("expiry")
            c_nonce = effective_consent.get("nonce")
            c_session = effective_consent.get("caller_session") or effective_consent.get("session") or effective_consent.get("session_id")
            # Check target, method, and path mismatch before rejecting incomplete dict fields
            if c_target and not (url.startswith(c_target.rstrip("/")) or self.base_url == c_target.rstrip("/")):
                return {
                    "name": mutation.get("name", "unnamed"),
                    "type": mutation.get("type", "UNKNOWN"),
                    "url": mask_secrets(url),
                    "method": method,
                    "status_code": -5,
                    "duration_ms": 0.0,
                    "verdict": "FAIL",
                    "severity": "CRITICAL",
                    "alarms": [f"CONSENT_MISMATCH: Scoped consent target '{c_target}' does not authorize target URL '{mask_secrets(url)}'."],
                    "response_preview": "Active request blocked: consent target mismatch."
                }

            if c_method and c_method.upper() != method.upper():
                return {
                    "name": mutation.get("name", "unnamed"),
                    "type": mutation.get("type", "UNKNOWN"),
                    "url": mask_secrets(url),
                    "method": method,
                    "status_code": -5,
                    "duration_ms": 0.0,
                    "verdict": "FAIL",
                    "severity": "CRITICAL",
                    "alarms": [f"CONSENT_MISMATCH: Scoped consent method '{c_method}' does not authorize mutation method '{method}'."],
                    "response_preview": "Active request blocked: consent method mismatch."
                }

            if c_path:
                m_path = mutation.get("path", "")
                if c_path != m_path and not fnmatch.fnmatch(m_path, c_path):
                    return {
                        "name": mutation.get("name", "unnamed"),
                        "type": mutation.get("type", "UNKNOWN"),
                        "url": mask_secrets(url),
                        "method": method,
                        "status_code": -5,
                        "duration_ms": 0.0,
                        "verdict": "FAIL",
                        "severity": "CRITICAL",
                        "alarms": [f"CONSENT_MISMATCH: Scoped consent path '{c_path}' does not authorize mutation path '{m_path}'."],
                        "response_preview": "Active request blocked: consent path mismatch."
                    }

            if not c_target or not c_nonce or c_expiry is None or not c_session:
                return {
                    "name": mutation.get("name", "unnamed"),
                    "type": mutation.get("type", "UNKNOWN"),
                    "url": mask_secrets(url),
                    "method": method,
                    "status_code": -5,
                    "duration_ms": 0.0,
                    "verdict": "FAIL",
                    "severity": "CRITICAL",
                    "alarms": ["CONSENT_REQUIRED: Granular grant dictionary missing mandatory fields (action, target, caller_session, nonce, expiry)."],
                    "response_preview": "Active request blocked: missing mandatory consent fields."
                }
        else:
            return {
                "name": mutation.get("name", "unnamed"),
                "type": mutation.get("type", "UNKNOWN"),
                "url": mask_secrets(url),
                "method": method,
                "status_code": -5,
                "duration_ms": 0.0,
                "verdict": "FAIL",
                "severity": "CRITICAL",
                "alarms": ["CONSENT_REQUIRED: Invalid consent type. Expected ConsentGrant or scoped grant dict."],
                "response_preview": "Active request blocked: missing consent."
            }

        # 3. Check expiration
        if c_expiry is not None:
            try:
                if time.time() > float(c_expiry):
                    return {
                        "name": mutation.get("name", "unnamed"),
                        "type": mutation.get("type", "UNKNOWN"),
                        "url": mask_secrets(url),
                        "method": method,
                        "status_code": -5,
                        "duration_ms": 0.0,
                        "verdict": "FAIL",
                        "severity": "CRITICAL",
                        "alarms": ["CONSENT_EXPIRED: Consent grant has expired."],
                        "response_preview": "Active request blocked: consent expired."
                    }
            except (ValueError, TypeError) as exp_err:
                return {
                    "name": mutation.get("name", "unnamed"),
                    "type": mutation.get("type", "UNKNOWN"),
                    "url": mask_secrets(url),
                    "method": method,
                    "status_code": -5,
                    "duration_ms": 0.0,
                    "verdict": "FAIL",
                    "severity": "CRITICAL",
                    "alarms": [f"CONSENT_INVALID_EXPIRY: {exp_err}"],
                    "response_preview": "Active request blocked: consent expiry invalid."
                }

        # 4. Check nonce replay
        if c_nonce:
            if hasattr(self.scope_guard, "consumed_nonces") and c_nonce in self.scope_guard.consumed_nonces:
                return {
                    "name": mutation.get("name", "unnamed"),
                    "type": mutation.get("type", "UNKNOWN"),
                    "url": mask_secrets(url),
                    "method": method,
                    "status_code": -5,
                    "duration_ms": 0.0,
                    "verdict": "FAIL",
                    "severity": "CRITICAL",
                    "alarms": ["CONSENT_REPLAYED: Replay attack detected. Consent nonce has already been consumed."],
                    "response_preview": "Active request blocked: consent replayed."
                }

        # 5. Check target mismatch
        if c_target and not (url.startswith(c_target.rstrip("/")) or self.base_url == c_target.rstrip("/")):
            return {
                "name": mutation.get("name", "unnamed"),
                "type": mutation.get("type", "UNKNOWN"),
                "url": mask_secrets(url),
                "method": method,
                "status_code": -5,
                "duration_ms": 0.0,
                "verdict": "FAIL",
                "severity": "CRITICAL",
                "alarms": [f"CONSENT_MISMATCH: Scoped consent target '{c_target}' does not authorize target URL '{mask_secrets(url)}'."],
                "response_preview": "Active request blocked: consent target mismatch."
            }

        # 6. Check method mismatch
        if c_method and c_method.upper() != method.upper():
            return {
                "name": mutation.get("name", "unnamed"),
                "type": mutation.get("type", "UNKNOWN"),
                "url": mask_secrets(url),
                "method": method,
                "status_code": -5,
                "duration_ms": 0.0,
                "verdict": "FAIL",
                "severity": "CRITICAL",
                "alarms": [f"CONSENT_MISMATCH: Scoped consent method '{c_method}' does not authorize mutation method '{method}'."],
                "response_preview": "Active request blocked: consent method mismatch."
            }

        # 7. Check path mismatch
        if c_path:
            m_path = mutation.get("path", "")
            if c_path != m_path and not fnmatch.fnmatch(m_path, c_path):
                return {
                    "name": mutation.get("name", "unnamed"),
                    "type": mutation.get("type", "UNKNOWN"),
                    "url": mask_secrets(url),
                    "method": method,
                    "status_code": -5,
                    "duration_ms": 0.0,
                    "verdict": "FAIL",
                    "severity": "CRITICAL",
                    "alarms": [f"CONSENT_MISMATCH: Scoped consent path '{c_path}' does not authorize mutation path '{m_path}'."],
                    "response_preview": "Active request blocked: consent path mismatch."
                }

        # 8. Verify with PentestScopeGuard
        if not self.scope_guard.verify_consent(effective_consent, expected_action="http:fuzz", expected_target=self.base_url):
            return {
                "name": mutation.get("name", "unnamed"),
                "type": mutation.get("type", "UNKNOWN"),
                "url": mask_secrets(url),
                "method": method,
                "status_code": -5,
                "duration_ms": 0.0,
                "verdict": "FAIL",
                "severity": "CRITICAL",
                "alarms": ["CONSENT_REQUIRED: Consent verification failed against pentest scope guard."],
                "response_preview": "Active request blocked: missing consent."
            }

        # Mark nonce consumed
        if c_nonce and hasattr(self.scope_guard, "consumed_nonces"):
            self.scope_guard.consumed_nonces.add(c_nonce)

        # Check target URL with PentestScopeGuard before network dispatch (Consent NEVER bypasses host scope guard)
        ok, scope_reason = self.scope_guard.validate_target(url, actor="ApiFuzzer.execute_request")
        if not ok:
            return {
                "name": mutation["name"],
                "type": mutation["type"],
                "url": mask_secrets(url),
                "method": method,
                "status_code": -3,
                "duration_ms": 0.0,
                "verdict": "FAIL",
                "severity": "CRITICAL",
                "alarms": [f"SCOPE_BLOCKED: Request target blocked by pentest scope guard: {scope_reason}"],
                "response_preview": mask_secrets(scope_reason)
            }

        req = urllib.request.Request(
            url=url,
            data=body_data,
            headers=mutation["headers"],
            method=method
        )

        start_time = time.time()
        status_code = 0
        response_body = ""
        duration_ms = 0.0
        redirect_blocked = False

        try:
            with self.opener.open(req, timeout=self.timeout_sec) as resp:
                status_code = resp.getcode()
                response_body = resp.read().decode("utf-8", errors="replace")
        except PentestScopeError as pse:
            status_code = -4
            response_body = str(pse)
            redirect_blocked = True
        except urllib.error.HTTPError as he:
            status_code = he.code
            try:
                response_body = he.read().decode("utf-8", errors="replace")
            except Exception:
                response_body = str(he)
        except urllib.error.URLError as ue:
            status_code = -1
            response_body = str(ue.reason)
        except Exception as e:
            status_code = -2
            response_body = str(e)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # ----------------------------------------------------
        # THREE-ALARM DEFECT ORACLE EVALUATION
        # ----------------------------------------------------
        alarms = []

        if redirect_blocked:
            alarms.append(f"DANGEROUS_REDIRECT_BLOCKED: {response_body}")

        # Alarm 1: HTTP 500 / 502 / 503 Internal Server Error
        if status_code in (500, 502, 503):
            alarms.append(f"HTTP_{status_code}_SERVER_CRASH: Unhandled backend exception / server panic")

        # Alarm 2: Database / Framework Stacktrace Leak
        for pattern in STACKTRACE_LEAK_PATTERNS:
            if pattern.search(response_body):
                matched = pattern.pattern
                alarms.append(f"STACKTRACE_LEAK: Response leaks backend internals matching '{matched}'")
                break

        # Alarm 3: SLA Latency Breach (> 3000ms)
        if duration_ms > self.sla_ms:
            alarms.append(f"SLA_TIMEOUT: Response took {duration_ms}ms (threshold: {self.sla_ms}ms), possible ReDoS or DB lock")

        # Alarm 4: Auth Bypass (OMISSION succeeded with 200/201)
        if mutation["type"] == "AUTH_OMISSION" and status_code in (200, 201):
            alarms.append("AUTH_BYPASS_VULNERABILITY: Endpoint returned 200 OK without Authorization header")

        # Alarm 5: Target unreachable - an endpoint that could not be tested
        # must NEVER be reported as PASS (Truth Anchor discipline).
        if status_code < 0 and not redirect_blocked:
            alarms.append("CONNECTION_ERROR: Target unreachable or transport failure - endpoint could not be verified")

        verdict = "FAIL" if alarms else "PASS"
        severity = "INFO"
        if alarms:
            severity = max(
                (classify_alarm_severity(a) for a in alarms),
                key=lambda s: SEVERITY_LEVELS.index(s)
            )

        return {
            "name": mutation["name"],
            "type": mutation["type"],
            "url": mask_secrets(url),
            "method": method,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "verdict": verdict,
            "severity": severity,
            "alarms": alarms,
            "response_preview": mask_secrets(response_body[:300])
        }

    def run_fuzz_suite(self, dry_run: bool = False, consent: Any = False) -> Dict[str, Any]:
        """Runs the complete fuzzing suite against all extracted targets."""
        effective_dry_run = dry_run or self.dry_run
        parent_nonce = None
        # Consent validation: active live testing requires explicit consent
        if not effective_dry_run:
            effective_consent = self.consent if consent is False else consent
            has_consent = self.scope_guard.verify_consent(
                effective_consent,
                expected_action="http:fuzz",
                expected_target=self.base_url,
                mark_consumed=False  # Do not burn session nonce during pre-flight check!
            )
            if not has_consent:
                raise PermissionError(
                    "Active API fuzzing requires explicit consent. Provide a valid granular ConsentGrant "
                    "(or pass --confirm-pentest-scope on CLI), or set dry_run=True to preview safely."
                )

            # Extract parent session grant attributes for deriving child request grants
            if is_consent_grant(effective_consent):
                parent_action = effective_consent.action
                parent_target = effective_consent.target
                parent_session = effective_consent.caller_session
                parent_nonce = effective_consent.nonce
                parent_expiry = effective_consent.expiry
            elif isinstance(effective_consent, dict):
                parent_action = effective_consent.get("action") or effective_consent.get("operation") or "http:fuzz"
                parent_target = effective_consent.get("target") or effective_consent.get("target_sandbox") or effective_consent.get("base_url") or self.base_url
                parent_session = effective_consent.get("caller_session") or effective_consent.get("session") or f"cli_{os.getpid()}"
                parent_nonce = effective_consent.get("nonce")
                parent_expiry = effective_consent.get("expiry") or (time.time() + 300.0)
            else:
                parent_action = "http:fuzz"
                parent_target = self.base_url
                parent_session = f"cli_{os.getpid()}"
                parent_nonce = secrets.token_hex(16)
                parent_expiry = time.time() + 300.0

        spec = self.load_spec()
        targets = self.extract_fuzz_targets(spec)

        all_mutations = []
        for t in targets:
            all_mutations.extend(self.generate_mutations(t))

        total_generated = len(all_mutations)
        volume_capped = False
        if len(all_mutations) > self.max_requests:
            all_mutations = all_mutations[:self.max_requests]
            volume_capped = True

        results = []
        total_failures = 0

        print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
        print(f"{BOLD}{CYAN}      ENTERPRISE AUTONOMOUS API FUZZING & CHAOS BREAKER               {RESET}")
        print(f"{BOLD}{CYAN}======================================================================{RESET}")
        print(f"  Target Base URL   : {mask_secrets(self.base_url)}")
        print(f"  Spec Source       : {mask_secrets(self.spec_path or 'Default Archetype')}")
        print(f"  Total Endpoints   : {len(targets)}")
        print(f"  Total Mutations   : {len(all_mutations)} (capped from {total_generated})" if volume_capped else f"  Total Mutations   : {len(all_mutations)}")
        print(f"  SLA Threshold     : {self.sla_ms} ms")
        print(f"  Rate Limit Max    : {self.rate_limiter.max_req_per_sec} req/s")
        print(f"  Mode              : {'DRY-RUN (Air-Gapped / Deterministic)' if effective_dry_run else 'LIVE STAGING ATTACK'}\n")

        try:
            for idx, m in enumerate(all_mutations, start=1):
                if not effective_dry_run:
                    self.rate_limiter.acquire()
                    sub_nonce = f"{parent_nonce}:sub_{idx}_{uuid.uuid4().hex[:8]}" if parent_nonce else secrets.token_hex(16)
                    child_grant = ConsentGrant(
                        action=parent_action,
                        target=parent_target,
                        caller_session=parent_session,
                        nonce=sub_nonce,
                        expiry=float(parent_expiry),
                        method=m.get("method"),
                        path_pattern=m.get("path")
                    )
                    res = self.execute_request(m, dry_run=False, consent=child_grant)
                else:
                    res = self.execute_request(m, dry_run=True, consent=None)

                results.append(res)

                if not effective_dry_run and res["status_code"] > 0:
                    self.rate_limiter.record_response(res["status_code"])

                status_str = f"{GREEN}PASS{RESET}" if res["verdict"] == "PASS" else f"{RED}ALARM{RESET}"
                sys.stdout.write(f"  [{idx:03d}/{len(all_mutations):03d}] {status_str} | HTTP {res['status_code']} ({res['duration_ms']}ms) | {m['name']}\n")
                if res["alarms"]:
                    total_failures += 1
                    for alarm in res["alarms"]:
                        print(f"       👉 {RED}{BOLD}[DEFECT]{RESET} {alarm}")
        finally:
            if not effective_dry_run and parent_nonce:
                clean_p_nonce = str(parent_nonce).strip()
                if hasattr(self.scope_guard, "consumed_nonces"):
                    self.scope_guard.consumed_nonces.add(clean_p_nonce)
                _GLOBAL_CONSUMED_NONCES.add(clean_p_nonce)

        scorecard = {
            "base_url": mask_secrets(self.base_url),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": "ACTIVE",
            "total_mutations": len(all_mutations),
            "total_generated": total_generated,
            "volume_capped": volume_capped,
            "max_requests": self.max_requests,
            "passed": len(all_mutations) - total_failures,
            "failed": total_failures,
            "sla_ms": self.sla_ms,
            "dry_run": dry_run,
            "severity_summary": self._severity_summary(results),
            "results": results
        }

        # Print Summary Scorecard
        print(f"\n{BOLD}======================================================================{RESET}")
        print(f"{BOLD}                   API FUZZING ORACLE SCORECARD                       {RESET}")
        print(f"{BOLD}======================================================================{RESET}")
        print(f"  Mutations Executed: {scorecard['total_mutations']}")
        print(f"  Clean Handled     : {GREEN}{scorecard['passed']}{RESET}")
        print(f"  Defects Detected  : {RED if total_failures > 0 else GREEN}{scorecard['failed']}{RESET}")
        print(f"  Severity Mix      : {scorecard['severity_summary']}")
        if total_failures == 0:
            print(f"  Verdict           : {GREEN}[PASS] API resilient against input fuzzing & chaos.{RESET}")
        else:
            print(f"  Verdict           : {RED}[FAIL] {total_failures} defect alarms detected. Backend fixes required!{RESET}")
        print("======================================================================\n")

        # Save Report
        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_path = os.path.join(REPORTS_DIR, "api_fuzz_report.json")
        with open(report_path, "w", encoding="utf-8") as out_file:
            json.dump(scorecard, out_file, indent=2)
        print(f"Full telemetry report saved to: {report_path}")

        return scorecard

    @staticmethod
    def _severity_summary(results: List[Dict[str, Any]]) -> Dict[str, int]:
        """Counts findings per severity level (ZAP-style risk mix)."""
        summary = {level: 0 for level in SEVERITY_LEVELS}
        for res in results:
            sev = res.get("severity", "INFO")
            if sev in summary:
                summary[sev] += 1
        return summary

    def run_passive_scan(self) -> Dict[str, Any]:
        """Offline spec-level audit (no HTTP dispatched).

        Concept borrowed from OWASP ZAP's passive scanning (Apache-2.0):
        findings are pre-flight advisories derived purely from the OpenAPI/
        Swagger document - unreachable endpoints cannot fake a pass here
        because nothing is dispatched at all.
        """
        spec = self.load_spec()
        has_global_security = bool(spec.get("security"))
        findings: List[Dict[str, Any]] = []

        for path, methods in spec.get("paths", {}).items():
            for method, op in methods.items():
                if method.lower() not in ("get", "post", "put", "patch", "delete"):
                    continue
                op_security = op.get("security") if isinstance(op, dict) else None
                is_protected = has_global_security or bool(op_security)
                label = f"{method.upper()} {path}"

                if not is_protected and method.lower() in ("post", "put", "patch", "delete"):
                    severity = "HIGH" if re.search(r"admin|internal|user", path, re.IGNORECASE) else "MEDIUM"
                    findings.append({
                        "finding": "AUTH_NOT_DECLARED: Mutating endpoint declares no security requirement",
                        "severity": severity,
                        "target": label,
                        "recommendation": "Declare securitySchemes/security for this operation or document why it is public.",
                    })

                if not is_protected and re.search(r"admin|internal", path, re.IGNORECASE):
                    findings.append({
                        "finding": "SENSITIVE_PATH_UNPROTECTED: Administrative/internal path is publicly declared",
                        "severity": "HIGH",
                        "target": label,
                        "recommendation": "Gate this path behind an authentication scheme and network policy.",
                    })

                body = op.get("requestBody", {}) if isinstance(op, dict) else {}
                content = body.get("content", {}).get("application/json", {}) if isinstance(body, dict) else {}
                schema = content.get("schema", {})
                props = schema.get("properties", {}) if isinstance(schema, dict) else {}
                unbounded = [
                    p_name for p_name, p_schema in props.items()
                    if isinstance(p_schema, dict)
                    and p_schema.get("type") == "string"
                    and not any(k in p_schema for k in ("maxLength", "pattern", "enum", "format"))
                ]
                if unbounded:
                    findings.append({
                        "finding": f"NO_INPUT_VALIDATION_DECLARED: unbounded string props {unbounded[:5]}",
                        "severity": "LOW",
                        "target": label,
                        "recommendation": "Add maxLength/pattern/enum constraints so the contract rejects oversized input.",
                    })

        if not spec.get("info") and spec.get("paths"):
            findings.append({
                "finding": "SPEC_METADATA_MISSING: OpenAPI info block absent",
                "severity": "INFO",
                "target": self.spec_path or "inline-spec",
                "recommendation": "Document title/version/contact so scan reports are traceable to an owner.",
            })

        severity_summary = {level: 0 for level in SEVERITY_LEVELS}
        for f in findings:
            severity_summary[f["severity"]] += 1

        blocking = severity_summary["HIGH"] + severity_summary["CRITICAL"]

        print(f"\n{BOLD}{CYAN}======================================================================{RESET}")
        print(f"{BOLD}{CYAN}          API PASSIVE SCAN (Offline Spec Audit - Zero Traffic)        {RESET}")
        print(f"{BOLD}{CYAN}======================================================================{RESET}")
        print(f"  Spec Source        : {self.spec_path or 'Default Archetype'}")
        print(f"  Findings           : {YELLOW if findings else GREEN}{len(findings)}{RESET}")
        print(f"  Severity Mix       : {severity_summary}")
        if blocking:
            print(f"  Verdict            : {RED}[FAIL] {blocking} HIGH/CRITICAL pre-flight finding(s).{RESET}")
        else:
            print(f"  Verdict            : {GREEN}[PASS] No HIGH/CRITICAL spec-level finding.{RESET}")
        print("======================================================================\n")
        for f in findings:
            print(f"  - [{f['severity']}] {f['target']} - {f['finding']}")
            print(f"      👉 {f['recommendation']}")

        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_path = os.path.join(REPORTS_DIR, "api_fuzz_report.json")
        scorecard = {
            "base_url": self.base_url,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": "PASSIVE",
            "spec_source": self.spec_path or "Default Archetype",
            "total_findings": len(findings),
            "severity_summary": severity_summary,
            "findings": findings,
        }
        with open(report_path, "w", encoding="utf-8") as out_file:
            json.dump(scorecard, out_file, indent=2)
        print(f"\nFull telemetry report saved to: {report_path}")

        return scorecard


def main():
    parser = argparse.ArgumentParser(description="Enterprise Autonomous API Fuzzer & Chaos Breaker")
    parser.add_argument("--base-url", default="http://localhost:8080", help="Base URL of target API server")
    parser.add_argument("--spec", default=None, help="Path or URL to OpenAPI/Swagger JSON specification")
    parser.add_argument("--token", default=None, help="Bearer token for authenticated endpoints")
    parser.add_argument("--sla-ms", type=float, default=3000.0, help="SLA latency ceiling in ms (default: 3000ms)")
    parser.add_argument("--mode", choices=["active", "passive"], default="active",
                        help="active = live fuzzing (default); passive = offline spec audit, zero traffic")
    parser.add_argument("--insecure", action="store_true", help="Explicitly bypass TLS certificate verification (for staging/self-signed certs)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate mutation generation without live requests")
    parser.add_argument("--max-requests", type=int, default=500, help="Max requests volume ceiling (default: 500)")
    parser.add_argument("--confirm-pentest-scope", action="store_true", help="Explicit human consent acknowledgement for live fuzzing")
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format")

    args = parser.parse_args()

    headers = {"Content-Type": "application/json", "User-Agent": "AgentQA-Fuzzer/2.0"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    grant = None
    if args.confirm_pentest_scope:
        grant = create_consent_grant(
            action="http:fuzz",
            target=args.base_url,
            caller_session=f"cli_{os.getpid()}",
            ttl_seconds=300
        )

    fuzzer = ApiFuzzer(
        base_url=args.base_url,
        spec_path_or_url=args.spec,
        headers=headers,
        sla_ms=args.sla_ms,
        insecure=args.insecure,
        max_requests=args.max_requests,
        dry_run=args.dry_run,
        consent=grant
    )

    if args.mode == "passive":
        scorecard = fuzzer.run_passive_scan()
        if args.json:
            print(json.dumps(scorecard, indent=2))
        severity_dict = scorecard.get("severity_summary", {})
        blocking = int(severity_dict.get("HIGH", 0)) + int(severity_dict.get("CRITICAL", 0))
        return 1 if blocking > 0 else 0

    scorecard = fuzzer.run_fuzz_suite(dry_run=args.dry_run, consent=grant)
    if args.json:
        print(json.dumps(scorecard, indent=2))

    critical = scorecard["severity_summary"].get("CRITICAL", 0)
    if critical > 0:
        return 1
    return 1 if scorecard["failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
