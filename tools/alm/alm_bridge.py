#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/alm/alm_bridge.py — Unified Enterprise ALM & TMS Sync Orchestrator
------------------------------------------------------------------------
Connects Synapse Hub's autonomous test runner and failure triage engine
directly to Enterprise ALM platforms (Jira Cloud/Server, Xray, Zephyr, TestRail v2).

Capabilities:
  1. push-bug: Automatically formats test failure autopsy and creates Jira Bug Ticket.
  2. sync-exec: Ingests JUnit XML test reports and updates Test Runs in Xray or TestRail.
  3. check-connection: Validates ALM endpoints and authentication tokens.
  4. dry-run: Offline simulation for local development and CI gates.

Usage:
    python3 tools/alm/alm_bridge.py status
    python3 tools/alm/alm_bridge.py push-bug --summary "Login failed" --trace "AssertionError" --dry-run
    python3 tools/alm/alm_bridge.py sync-exec --report reports/junit.xml --platform xray --dry-run
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_ROOT = os.path.dirname(_CURRENT_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)

for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


MAX_TRACE_CHARS = 4000
DEFAULT_HTTP_TIMEOUT = 15


def _build_basic_auth(username: str, secret: str) -> str:
    """Encode HTTP Basic Authentication header value from username and token."""
    raw = f"{username}:{secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


class ALMBridge:
    """Enterprise ALM/TMS sync connector supporting Jira, Xray, and TestRail."""

    def __init__(self, platform: str = "jira", dry_run: bool = False):
        self.platform = platform.lower()
        self.dry_run = dry_run
        self.jira_url = os.environ.get("JIRA_BASE_URL", "https://jira.example.com").rstrip("/")
        self.jira_email = os.environ.get("JIRA_EMAIL", "qa-bot@example.com")
        self.jira_token = os.environ.get("JIRA_API_TOKEN", "")
        self.jira_project = os.environ.get("JIRA_PROJECT_KEY", "AUTO")
        self.testrail_url = os.environ.get("TESTRAIL_BASE_URL", "https://testrail.example.com").rstrip("/")
        self.testrail_user = os.environ.get("TESTRAIL_USER", "qa@example.com")
        self.testrail_key = os.environ.get("TESTRAIL_API_KEY", "")

    def _http_post_json(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        timeout: int = DEFAULT_HTTP_TIMEOUT,
    ) -> Dict[str, Any]:
        """Issue a bounded JSON POST request via Python stdlib urllib."""
        body = json.dumps(payload).encode("utf-8")
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **headers,
        }
        req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_text = resp.read().decode("utf-8", errors="replace")
                status_code = getattr(resp, "status", 200)
                parsed: Dict[str, Any] = {}
                if raw_text.strip():
                    try:
                        decoded = json.loads(raw_text)
                        parsed = decoded if isinstance(decoded, dict) else {"data": decoded}
                    except json.JSONDecodeError:
                        parsed = {"raw": raw_text[:500]}
                return {"ok": True, "http_status": status_code, "data": parsed}
        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8", errors="replace")[:300]
            except OSError:
                err_body = ""
            detail = f"HTTP {exc.code}: {exc.reason}"
            if err_body:
                detail = f"{detail} ({err_body})"
            return {"ok": False, "http_status": exc.code, "error_message": detail}
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            return {"ok": False, "http_status": None, "error_message": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        """Inspect active ALM configurations."""
        return {
            "platform_selected": self.platform,
            "dry_run": self.dry_run,
            "jira": {
                "base_url": self.jira_url,
                "email": self.jira_email,
                "project_key": self.jira_project,
                "configured": bool(self.jira_token),
            },
            "testrail": {
                "base_url": self.testrail_url,
                "user": self.testrail_user,
                "configured": bool(self.testrail_key),
            },
        }

    def create_bug(
        self,
        summary: str,
        trace: str,
        severity: str = "High",
        attachments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create or simulate creation of a Bug ticket."""
        bounded_trace = (trace or "").strip()[:MAX_TRACE_CHARS]
        clean_summary = f"[AUT Defect] {summary.strip()}"
        description = (
            f"h2. Autonomous Test Failure Autopsy\n\n"
            f"*Severity:* {severity}\n"
            f"*Detector:* Synapse Hub Failure Sentinel\n\n"
            f"h3. Root Cause Traceback\n"
            f"{{noformat}}\n{bounded_trace}\n{{noformat}}\n\n"
            f"*Attachments:* {', '.join(attachments or ['None'])}"
        )

        ticket_data = {
            "project": self.jira_project,
            "summary": clean_summary,
            "description": description,
            "issue_type": "Bug",
            "severity": severity,
            "attachments": attachments or [],
        }

        if self.dry_run:
            ticket_id = f"{self.jira_project}-SIM-101"
            return {
                "status": "SIMULATED",
                "ticket_id": ticket_id,
                "http_status": None,
                "url": f"{self.jira_url}/browse/{ticket_id}",
                "payload": ticket_data,
                "note": "Executed in dry-run simulation mode. No live API call made.",
            }

        if not self.jira_token:
            return {
                "status": "ERROR",
                "ticket_id": None,
                "http_status": None,
                "url": None,
                "error_message": "Missing JIRA_API_TOKEN for live create_bug request.",
            }

        jira_payload = {
            "fields": {
                "project": {"key": self.jira_project},
                "summary": clean_summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": "Bug"},
                "priority": {"name": severity},
            }
        }
        headers = {"Authorization": _build_basic_auth(self.jira_email, self.jira_token)}
        resp = self._http_post_json(
            f"{self.jira_url}/rest/api/3/issue",
            jira_payload,
            headers,
            timeout=DEFAULT_HTTP_TIMEOUT,
        )
        if not resp["ok"]:
            return {
                "status": "ERROR",
                "ticket_id": None,
                "http_status": resp["http_status"],
                "url": None,
                "error_message": resp["error_message"],
            }

        ticket_id = str(resp["data"].get("key") or resp["data"].get("id") or "")
        if not ticket_id:
            return {
                "status": "ERROR",
                "ticket_id": None,
                "http_status": resp["http_status"],
                "url": None,
                "error_message": "ALM response succeeded without returning a ticket key.",
            }

        return {
            "status": "SUCCESS",
            "ticket_id": ticket_id,
            "http_status": resp["http_status"],
            "url": f"{self.jira_url}/browse/{ticket_id}",
        }

    def parse_junit_report(self, report_path: str) -> Dict[str, Any]:
        """Parse JUnit XML report to extract test execution metrics."""
        if not os.path.isfile(report_path):
            return {
                "error": f"JUnit report file not found: {report_path}",
                "tests": 0,
                "passed": 0,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
                "cases": [],
            }

        try:
            tree = ET.parse(report_path)
            root = tree.getroot()
            cases = []
            failures = 0
            errors = 0
            skipped = 0

            # Handle either <testsuite> root or <testsuites> container
            testcase_nodes = root.findall(".//testcase")
            for tc in testcase_nodes:
                name = tc.get("name", "Unnamed")
                classname = tc.get("classname", "")
                time_val = float(tc.get("time", "0.0") or 0.0)
                status = "PASS"
                failure_msg = ""

                fail_elem = tc.find("failure")
                if fail_elem is not None:
                    status = "FAIL"
                    failures += 1
                    failure_msg = fail_elem.get("message", "") or (fail_elem.text or "").strip()
                elif tc.find("error") is not None:
                    status = "ERROR"
                    errors += 1
                elif tc.find("skipped") is not None:
                    status = "SKIPPED"
                    skipped += 1

                cases.append({
                    "name": name,
                    "classname": classname,
                    "time": time_val,
                    "status": status,
                    "failure": failure_msg,
                })

            total = len(cases)
            passed = total - (failures + errors + skipped)

            return {
                "tests": total,
                "passed": passed,
                "failures": failures,
                "errors": errors,
                "skipped": skipped,
                "cases": cases,
            }
        except Exception as e:
            return {"error": f"Failed to parse JUnit XML: {e}", "cases": []}

    def sync_execution(self, report_path: str) -> Dict[str, Any]:
        """Synchronize JUnit XML execution results to Xray, Jira, or TestRail."""
        metrics = self.parse_junit_report(report_path)
        if "error" in metrics:
            return {
                "status": "ERROR",
                "platform": self.platform,
                "execution_id": None,
                "http_status": None,
                "error_message": metrics["error"],
                "message": metrics["error"],
            }

        base_summary = {
            "platform": self.platform,
            "dry_run": self.dry_run,
            "total_tests": metrics.get("tests", 0),
            "passed": metrics.get("passed", 0),
            "failed": metrics.get("failures", 0) + metrics.get("errors", 0),
            "skipped": metrics.get("skipped", 0),
        }

        if self.dry_run:
            return {
                **base_summary,
                "status": "SIMULATED",
                "http_status": None,
                "execution_id": "EXEC-SIM-999",
                "message": "Test execution results simulated in dry-run mode.",
            }

        if self.platform == "testrail":
            if not self.testrail_key:
                return {
                    **base_summary,
                    "status": "ERROR",
                    "http_status": None,
                    "execution_id": None,
                    "error_message": "Missing TESTRAIL_API_KEY for live testrail sync.",
                    "message": "Missing TESTRAIL_API_KEY for live testrail sync.",
                }
            endpoint = f"{self.testrail_url}/index.php?/api/v2/add_run/1"
            headers = {"Authorization": _build_basic_auth(self.testrail_user, self.testrail_key)}
            payload = {
                "name": f"Synapse Automated Run ({os.path.basename(report_path)})",
                "description": f"Passed: {base_summary['passed']}, Failed: {base_summary['failed']}",
                "include_all": False,
                "cases": metrics.get("cases", [])[:500],
            }
            resp = self._http_post_json(endpoint, payload, headers, timeout=DEFAULT_HTTP_TIMEOUT)
            if not resp["ok"]:
                return {
                    **base_summary,
                    "status": "ERROR",
                    "http_status": resp["http_status"],
                    "execution_id": None,
                    "error_message": resp["error_message"],
                    "message": resp["error_message"],
                }
            exec_id = str(resp["data"].get("id") or "")
        else:
            if not self.jira_token:
                return {
                    **base_summary,
                    "status": "ERROR",
                    "http_status": None,
                    "execution_id": None,
                    "error_message": f"Missing JIRA_API_TOKEN for live {self.platform} sync.",
                    "message": f"Missing JIRA_API_TOKEN for live {self.platform} sync.",
                }
            endpoint = f"{self.jira_url}/rest/raven/1.0/import/execution"
            headers = {"Authorization": _build_basic_auth(self.jira_email, self.jira_token)}
            payload = {
                "info": {
                    "project": self.jira_project,
                    "summary": f"Synapse Execution Sync ({os.path.basename(report_path)})",
                },
                "tests": [
                    {
                        "testKey": c["name"],
                        "status": c["status"],
                        "comment": c.get("failure", ""),
                    }
                    for c in metrics.get("cases", [])[:500]
                ],
            }
            resp = self._http_post_json(endpoint, payload, headers, timeout=DEFAULT_HTTP_TIMEOUT)
            if not resp["ok"]:
                return {
                    **base_summary,
                    "status": "ERROR",
                    "http_status": resp["http_status"],
                    "execution_id": None,
                    "error_message": resp["error_message"],
                    "message": resp["error_message"],
                }
            xray_issue = resp["data"].get("testExecIssue")
            exec_id = str(
                (xray_issue.get("key") if isinstance(xray_issue, dict) else None)
                or resp["data"].get("key")
                or resp["data"].get("id")
                or ""
            )

        if not exec_id:
            return {
                **base_summary,
                "status": "ERROR",
                "http_status": resp["http_status"],
                "execution_id": None,
                "error_message": "ALM sync succeeded without returning an execution ID.",
                "message": "ALM sync succeeded without returning an execution ID.",
            }

        return {
            **base_summary,
            "status": "SUCCESS",
            "http_status": resp["http_status"],
            "execution_id": exec_id,
            "message": "Test execution results synchronized successfully.",
        }


def main():
    parser = argparse.ArgumentParser(description="Unified Enterprise ALM & TMS Sync Orchestrator")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: status
    subparsers.add_parser("status", help="Inspect ALM connector configuration status")

    # Command: push-bug
    bug_parser = subparsers.add_parser("push-bug", help="File a Bug ticket on Jira/Xray")
    bug_parser.add_argument("--summary", required=True, help="Bug summary title")
    bug_parser.add_argument("--trace", required=True, help="Failure traceback / reason")
    bug_parser.add_argument("--severity", default="High", choices=["Highest", "High", "Medium", "Low"], help="Defect severity")
    bug_parser.add_argument("--dry-run", action="store_true", help="Simulate creation without API call")

    # Command: sync-exec
    exec_parser = subparsers.add_parser("sync-exec", help="Sync JUnit XML results to Xray or TestRail")
    exec_parser.add_argument("--report", required=True, help="Path to JUnit XML report")
    exec_parser.add_argument("--platform", default="xray", choices=["xray", "testrail", "jira"], help="Target platform")
    exec_parser.add_argument("--dry-run", action="store_true", help="Simulate execution sync without API call")

    args = parser.parse_args()

    if not args.command or args.command == "status":
        bridge = ALMBridge()
        print(json.dumps(bridge.get_status(), indent=2))
        return

    if args.command == "push-bug":
        bridge = ALMBridge(dry_run=args.dry_run)
        res = bridge.create_bug(summary=args.summary, trace=args.trace, severity=args.severity)
        print(json.dumps(res, indent=2))
        return

    if args.command == "sync-exec":
        bridge = ALMBridge(platform=args.platform, dry_run=args.dry_run)
        res = bridge.sync_execution(args.report)
        print(json.dumps(res, indent=2))
        return


if __name__ == "__main__":
    main()
