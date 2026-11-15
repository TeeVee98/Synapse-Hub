#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Enterprise ALM & TMS Sync Bridge (Jira / Xray / Zephyr / TestRail)
------------------------------------------------------------------
Bi-directional synchronization bridge connecting autonomous QA agents with
Enterprise Test Management Systems:
  1. Pull Mode (Inward):
     - Pulls User Stories, Acceptance Criteria (Given-When-Then / Gherkin),
       and Test Cases directly from Jira Issues, Xray, or TestRail v2.
     - Formats them into standardized prompt contexts for Clean POM test generation.
  2. Push Mode (Outward Defect Reporter):
     - Automatically creates detailed Bug Tickets on Jira/Xray or flags defects in TestRail.
     - Attaches failure stack traces, repro steps, links to Screenshots/FAILED_*.png,
       video recordings, console error logs, and environment metadata.
  3. Execution Run Sync:
     - Reports bulk test execution outcomes (PASS / FAIL / BLOCKED, execution time)
       back to Jira Xray (/api/v2/import/execution) or TestRail v2 (/api/v2/add_result_for_case).
  4. Enterprise Security & Authentication:
     - Supports OAuth2 Bearer Tokens (JWT, Personal Access Tokens) alongside Basic Auth.
  5. Offline / Mock & Dry-Run Support:
     - Fully functional offline simulation for CI pipelines and test suites without
       requiring live enterprise credentials.
"""

import os
import sys
import json
import base64
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QA_HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def text_to_adf(text: str) -> Dict[str, Any]:
    """Converts a raw string into Atlassian Document Format (ADF) JSON for Jira Cloud API v3."""
    paragraphs = []
    for block in (text or "").split("\n\n"):
        block = block.strip()
        if not block:
            continue
        paragraphs.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": block}]
        })
    if not paragraphs:
        paragraphs = [{"type": "paragraph", "content": [{"type": "text", "text": "No content provided."}]}]
    return {
        "type": "doc",
        "version": 1,
        "content": paragraphs
    }


def adf_to_text(adf_data: Any) -> str:
    """Extracts plain text recursively from Atlassian Document Format (ADF) JSON."""
    if not isinstance(adf_data, dict):
        return str(adf_data) if adf_data is not None else ""
    text_parts: List[str] = []

    def _extract(node: Any):
        if isinstance(node, dict):
            node_type = node.get("type")
            if node_type == "text" and "text" in node:
                text_parts.append(node["text"])
            elif node_type == "hardBreak":
                text_parts.append("\n")
            for child in node.get("content", []):
                _extract(child)
            if node_type in ("paragraph", "heading", "listItem", "codeBlock"):
                text_parts.append("\n")
        elif isinstance(node, list):
            for item in node:
                _extract(item)

    _extract(adf_data)
    return "".join(text_parts).strip()


def build_jira_v3_adf_description(
    test_case_id: str,
    error_message: str,
    reproduction_steps: List[str],
    stack_trace: str = "",
) -> Dict[str, Any]:
    """
    Constructs compliant Atlassian Document Format (ADF) JSON for Jira Cloud REST API v3 (/rest/api/3/issue).
    Prevents HTTP 400 Bad Request: 'Operation value must be an Atlassian Document (ADF)'.
    Guarantees all text nodes are non-empty strings (ADF schema requirement: minLength 1).
    """
    tc_clean = (test_case_id or "").strip() or "UNKNOWN_TEST"
    err_clean = (error_message or "").strip() or "Unknown error"

    raw_steps = reproduction_steps if reproduction_steps is not None else []
    clean_steps = [s.strip() for s in raw_steps if isinstance(s, str) and s.strip()]
    if not clean_steps:
        clean_steps = ["Execute automated test scenario."]

    content: List[Dict[str, Any]] = [
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Failing Test Case: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": tc_clean},
            ],
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Error Message:", "marks": [{"type": "strong"}]},
            ],
        },
        {
            "type": "codeBlock",
            "attrs": {"language": "text"},
            "content": [{"type": "text", "text": err_clean}],
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Reproduction Steps:", "marks": [{"type": "strong"}]},
            ],
        },
        {
            "type": "orderedList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": step}]}
                    ],
                }
                for step in clean_steps
            ],
        },
    ]

    st_clean = (stack_trace or "").strip()
    if st_clean:
        content.extend([
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Stack Trace:", "marks": [{"type": "strong"}]},
                ],
            },
            {
                "type": "codeBlock",
                "attrs": {"language": "text"},
                "content": [{"type": "text", "text": st_clean}],
            },
        ])

    return {
        "type": "doc",
        "version": 1,
        "content": content,
    }


class TMSBridge:
    """Enterprise Test Management System Adapter."""

    def __init__(
        self,
        provider: str = "jira",
        base_url: str = "",
        api_token: str = "",
        user_email: str = "",
        auth_type: str = "auto",
    ):
        self.provider = provider.lower().strip()
        resolved_url = (
            base_url
            or os.getenv("JIRA_URL")
            or os.getenv("TESTRAIL_URL")
            or os.getenv("XRAY_BASE_URL")
            or os.getenv("TMS_BASE_URL")
            or ""
        )
        resolved_token = (
            api_token
            or os.getenv("JIRA_API_TOKEN")
            or os.getenv("TESTRAIL_API_KEY")
            or os.getenv("TESTRAIL_API_TOKEN")
            or os.getenv("XRAY_API_TOKEN")
            or os.getenv("TMS_API_TOKEN")
            or ""
        )
        resolved_email = (
            user_email
            or os.getenv("JIRA_USER_EMAIL")
            or os.getenv("TESTRAIL_USER_EMAIL")
            or os.getenv("TMS_USER_EMAIL")
            or ""
        )
        resolved_auth_type = auth_type if auth_type != "auto" else (os.getenv("TMS_AUTH_TYPE") or "auto")

        # Use mock simulation if URL is omitted, mock is specified, or token is absent
        if not resolved_url or "mock" in resolved_url or not resolved_token:
            self.base_url = "https://mock-alm.enterprise.local"
            self.api_token = "mock_token_12345"
            self.user_email = resolved_email or "qa-agent@enterprise.local"
            self.auth_type = "basic"
            self.is_mock = True
        else:
            self.base_url = resolved_url.rstrip("/")
            self.api_token = resolved_token
            self.user_email = resolved_email
            self.is_mock = False

            if resolved_auth_type != "auto":
                self.auth_type = resolved_auth_type.lower()
            elif resolved_token.startswith("Bearer ") or len(resolved_token) > 100 or not resolved_email:
                self.auth_type = "bearer"
            else:
                self.auth_type = "basic"

    def get_auth_headers(self) -> Dict[str, str]:
        """Generates HTTP authorization headers supporting Bearer Token, OAuth2, and Basic Auth."""
        headers = {"Accept": "application/json"}
        if self.auth_type in ("bearer", "oauth2") or self.api_token.startswith("Bearer "):
            tok = self.api_token[7:].strip() if self.api_token.startswith("Bearer ") else self.api_token.strip()
            headers["Authorization"] = f"Bearer {tok}"
        else:
            auth_str = f"{self.user_email}:{self.api_token}".encode("utf-8")
            headers["Authorization"] = f"Basic {base64.b64encode(auth_str).decode('utf-8')}"
        return headers

    def _testrail_url(self, path: str) -> str:
        """Normalizes TestRail API v2 endpoint URL preventing duplicated path fragments."""
        base = self.base_url.rstrip("/")
        if "/index.php" in base:
            base = base.split("/index.php")[0]
        elif base.endswith("/api/v2"):
            base = base[:-7]
        clean_path = path.lstrip("/")
        return f"{base}/index.php?/api/v2/{clean_path}"

    def _xray_url(self, path: str) -> str:
        """Normalizes Xray endpoint URL supporting Cloud and DC/Server."""
        base = self.base_url.rstrip("/")
        is_cloud = "cloud" in base or "getxray.app" in base
        clean_path = path.lstrip("/")
        if is_cloud:
            if base.endswith("/api/v2"):
                base = base[:-7]
            return f"{base}/api/v2/{clean_path}"
        else:
            if base.endswith("/rest/raven/1.0"):
                base = base[:-15]
            return f"{base}/rest/raven/1.0/{clean_path}"

    def _execute_request(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 15.0,
    ) -> Dict[str, Any]:
        """Executes an authenticated JSON HTTP request with strict error handling."""
        req_headers = self.get_auth_headers()
        if headers:
            req_headers.update(headers)

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")
            req_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
                resp_content = resp.read().decode("utf-8")
                if not resp_content.strip():
                    return {"status_code": resp.status, "message": "OK (empty body)"}
                try:
                    return json.loads(resp_content)
                except json.JSONDecodeError:
                    return {"status_code": resp.status, "raw": resp_content}
        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8")
            except Exception as read_err:
                err_body = f"<unreadable error body: {read_err}>"
            err_msg = f"HTTP Error {exc.code}: {exc.reason}"
            if err_body:
                err_msg += f" - Response: {err_body}"
            raise RuntimeError(err_msg) from exc

    # -------------------------------------------------------------------------
    # 1. PULL MODE: Extract User Story & Acceptance Criteria
    # -------------------------------------------------------------------------
    def pull_story_acceptance_criteria(self, issue_key: str) -> Dict[str, Any]:
        """
        Pulls User Story details, acceptance criteria, and technical specifications
        by Issue Key (e.g. 'PROJ-1042' or TestRail case 'C1042').
        """
        issue_key_clean = issue_key.strip().upper()

        if self.is_mock:
            return {
                "issue_key": issue_key_clean,
                "summary": f"Automated Invoice Reconciliation for {issue_key_clean}",
                "issue_type": "Story",
                "status": "Ready for QA",
                "assignee": self.user_email,
                "description": "As an Enterprise Accountant, I want to reconcile invoices matching ERP records to ensure financial accuracy.",
                "acceptance_criteria": [
                    "Given the accountant is logged in with FINANCE_ROLE",
                    "When navigating to '/billing/invoices' and filtering by date '2026-10-01'",
                    "Then invoice table displays matching records with status 'MATCHED'",
                    "And total amount reconciles with zero discrepancy"
                ],
                "gherkin_feature": (
                    f"Feature: Invoice Reconciliation ({issue_key_clean})\n"
                    f"  Scenario: Successful matching of monthly invoices\n"
                    f"    Given user is authenticated with 'FINANCE_ROLE'\n"
                    f"    When filtering invoices by '2026-10-01'\n"
                    f"    Then status badge displays 'MATCHED'\n"
                ),
                "labels": ["Billing", "Automated-E2E", "Finance"],
                "source": f"Mock ALM Adapter ({self.provider})"
            }

        # TestRail v2 Pull Integration
        if self.provider == "testrail":
            clean_case_id = issue_key_clean.lstrip("C")
            try:
                case_int = int(clean_case_id)
                data = self.testrail_get_case(case_int)
                summary = data.get("title", f"TestRail Case C{case_int}")
                desc_str = data.get("custom_preconds", "") or data.get("custom_steps", "") or ""
                ac_lines = [step.strip() for step in str(desc_str).splitlines() if step.strip()]
                return {
                    "issue_key": f"C{case_int}",
                    "summary": summary,
                    "issue_type": "TestCase",
                    "status": "Active",
                    "assignee": self.user_email,
                    "description": str(desc_str),
                    "acceptance_criteria": ac_lines,
                    "labels": ["TestRail", f"Section-{data.get('section_id')}"],
                    "source": f"Live TestRail API ({self.base_url})"
                }
            except Exception as e:
                return {
                    "error": f"Failed to pull TestRail case {issue_key_clean}: {str(e)}",
                    "issue_key": issue_key_clean,
                    "source": "Live TestRail API (Error Fallback)"
                }

        # Live Jira / Xray REST API Integration
        try:
            endpoint = f"{self.base_url}/rest/api/3/issue/{issue_key_clean}"
            data = self._execute_request(endpoint, method="GET")

            fields = data.get("fields", {})
            desc_raw = fields.get("description", "")
            summary = fields.get("summary", "")

            # Convert ADF dict if Jira Cloud API v3 returned document
            desc_str = adf_to_text(desc_raw) if isinstance(desc_raw, dict) else (desc_raw if isinstance(desc_raw, str) else str(desc_raw))

            # Extract Acceptance Criteria if present in text
            ac_lines = []
            for line in desc_str.splitlines():
                if any(line.strip().startswith(kw) for kw in ("Given", "When", "Then", "And", "*", "-")):
                    ac_lines.append(line.strip())

            return {
                "issue_key": issue_key_clean,
                "summary": summary,
                "issue_type": fields.get("issuetype", {}).get("name", "Story"),
                "status": fields.get("status", {}).get("name", "Open"),
                "assignee": fields.get("assignee", {}).get("displayName", "Unassigned"),
                "description": desc_str,
                "acceptance_criteria": ac_lines,
                "labels": fields.get("labels", []),
                "source": f"Live {self.provider.upper()} API ({self.base_url})"
            }
        except Exception as e:
            return {
                "error": f"Failed to pull story {issue_key_clean}: {str(e)}",
                "issue_key": issue_key_clean,
                "source": f"Live {self.provider.upper()} API (Error Fallback)"
            }

    # -------------------------------------------------------------------------
    # 2. PUSH MODE: Automated Bug Ticket Creation on Test Failure
    # -------------------------------------------------------------------------
    def report_defect(
        self,
        project_key: str,
        test_case_id: str,
        summary: str,
        error_message: str,
        stack_trace: str = "",
        screenshot_path: str = "",
        reproduction_steps: Optional[List[str]] = None,
        severity: str = "High"
    ) -> Dict[str, Any]:
        """
        Creates an actionable Bug Ticket in Jira/Xray or flags failure in TestRail.
        """
        proj_clean = project_key.strip().upper()
        bug_key = f"{proj_clean}-BUG-{int(datetime.now().timestamp()) % 10000}"

        repro = reproduction_steps or [
            "1. Launch headless browser session via Playwright Live.",
            "2. Navigate to target application flow under test.",
            f"3. Execute test action sequence for '{test_case_id}'.",
            f"4. Observe failure: {error_message}"
        ]

        ticket_payload = {
            "ticket_key": bug_key,
            "project": proj_clean,
            "issue_type": "Bug",
            "summary": f"[AUT-DEFECT] {test_case_id}: {summary}",
            "severity": severity,
            "test_case_id": test_case_id,
            "error_message": error_message,
            "reproduction_steps": repro,
            "stack_trace": stack_trace,
            "screenshot_attachment": screenshot_path,
            "environment": {
                "runner": "Playwright / Headless",
                "os": sys.platform,
                "timestamp": datetime.now().isoformat()
            },
            "status": "Created",
            "mode": "MOCK_SIMULATION" if self.is_mock else f"LIVE_{self.provider.upper()}"
        }

        if self.is_mock:
            return ticket_payload

        # TestRail Defect Reporting via /api/v2/add_result_for_case
        if self.provider == "testrail":
            clean_case_id = "".join([c for c in test_case_id if c.isdigit()])
            if clean_case_id:
                try:
                    case_int = int(clean_case_id)
                    comment = f"Automated Failure: {summary}\nError: {error_message}\nStack Trace:\n{stack_trace}"
                    run_id = int(os.getenv("TESTRAIL_RUN_ID", "1"))
                    res = self.testrail_add_result_for_case(
                        run_id=run_id,
                        case_id=case_int,
                        status_id=5,  # 5 = Failed in TestRail
                        comment=comment,
                    )
                    ticket_payload["ticket_key"] = f"TR-RESULT-{res.get('id', case_int)}"
                    ticket_payload["status"] = "Submitted"
                    return ticket_payload
                except Exception as e:
                    ticket_payload["live_error"] = str(e)
                    ticket_payload["status"] = "Drafted (Offline Fallback)"
                    return ticket_payload
            else:
                ticket_payload["live_error"] = f"TestRail requires a numeric Case ID (e.g. C123), but '{test_case_id}' contains no digits."
                ticket_payload["status"] = "Drafted (Offline Fallback)"
                return ticket_payload

        # Live Jira & Xray Bug Creation
        try:
            endpoint = f"{self.base_url}/rest/api/3/issue"
            adf_desc = build_jira_v3_adf_description(
                test_case_id=test_case_id,
                error_message=error_message,
                reproduction_steps=repro,
                stack_trace=stack_trace,
            )
            body = {
                "fields": {
                    "project": {"key": proj_clean},
                    "summary": ticket_payload["summary"],
                    "issuetype": {"name": "Bug"},
                    "description": adf_desc,
                    "labels": ["Automated-Failure", "AI-Reported", "Playwright"]
                }
            }

            res_data = self._execute_request(endpoint, method="POST", data=body)
            ticket_payload["ticket_key"] = res_data.get("key", bug_key)
            ticket_payload["status"] = "Submitted"
        except Exception as e:
            ticket_payload["live_error"] = str(e)
            ticket_payload["status"] = "Drafted (Offline Fallback)"

        return ticket_payload

    # -------------------------------------------------------------------------
    # 3. TESTRAIL v2 REST ADAPTERS
    # -------------------------------------------------------------------------
    def testrail_get_tests(self, run_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves tests for a TestRail test run via GET /api/v2/get_tests/{run_id}.
        """
        if self.is_mock:
            return [
                {"id": 1, "case_id": 101, "title": "Verify User Authentication", "status_id": 1},
                {"id": 2, "case_id": 102, "title": "Verify Invoice Matching", "status_id": 1},
                {"id": 3, "case_id": 103, "title": "Verify Payment Gateway", "status_id": 5},
            ]

        endpoint = self._testrail_url(f"get_tests/{run_id}")
        resp = self._execute_request(endpoint, method="GET")
        if isinstance(resp, list):
            return resp
        return resp.get("tests", [])

    def testrail_get_case(self, case_id: int) -> Dict[str, Any]:
        """
        Retrieves a test case from TestRail via GET /api/v2/get_case/{case_id}.
        """
        if self.is_mock:
            return {
                "id": case_id,
                "title": f"TestRail Test Case C{case_id}",
                "section_id": 42,
                "type_id": 1,
                "priority_id": 2,
                "custom_preconds": "Given user is on login page",
                "custom_steps": "When entering valid credentials\nThen dashboard opens",
            }

        endpoint = self._testrail_url(f"get_case/{case_id}")
        return self._execute_request(endpoint, method="GET")

    def testrail_add_result_for_case(
        self,
        run_id: int,
        case_id: int,
        status_id: int = 1,
        comment: str = "",
        elapsed: str = "",
        defects: str = "",
    ) -> Dict[str, Any]:
        """
        Submits a test result to TestRail via POST /api/v2/add_result_for_case/{run_id}/{case_id}.
        Status IDs: 1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed.
        """
        if self.is_mock:
            return {
                "id": 1000 + case_id,
                "test_id": 500 + case_id,
                "status_id": status_id,
                "created_on": int(datetime.now().timestamp()),
                "assignedto_id": None,
                "comment": comment or "Result submitted autonomously by Synapse Hub",
                "version": "1.0",
                "elapsed": elapsed or "1s",
                "defects": defects,
            }

        endpoint = self._testrail_url(f"add_result_for_case/{run_id}/{case_id}")
        payload: Dict[str, Any] = {"status_id": status_id}
        if comment:
            payload["comment"] = comment
        if elapsed:
            payload["elapsed"] = elapsed
        if defects:
            payload["defects"] = defects

        return self._execute_request(endpoint, method="POST", data=payload)

    # -------------------------------------------------------------------------
    # 4. JIRA XRAY REST ADAPTERS
    # -------------------------------------------------------------------------
    def xray_import_execution(
        self,
        test_execution_key: Optional[str] = None,
        tests: Optional[List[Dict[str, Any]]] = None,
        summary: str = "",
        test_environments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Imports execution results into Jira Xray via REST API:
        Cloud: POST /api/v2/import/execution
        Server/DC: POST /rest/raven/1.0/import/execution
        """
        tests_payload = tests or []
        if self.is_mock:
            return {
                "testExecIssue": {
                    "id": "10400",
                    "key": test_execution_key or "EXEC-101",
                    "self": f"{self.base_url}/rest/api/2/issue/10400"
                },
                "status": "SUCCESS",
                "imported_tests_count": len(tests_payload)
            }

        endpoint = self._xray_url("import/execution")

        body: Dict[str, Any] = {
            "info": {
                "summary": summary or f"Automated Execution Run ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
                "description": "Reported autonomously via Synapse Hub TMS Bridge",
                "testEnvironments": test_environments or ["Playwright-Headless"],
            },
            "tests": tests_payload,
        }
        if test_execution_key:
            body["testExecutionKey"] = test_execution_key

        return self._execute_request(endpoint, method="POST", data=body)

    def xray_authenticate(self, client_id: str, client_secret: str) -> str:
        """
        Authenticates with Xray Cloud using OAuth2 client credentials and returns a Bearer JWT token.
        POST /api/v2/authenticate
        """
        if self.is_mock:
            return "mock_xray_jwt_token_sample"

        endpoint = self._xray_url("authenticate")
        payload = {"client_id": client_id, "client_secret": client_secret}
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
            token = resp.read().decode("utf-8").strip().strip('"')
            self.api_token = token
            self.auth_type = "bearer"
            return token

    # -------------------------------------------------------------------------
    # 5. EXECUTION SYNC: Push Run Execution Outcomes
    # -------------------------------------------------------------------------
    def sync_execution_results(
        self,
        test_plan_key: str,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Pushes batch test execution status (PASS/FAIL/BLOCKED) to Jira, Xray, or TestRail.
        """
        total = len(results)
        passed = sum(1 for r in results if r.get("status") in ("PASS", "PASSED"))
        failed = sum(1 for r in results if r.get("status") in ("FAIL", "FAILED"))

        sync_report: Dict[str, Any] = {
            "test_plan_key": test_plan_key,
            "provider": self.provider,
            "timestamp": datetime.now().isoformat(),
            "total_synced": total,
            "passed": passed,
            "failed": failed,
            "pass_rate_pct": round((passed / total) * 100.0, 2) if total else 0.0,
            "sync_status": "SUCCESS",
            "destination": self.base_url,
            "entries": results
        }

        if self.is_mock:
            return sync_report

        # Live Xray Execution Import
        if self.provider in ("xray", "jira_xray"):
            xray_tests = []
            for item in results:
                t_key = item.get("test_key") or item.get("tc_id") or "TEST-01"
                st = "PASSED" if item.get("status") in ("PASS", "PASSED") else "FAILED"
                xray_tests.append({
                    "testKey": t_key,
                    "status": st,
                    "comment": item.get("comment", f"Result: {st}"),
                    "duration": item.get("duration_sec", 0.0)
                })
            try:
                import_resp = self.xray_import_execution(
                    test_execution_key=test_plan_key,
                    tests=xray_tests,
                    summary=f"Automated Suite Execution: {test_plan_key}"
                )
                sync_report["xray_response"] = import_resp
            except Exception as e:
                sync_report["sync_status"] = "PARTIAL_ERROR"
                sync_report["error"] = str(e)

        # Live TestRail Result Posting
        elif self.provider == "testrail":
            run_id = 1
            clean_digits = "".join([c for c in test_plan_key if c.isdigit()])
            if clean_digits:
                run_id = int(clean_digits)

            posted_results = []
            for item in results:
                t_key = item.get("test_key") or item.get("tc_id") or "1"
                case_id = int("".join([c for c in t_key if c.isdigit()]) or 1)
                st_id = 1 if item.get("status") in ("PASS", "PASSED") else 5
                elapsed_str = f"{int(item.get('duration_sec', 1))}s"
                try:
                    res = self.testrail_add_result_for_case(
                        run_id=run_id,
                        case_id=case_id,
                        status_id=st_id,
                        comment=item.get("comment", f"Status: {item.get('status')}"),
                        elapsed=elapsed_str
                    )
                    posted_results.append(res)
                except Exception as e:
                    posted_results.append({"case_id": case_id, "error": str(e)})
            sync_report["testrail_results"] = posted_results

        return sync_report


def main():
    parser = argparse.ArgumentParser(description="Enterprise ALM & TMS Sync Bridge")
    parser.add_argument("--provider", default="jira", choices=["jira", "xray", "testrail"], help="TMS Provider")
    parser.add_argument("--base-url", default="", help="Base URL of TMS")
    parser.add_argument("--token", default="", help="API Token or Bearer Token")
    parser.add_argument("--email", default="", help="User email for Basic Auth")
    parser.add_argument("--auth-type", default="auto", choices=["auto", "basic", "bearer", "oauth2"], help="Auth scheme")

    subparsers = parser.add_subparsers(dest="command", help="Sync command")

    # Command: pull
    pull_p = subparsers.add_parser("pull", help="Pull Acceptance Criteria from User Story")
    pull_p.add_argument("issue_key", help="Jira / ALM Issue Key (e.g. PROJ-1042)")
    pull_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Command: report-bug
    bug_p = subparsers.add_parser("report-bug", help="Report defect on test failure")
    bug_p.add_argument("--project", default="QA", help="Project Key (e.g. PROJ)")
    bug_p.add_argument("--tc-id", required=True, help="Test Case ID")
    bug_p.add_argument("--summary", required=True, help="Bug summary title")
    bug_p.add_argument("--error", required=True, help="Failure error message")
    bug_p.add_argument("--stack", default="", help="Error stack trace")
    bug_p.add_argument("--screenshot", default="", help="Path to FAILED screenshot")
    bug_p.add_argument("--json", action="store_true", help="Output JSON format")

    # Command: sync-run
    sync_p = subparsers.add_parser("sync-run", help="Sync batch test execution results")
    sync_p.add_argument("--plan-key", default="QA-PLAN-1", help="Xray Test Plan / Run Key")
    sync_p.add_argument("--results-file", help="Path to JSON test results file")
    sync_p.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()
    bridge = TMSBridge(
        provider=args.provider,
        base_url=args.base_url,
        api_token=args.token,
        user_email=args.email,
        auth_type=args.auth_type,
    )

    if args.command == "pull":
        story = bridge.pull_story_acceptance_criteria(args.issue_key)
        if args.json:
            print(json.dumps(story, indent=2))
        else:
            print("\n======================================================================")
            print(f"      ENTERPRISE ALM STORY PULL: [{story.get('issue_key')}]")
            print("======================================================================")
            print(f"  Summary   : {story.get('summary')}")
            print(f"  Status    : {story.get('status')} | Assignee: {story.get('assignee')}")
            print(f"  Source    : {story.get('source')}\n")
            print("  📋 Acceptance Criteria (Given-When-Then):")
            for ac in story.get("acceptance_criteria", []):
                print(f"     • {ac}")
            print("======================================================================\n")
        return 0

    elif args.command == "report-bug":
        ticket = bridge.report_defect(
            project_key=args.project,
            test_case_id=args.tc_id,
            summary=args.summary,
            error_message=args.error,
            stack_trace=args.stack,
            screenshot_path=args.screenshot
        )
        if args.json:
            print(json.dumps(ticket, indent=2))
        else:
            print(f"\n🐞 [TMS DEFECT CREATED] Ticket: {ticket['ticket_key']}")
            print(f"   Summary : {ticket['summary']}")
            print(f"   Status  : {ticket['status']} ({ticket['mode']})")
            print(f"   Artifact: {ticket['screenshot_attachment'] or 'None'}\n")
        return 0

    elif args.command == "sync-run":
        res_list = []
        if args.results_file and os.path.exists(args.results_file):
            with open(args.results_file, "r", encoding="utf-8") as f:
                res_list = json.load(f)
        else:
            res_list = [
                {"tc_id": "TC-01", "status": "PASS", "duration_sec": 1.2},
                {"tc_id": "TC-02", "status": "PASS", "duration_sec": 0.8},
                {"tc_id": "TC-03", "status": "FAIL", "duration_sec": 2.5}
            ]
        sync = bridge.sync_execution_results(args.plan_key, res_list)
        if args.json:
            print(json.dumps(sync, indent=2))
        else:
            print(f"\n📊 [TMS EXECUTION SYNCED] Plan: {sync['test_plan_key']}")
            print(f"   Total Synced: {sync['total_synced']} | Pass Rate: {sync['pass_rate_pct']}%")
            print(f"   Destination : {sync['destination']}\n")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
