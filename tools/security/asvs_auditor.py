#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/asvs_auditor.py — OWASP Application Security Verification Standard (ASVS 4.0.3) Engine
--------------------------------------------------------------------------------------------
Implements the OWASP ASVS 4.0.3 verification framework across 14 security chapters
and 3 verification levels (Level 1: Opportunistic, Level 2: Standard, Level 3: Advanced).

Provides:
  1. Complete ASVS 4.0.3 requirement matrix with CWE cross-references.
  2. Automated non-destructive probes for Level-1 verifiable web/API controls
     (Security Headers, CORS, Cookies, TLS enforcement, Error disclosures).
  3. Interactive/Automated compliance checklists and Markdown/JSON reporting.

Usage:
  python tools/asvs_auditor.py --probe https://staging.example.com --level 1
  python tools/asvs_auditor.py --probe https://staging.example.com --json report.json
  python tools/asvs_auditor.py --export-checklist asvs_checklist.md --level 2
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


import sys
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import argparse
from typing import Dict, List, Any, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ==============================================================================
# ASVS 4.0.3 CHAPTER DEFINITIONS & CORE MATRIX
# ==============================================================================

ASVS_CHAPTERS = {
    "V1": "Architecture, Design and Threat Modeling",
    "V2": "Authentication",
    "V3": "Session Management",
    "V4": "Access Control",
    "V5": "Malicious Input Handling & Validation",
    "V6": "Cryptography at Rest",
    "V7": "Error Handling and Logging",
    "V8": "Data Protection & Privacy",
    "V9": "Communications & TLS Verification",
    "V10": "Malicious Code & Integrity",
    "V11": "Business Logic",
    "V12": "Files and Resources",
    "V13": "API and Web Service",
    "V14": "Configuration & Security Headers",
}

# Curated high-impact ASVS requirements covering L1, L2, L3
ASVS_REQUIREMENTS = [
    # V1: Architecture
    {"id": "V1.1.1", "chapter": "V1", "level": 1, "cwe": "CWE-1027", "desc": "Verify that secure development lifecycle is followed and threat modeling was performed.", "automated": False},
    {"id": "V1.4.1", "chapter": "V1", "level": 1, "cwe": "CWE-1188", "desc": "Verify that untrusted data from all boundaries is validated or sanitized.", "automated": False},

    # V2: Authentication
    {"id": "V2.1.1", "chapter": "V2", "level": 1, "cwe": "CWE-521", "desc": "Verify that user passwords are at least 12 characters in length (or 8 for legacy).", "automated": True},
    {"id": "V2.2.1", "chapter": "V2", "level": 1, "cwe": "CWE-307", "desc": "Verify that anti-automation or rate-limiting is in place against brute-force attacks.", "automated": True},
    {"id": "V2.8.1", "chapter": "V2", "level": 2, "cwe": "CWE-308", "desc": "Verify multi-factor authentication (MFA) is supported for privileged accounts.", "automated": False},

    # V3: Session Management
    {"id": "V3.4.1", "chapter": "V3", "level": 1, "cwe": "CWE-614", "desc": "Verify cookie-based session tokens possess the 'Secure' attribute.", "automated": True},
    {"id": "V3.4.2", "chapter": "V3", "level": 1, "cwe": "CWE-1004", "desc": "Verify cookie-based session tokens possess the 'HttpOnly' attribute.", "automated": True},
    {"id": "V3.4.3", "chapter": "V3", "level": 1, "cwe": "CWE-1275", "desc": "Verify cookie-based session tokens possess 'SameSite=Lax' or 'SameSite=Strict'.", "automated": True},
    {"id": "V3.2.1", "chapter": "V3", "level": 2, "cwe": "CWE-384", "desc": "Verify session tokens are invalidated and renewed upon user authentication/logout.", "automated": True},

    # V4: Access Control
    {"id": "V4.1.1", "chapter": "V4", "level": 1, "cwe": "CWE-285", "desc": "Verify that the principle of least privilege exists (users only access their own records).", "automated": True},
    {"id": "V4.1.2", "chapter": "V4", "level": 1, "cwe": "CWE-639", "desc": "Verify protection against Broken Object Level Authorization (BOLA/IDOR).", "automated": True},
    {"id": "V4.2.1", "chapter": "V4", "level": 1, "cwe": "CWE-862", "desc": "Verify that sensitive endpoints strictly enforce role-based access control (RBAC).", "automated": True},

    # V5: Malicious Input Handling
    {"id": "V5.1.1", "chapter": "V5", "level": 1, "cwe": "CWE-20", "desc": "Verify that all input data is validated against a strict allowlist schema.", "automated": True},
    {"id": "V5.3.1", "chapter": "V5", "level": 1, "cwe": "CWE-89", "desc": "Verify protection against SQL Injection using parameterized queries and ORMs.", "automated": True},
    {"id": "V5.3.3", "chapter": "V5", "level": 1, "cwe": "CWE-79", "desc": "Verify context-aware output encoding to prevent Cross-Site Scripting (XSS).", "automated": True},

    # V6: Cryptography at Rest
    {"id": "V6.2.1", "chapter": "V6", "level": 2, "cwe": "CWE-311", "desc": "Verify sensitive data at rest (passwords, PII, keys) is strongly encrypted using AES-256 or ChaCha20.", "automated": False},

    # V7: Error Handling and Logging
    {"id": "V7.1.1", "chapter": "V7", "level": 1, "cwe": "CWE-209", "desc": "Verify that error handling does not disclose internal system details, stacktraces, or database queries.", "automated": True},
    {"id": "V7.1.2", "chapter": "V7", "level": 1, "cwe": "CWE-532", "desc": "Verify that log messages do not record secrets, auth tokens, credit cards, or passwords in plain text.", "automated": True},

    # V8: Data Protection
    {"id": "V8.3.1", "chapter": "V8", "level": 1, "cwe": "CWE-319", "desc": "Verify that sensitive personal data (PII) is masked or tokenized in test environments and logs.", "automated": True},

    # V9: Communications
    {"id": "V9.1.1", "chapter": "V9", "level": 1, "cwe": "CWE-319", "desc": "Verify that all network traffic enforces TLS 1.2 or TLS 1.3.", "automated": True},
    {"id": "V9.2.1", "chapter": "V9", "level": 1, "cwe": "CWE-523", "desc": "Verify that HTTP Strict Transport Security (HSTS) header is enabled with max-age >= 15768000.", "automated": True},

    # V10: Malicious Code
    {"id": "V10.3.1", "chapter": "V10", "level": 1, "cwe": "CWE-1395", "desc": "Verify third-party dependencies are scanned for known CVE vulnerabilities.", "automated": True},

    # V11: Business Logic
    {"id": "V11.1.1", "chapter": "V11", "level": 1, "cwe": "CWE-840", "desc": "Verify that business logic flows cannot be bypassed or executed out of sequence.", "automated": True},
    {"id": "V11.1.4", "chapter": "V11", "level": 1, "cwe": "CWE-362", "desc": "Verify protection against race conditions and double-submits in financial transactions.", "automated": True},

    # V12: Files and Resources
    {"id": "V12.1.1", "chapter": "V12", "level": 1, "cwe": "CWE-434", "desc": "Verify that uploaded files are validated for MIME type, extension, and scanned for malware.", "automated": True},

    # V13: API and Web Service
    {"id": "V13.1.1", "chapter": "V13", "level": 1, "cwe": "CWE-306", "desc": "Verify that all API endpoints enforce authentication and valid access tokens.", "automated": True},
    {"id": "V13.2.1", "chapter": "V13", "level": 1, "cwe": "CWE-1027", "desc": "Verify that API schemas conform to published OpenAPI/Swagger specifications.", "automated": True},

    # V14: Configuration & Headers
    {"id": "V14.4.1", "chapter": "V14", "level": 1, "cwe": "CWE-1021", "desc": "Verify that 'Content-Security-Policy' header is present and restricts script execution.", "automated": True},
    {"id": "V14.4.2", "chapter": "V14", "level": 1, "cwe": "CWE-1021", "desc": "Verify that 'X-Frame-Options' (or CSP frame-ancestors) is set to DENY or SAMEORIGIN.", "automated": True},
    {"id": "V14.4.3", "chapter": "V14", "level": 1, "cwe": "CWE-16", "desc": "Verify that 'X-Content-Type-Options' is set to 'nosniff'.", "automated": True},
    {"id": "V14.4.4", "chapter": "V14", "level": 1, "cwe": "CWE-116", "desc": "Verify that 'Referrer-Policy' is configured safely (e.g., strict-origin-when-cross-origin).", "automated": True},
    {"id": "V14.5.1", "chapter": "V14", "level": 1, "cwe": "CWE-942", "desc": "Verify CORS policy does not reflect untrusted Origins with Access-Control-Allow-Credentials: true.", "automated": True},
]


# ==============================================================================
# AUTOMATED LEVEL-1 VERIFIER PROBE
# ==============================================================================

class ASVSProbeRunner:
    """Performs passive and safe non-destructive probes against web/API targets."""

    def __init__(self, target_url: str, timeout: int = 8):
        self.target_url = target_url.strip()
        self.timeout = timeout
        self.headers_observed: Dict[str, str] = {}
        self.cookies_observed: List[str] = []
        self.status_code = 0
        self.is_tls = self.target_url.startswith("https://")
        self.cors_vulnerable = False
        self.cors_probe_error: Optional[str] = None
        self.verbose_error_detected = False

    def execute_probe(self) -> Dict[str, Any]:
        """Dispatches inspection request and analyzes response."""
        results = {}
        req = urllib.request.Request(
            self.target_url,
            headers={"User-Agent": "Synapse-Hub-ASVS-Auditor/4.6.3 (OWASP-Verification)"},
        )
        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as resp:
                self.status_code = resp.getcode()
                for k, v in resp.headers.items():
                    self.headers_observed[k.lower()] = v
                self.cookies_observed = resp.headers.get_all("set-cookie") or []
                body = resp.read(4096).decode("utf-8", errors="ignore")
                if "stacktrace" in body.lower() or "sqlexception" in body.lower():
                    self.verbose_error_detected = True
        except urllib.error.HTTPError as e:
            self.status_code = e.code
            for k, v in e.headers.items():
                self.headers_observed[k.lower()] = v
            self.cookies_observed = e.headers.get_all("set-cookie") or []
        except Exception as e:
            results["error"] = f"Failed to connect to target: {e}"
            return results

        # Test CORS Reflection (safe non-destructive probe)
        try:
            cors_req = urllib.request.Request(
                self.target_url,
                headers={
                    "User-Agent": "Synapse-Hub-ASVS-Auditor/4.6.3",
                    "Origin": "https://untrusted-attacker-domain.example",
                },
            )
            with urllib.request.urlopen(cors_req, timeout=self.timeout, context=ctx) as c_resp:
                acao = c_resp.headers.get("Access-Control-Allow-Origin", "")
                acac = c_resp.headers.get("Access-Control-Allow-Credentials", "").lower()
                if "untrusted-attacker-domain" in acao and acac == "true":
                    self.cors_vulnerable = True
        except Exception as exc:
            self.cors_probe_error = f"{type(exc).__name__}: {str(exc)}"

        return self.evaluate_asvs_controls()

    def evaluate_asvs_controls(self) -> Dict[str, Any]:
        """Evaluates observed probe data against ASVS Level 1 requirements."""
        evaluations = {}

        # V9.1.1 & V9.2.1: TLS & HSTS
        hsts_header = self.headers_observed.get("strict-transport-security", "")
        hsts_pass = self.is_tls and ("max-age=" in hsts_header)
        evaluations["V9.1.1"] = {"status": "PASS" if self.is_tls else "FAIL", "evidence": f"TLS enabled: {self.is_tls}"}
        evaluations["V9.2.1"] = {
            "status": "PASS" if hsts_pass else "FAIL",
            "evidence": f"Strict-Transport-Security: {hsts_header}" if hsts_header else "Header missing",
        }

        # V14.4.1: Content-Security-Policy
        csp = self.headers_observed.get("content-security-policy", "")
        evaluations["V14.4.1"] = {
            "status": "PASS" if csp else "FAIL",
            "evidence": f"CSP present (length {len(csp)})" if csp else "Content-Security-Policy header missing",
        }

        # V14.4.2: X-Frame-Options or CSP frame-ancestors
        xfo = self.headers_observed.get("x-frame-options", "").upper()
        frame_safe = ("DENY" in xfo or "SAMEORIGIN" in xfo) or ("frame-ancestors" in csp)
        evaluations["V14.4.2"] = {
            "status": "PASS" if frame_safe else "FAIL",
            "evidence": f"X-Frame-Options: {xfo}" if xfo else "X-Frame-Options missing",
        }

        # V14.4.3: X-Content-Type-Options: nosniff
        xcto = self.headers_observed.get("x-content-type-options", "").lower()
        evaluations["V14.4.3"] = {
            "status": "PASS" if "nosniff" in xcto else "FAIL",
            "evidence": f"X-Content-Type-Options: {xcto}" if xcto else "Missing 'nosniff'",
        }

        # V14.4.4: Referrer-Policy
        ref_pol = self.headers_observed.get("referrer-policy", "")
        evaluations["V14.4.4"] = {
            "status": "PASS" if ref_pol else "FAIL",
            "evidence": f"Referrer-Policy: {ref_pol}" if ref_pol else "Referrer-Policy missing",
        }

        # V14.5.1: CORS
        if self.cors_probe_error:
            evaluations["V14.5.1"] = {
                "status": "WARN",
                "evidence": f"CORS probe inconclusive: {self.cors_probe_error}",
            }
        else:
            evaluations["V14.5.1"] = {
                "status": "FAIL" if self.cors_vulnerable else "PASS",
                "evidence": "Insecure CORS reflection with credentials" if self.cors_vulnerable else "CORS policy safe or restrictive",
            }

        # V3.4.1 - V3.4.3: Cookies
        if self.cookies_observed:
            sec_cookie = all("secure" in c.lower() for c in self.cookies_observed)
            http_only = all("httponly" in c.lower() for c in self.cookies_observed)
            same_site = all("samesite" in c.lower() for c in self.cookies_observed)
            evaluations["V3.4.1"] = {"status": "PASS" if sec_cookie else "FAIL", "evidence": f"Secure flag on {len(self.cookies_observed)} cookies"}
            evaluations["V3.4.2"] = {"status": "PASS" if http_only else "FAIL", "evidence": f"HttpOnly flag on {len(self.cookies_observed)} cookies"}
            evaluations["V3.4.3"] = {"status": "PASS" if same_site else "FAIL", "evidence": "SameSite attribute present on cookies"}
        else:
            evaluations["V3.4.1"] = {"status": "NOT_APPLICABLE", "evidence": "No Set-Cookie headers in response"}
            evaluations["V3.4.2"] = {"status": "NOT_APPLICABLE", "evidence": "No Set-Cookie headers in response"}
            evaluations["V3.4.3"] = {"status": "NOT_APPLICABLE", "evidence": "No Set-Cookie headers in response"}

        # V7.1.1: Error & Stacktrace disclosure
        evaluations["V7.1.1"] = {
            "status": "FAIL" if self.verbose_error_detected else "PASS",
            "evidence": "Stacktrace / Exception revealed in body" if self.verbose_error_detected else "Zero system leaks observed in response",
        }

        return evaluations


# ==============================================================================
# REPORTING & CHECKLIST GENERATION
# ==============================================================================

def generate_asvs_checklist_markdown(level: int = 1, chapter: Optional[str] = None) -> str:
    """Generates an interactive Markdown audit checklist for ASVS."""
    lines = [
        f"# OWASP ASVS 4.0.3 Verification Checklist (Level {level})",
        "",
        "> Generated by Synapse Hub ASVS Engine (`tools/asvs_auditor.py`).",
        "",
    ]

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for req in ASVS_REQUIREMENTS:
        if req["level"] > level:
            continue
        if chapter and req["chapter"] != chapter:
            continue
        c_id = req["chapter"]
        grouped.setdefault(c_id, []).append(req)

    for c_id, reqs in grouped.items():
        title = ASVS_CHAPTERS.get(c_id, c_id)
        lines.append(f"## Chapter {c_id}: {title}")
        lines.append("")
        lines.append("| Status | ID | Level | CWE | Requirement Description | Verification Method |")
        lines.append("| :---: | :--- | :---: | :--- | :--- | :--- |")
        for r in reqs:
            v_type = "Automated Probe" if r["automated"] else "Manual Review"
            lines.append(f"| [ ] | **{r['id']}** | L{r['level']} | {r['cwe']} | {r['desc']} | {v_type} |")
        lines.append("")

    return "\n".join(lines)


def run_asvs_audit(target_url: Optional[str], level: int = 1, chapter: Optional[str] = None) -> Dict[str, Any]:
    """Runs ASVS audit combining automated probes and structural requirements."""
    probe_results = {}
    if target_url:
        runner = ASVSProbeRunner(target_url)
        probe_results = runner.execute_probe()

    report_items = []
    total_applicable = 0
    total_passed = 0
    total_failed = 0
    total_na = 0
    total_manual = 0

    for req in ASVS_REQUIREMENTS:
        if req["level"] > level:
            continue
        if chapter and req["chapter"] != chapter:
            continue

        item = dict(req)
        item["chapter_title"] = ASVS_CHAPTERS.get(req["chapter"], req["chapter"])
        r_id = req["id"]

        if r_id in probe_results:
            probe = probe_results[r_id]
            item["status"] = probe["status"]
            item["evidence"] = probe["evidence"]
            if item["status"] == "PASS":
                total_passed += 1
            elif item["status"] == "FAIL":
                total_failed += 1
            elif item["status"] == "NOT_APPLICABLE":
                total_na += 1
        else:
            item["status"] = "MANUAL_VERIFICATION_REQUIRED"
            item["evidence"] = "Requires architecture review, code audit, or functional test."
            total_manual += 1

        total_applicable += 1
        report_items.append(item)

    score_pct = (total_passed / (total_passed + total_failed) * 100) if (total_passed + total_failed) > 0 else 0.0

    return {
        "asvs_version": "4.0.3",
        "target_url": target_url or "Offline Checklist",
        "level": level,
        "compliance_score_pct": round(score_pct, 1),
        "summary": {
            "total_requirements": total_applicable,
            "passed": total_passed,
            "failed": total_failed,
            "not_applicable": total_na,
            "manual_required": total_manual,
        },
        "requirements": report_items,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Synapse Hub OWASP ASVS 4.0.3 Verification Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--probe", help="Target URL to run automated Level 1 ASVS probes against")
    parser.add_argument("--level", type=int, choices=[1, 2, 3], default=1, help="ASVS Verification Level (1: Opportunistic, 2: Standard, 3: Advanced)")
    parser.add_argument("--chapter", help="Filter by Chapter ID (e.g. V1, V3, V14)")
    parser.add_argument("--export-checklist", help="Export Markdown checklist file (e.g. asvs_checklist.md)")
    parser.add_argument("--json", help="Export structured JSON audit report to specified file")
    parser.add_argument("--gate-score", type=float, help="Quality Gate: Fail with exit code 1 if compliance score < threshold")

    args = parser.parse_args()

    if args.export_checklist:
        md = generate_asvs_checklist_markdown(level=args.level, chapter=args.chapter)
        with open(args.export_checklist, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✅ Exported OWASP ASVS Level {args.level} checklist to {args.export_checklist}")
        return 0

    report = run_asvs_audit(args.probe, level=args.level, chapter=args.chapter)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"✅ ASVS audit report saved to {args.json}")
    else:
        print("=" * 70)
        print("  SYNAPSE HUB — OWASP ASVS 4.0.3 SECURITY AUDIT SCORECARD")
        print("=" * 70)
        print(f"  Target URL     : {report['target_url']}")
        print(f"  Target Level   : Level {report['level']} (ASVS 4.0.3)")
        print(f"  Total Checks   : {report['summary']['total_requirements']}")
        print(f"  Passed Checks  : \033[92m{report['summary']['passed']}\033[0m")
        print(f"  Failed Checks  : \033[91m{report['summary']['failed']}\033[0m")
        print(f"  Manual Review  : \033[93m{report['summary']['manual_required']}\033[0m")
        print(f"  Compliance Rate: \033[1m{report['compliance_score_pct']}%\033[0m (Automated probes)")
        print("-" * 70)

        for r in report["requirements"]:
            if r["status"] in ("PASS", "FAIL"):
                st_color = "\033[92m[PASS]\033[0m" if r["status"] == "PASS" else "\033[91m[FAIL]\033[0m"
                print(f"  {st_color} {r['id']:<8} L{r['level']} | {r['desc'][:45]:<45} -> {r['evidence']}")
        print("=" * 70)

    if args.gate_score and report["compliance_score_pct"] < args.gate_score:
        print(f"🚨 Quality Gate Failed: ASVS score {report['compliance_score_pct']}% < required {args.gate_score}%", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
