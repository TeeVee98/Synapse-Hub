#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/jira_sync.py — Jira / Xray / Zephyr Enterprise 2-Way Synchronization Engine
---------------------------------------------------------------------------------
Zero external dependencies (pure Python standard library: urllib.request).
Bridges Synapse Hub with Atlassian Jira Cloud & Data Center:
1. pull-story: Pulls user story & acceptance criteria into standardized Markdown.
2. push-tests: Creates/updates Test Issues (Xray/Zephyr) linked to User Stories.
3. import-exec: Pushes JUnit XML execution results into Jira/Xray Test Executions.
4. create-bug: Autonomously files Jira Bug tickets with failure traces and screenshots.
5. test-conn: Verifies API connectivity and credentials.
"""

import os
import re
import sys
import time
import json
import base64
import argparse
import mimetypes
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import urllib.request
import urllib.error

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class JiraConfig:
    """Resolves and encapsulates Jira configuration and authentication credentials."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        pat: Optional[str] = None,
        project_key: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        self.config_data = self._load_synapse_config(config_path)
        jira_cfg = self.config_data.get("jira", {})

        # Resolution Precedence: Explicit CLI -> Environment Variables -> .synapse.json
        self.base_url = (
            base_url
            or os.environ.get("JIRA_BASE_URL")
            or jira_cfg.get("baseUrl")
            or "https://jira.example.com"
        ).rstrip("/")

        self.email = (
            email
            or os.environ.get("JIRA_EMAIL")
            or os.environ.get("JIRA_USER")
            or jira_cfg.get("email")
            or ""
        )

        token_raw = (
            api_token
            or os.environ.get("JIRA_API_TOKEN")
            or os.environ.get("JIRA_TOKEN")
            or jira_cfg.get("apiToken")
            or ""
        )
        if token_raw.startswith("env:"):
            env_var = token_raw[4:]
            self.api_token = os.environ.get(env_var, "")
        else:
            self.api_token = token_raw

        pat_raw = pat or os.environ.get("JIRA_PAT") or jira_cfg.get("pat") or ""
        if pat_raw.startswith("env:"):
            self.pat = os.environ.get(pat_raw[4:], "")
        else:
            self.pat = pat_raw

        self.project_key = (
            project_key
            or os.environ.get("JIRA_PROJECT_KEY")
            or jira_cfg.get("projectKey")
            or "QA"
        )
        self.issue_type_test = jira_cfg.get("issueTypeTest", "Test")
        self.issue_type_bug = jira_cfg.get("issueTypeBug", "Bug")

    def _load_synapse_config(self, custom_path: Optional[str] = None) -> Dict[str, Any]:
        cfg_path = custom_path or os.path.join(REPO_ROOT, ".synapse.json")
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_auth_headers(self) -> Dict[str, str]:
        """Generates RFC 7617 Basic Auth or Bearer Authorization headers."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if self.pat:
            headers["Authorization"] = f"Bearer {self.pat}"
        elif self.email and self.api_token:
            creds = f"{self.email}:{self.api_token}".encode("utf-8")
            b64_creds = base64.b64encode(creds).decode("ascii")
            headers["Authorization"] = f"Basic {b64_creds}"
        return headers


class JiraClient:
    """REST API Client for Jira Cloud and Jira Data Center (stdlib only)."""

    def __init__(self, config: JiraConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run

    def request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        custom_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Performs HTTP request to Jira REST API."""
        url = f"{self.config.base_url}{endpoint}"
        headers = self.config.get_auth_headers()
        if custom_headers:
            headers.update(custom_headers)

        if self.dry_run and method in ("POST", "PUT", "DELETE"):
            print(f"[DRY-RUN] {method} -> {url}")
            if data:
                print(f"[DRY-RUN] Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return {"key": f"{self.config.project_key}-DRYRUN", "id": "99999", "dry_run": True}

        body_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                resp_bytes = resp.read()
                if not resp_bytes:
                    return {"status": resp.status}
                return json.loads(resp_bytes.decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Jira API Error [{err.code}] {err.reason}: {err_body}")
        except urllib.error.URLError as err:
            raise RuntimeError(f"Failed to connect to Jira at {self.config.base_url}: {err.reason}")

    def test_connection(self) -> Dict[str, Any]:
        """Tests connectivity and returns authenticated user info."""
        if self.dry_run:
            print("[DRY-RUN] Connection test simulated successfully.")
            return {"status": "OK", "user": "dry_run_user", "mode": "DRY-RUN"}
        res = self.request("/rest/api/2/myself")
        name = res.get("displayName") or res.get("name") or "Authenticated User"
        print(f"✅ Connected to Jira successfully as: {name} ({res.get('emailAddress', 'N/A')})")
        return res

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Fetches issue details by key."""
        return self.request(f"/rest/api/2/issue/{issue_key}?expand=names,renderedFields")

    def create_issue(
        self,
        summary: str,
        description: str,
        issue_type: str,
        priority: str = "Medium",
        labels: Optional[List[str]] = None,
        parent_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a Jira issue."""
        fields: Dict[str, Any] = {
            "project": {"key": self.config.project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
            "labels": labels or ["synapse-hub", "automated"]
        }
        if parent_key and issue_type.lower() in ("sub-task", "subtask"):
            fields["parent"] = {"key": parent_key}

        payload = {"fields": fields}
        return self.request("/rest/api/2/issue", method="POST", data=payload)

    def attach_file(self, issue_key: str, file_path: str) -> Dict[str, Any]:
        """Attaches a file to an issue using multipart/form-data."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        if self.dry_run:
            print(f"[DRY-RUN] Would attach '{file_path}' to issue {issue_key}")
            return {"dry_run": True, "attached": file_path}

        url = f"{self.config.base_url}/rest/api/2/issue/{issue_key}/attachments"
        headers = self.config.get_auth_headers()
        headers["X-Atlassian-Token"] = "no-check"
        del headers["Content-Type"]

        boundary = f"----SynapseHubBoundary{int(time.time() * 1000)}"
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

        filename = os.path.basename(file_path)
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Failed to attach file to {issue_key}: [{err.code}] {err_body}")


def parse_markdown_testcases(md_content: str) -> List[Dict[str, Any]]:
    """Parses markdown test case tables or bulleted test scenarios into structured dicts."""
    testcases = []
    lines = md_content.splitlines()

    # Look for table header with Test ID / Summary / Steps / Expected
    table_mode = False
    headers = []
    for line in lines:
        line_clean = line.strip()
        if "|" in line_clean:
            cols = [c.strip() for c in line_clean.split("|")[1:-1]]
            if any("test" in c.lower() or "summary" in c.lower() or "tiêu chí" in c.lower() for c in cols):
                table_mode = True
                headers = [c.lower() for c in cols]
                continue
            if table_mode and re.match(r"^[\s\-|:]+$", line_clean):
                continue
            if table_mode and len(cols) >= 2:
                tc = {
                    "id": cols[0],
                    "summary": cols[1],
                    "description": cols[2] if len(cols) > 2 else cols[1],
                    "expected": cols[3] if len(cols) > 3 else "Pass"
                }
                testcases.append(tc)
        elif line_clean.startswith("### ") or line_clean.startswith("## "):
            table_mode = False
            title = line_clean.lstrip("#").strip()
            if any(kw in title.lower() for kw in ("test", "tc_", "kịch bản", "scenario")):
                testcases.append({
                    "id": f"TC_{len(testcases) + 1}",
                    "summary": title,
                    "description": title,
                    "expected": "Pass"
                })

    return testcases


def parse_junit_xml(xml_path: str) -> Dict[str, Any]:
    """Parses a JUnit XML report file into execution metrics."""
    if not os.path.isfile(xml_path):
        raise FileNotFoundError(f"JUnit XML report not found: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_time = 0.0
    cases = []

    # Handle both <testsuites> and single <testsuite> root
    suites = root.findall(".//testsuite") if root.tag != "testsuite" else [root]
    for suite in suites:
        total_tests += int(suite.attrib.get("tests", 0))
        total_failures += int(suite.attrib.get("failures", 0))
        total_errors += int(suite.attrib.get("errors", 0))
        total_time += float(suite.attrib.get("time", 0.0))

        for tc in suite.findall("testcase"):
            tc_name = tc.attrib.get("name", "Unnamed")
            tc_class = tc.attrib.get("classname", "")
            tc_time = float(tc.attrib.get("time", 0.0))

            failure_el = tc.find("failure")
            if failure_el is None:
                failure_el = tc.find("error")

            status = "FAILED" if failure_el is not None else "PASSED"
            message = failure_el.attrib.get("message", "") if failure_el is not None else ""
            trace = failure_el.text if failure_el is not None else ""

            cases.append({
                "name": tc_name,
                "classname": tc_class,
                "time": tc_time,
                "status": status,
                "message": message,
                "trace": trace
            })

    return {
        "tests": total_tests,
        "failures": total_failures,
        "errors": total_errors,
        "time": round(total_time, 2),
        "cases": cases
    }


def pull_story(client: JiraClient, story_key: str, out_dir: str = "requirements/jira"):
    """Pulls a Jira User Story and generates clean requirement Markdown and attachments."""
    print(f"📥 Pulling Jira requirement for '{story_key}'...")
    issue = client.get_issue(story_key)
    fields = issue.get("fields", {})

    summary = fields.get("summary", "No Summary")
    description = fields.get("description", "No Description")
    issue_type = fields.get("issuetype", {}).get("name", "Story")
    status = fields.get("status", {}).get("name", "Open")
    priority = fields.get("priority", {}).get("name", "Medium")

    if os.path.isabs(out_dir):
        dest_dir = os.path.join(out_dir, story_key)
    else:
        dest_dir = os.path.join(REPO_ROOT, out_dir, story_key)
    os.makedirs(dest_dir, exist_ok=True)
    md_path = os.path.join(dest_dir, f"{story_key}_requirement.md")

    md_content = f"""# {story_key}: {summary}

| Thuộc tính | Giá trị |
|---|---|
| **Issue Key** | {story_key} |
| **Loại** | {issue_type} |
| **Trạng thái** | {status} |
| **Độ ưu tiên** | {priority} |
| **Ngày đồng bộ** | {time.strftime('%Y-%m-%d %H:%M:%S')} |

## Mô tả & Tiêu chí chấp nhận (Description & AC)

{description or 'Không có mô tả chi tiết.'}

---
*Bản đồng bộ tự động từ Jira REST API bởi Synapse Hub v3.2.2.*
"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    try:
        display_path = os.path.relpath(md_path, REPO_ROOT)
    except ValueError:
        display_path = md_path
    print(f"✅ Saved requirement markdown: {display_path}")
    return md_path


def push_tests_from_file(
    client: JiraClient,
    file_path: str,
    story_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Reads test cases from file and creates corresponding Test issues on Jira."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Test case file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    testcases = parse_markdown_testcases(content)
    if not testcases:
        print(f"⚠️ No structured test cases found in {file_path}")
        return []

    print(f"📤 Pushing {len(testcases)} test case(s) from '{file_path}' to Jira project '{client.config.project_key}'...")
    created_issues = []
    for tc in testcases:
        summary = f"[{tc['id']}] {tc['summary']}"
        desc = (
            f"h3. Synapse Hub Automated Test Specification\n\n"
            f"*ID:* {tc['id']}\n"
            f"*Summary:* {tc['summary']}\n"
            f"*Description:* {tc.get('description', '')}\n"
            f"*Expected Result:* {tc.get('expected', 'Pass')}\n\n"
        )
        if story_key:
            desc += f"*Linked Story:* [{story_key}|{client.config.base_url}/browse/{story_key}]\n"

        res = client.create_issue(
            summary=summary,
            description=desc,
            issue_type=client.config.issue_type_test,
            labels=["synapse-hub", "automated", tc['id']]
        )
        created_issues.append(res)
        print(f"  [PASS] Created Test Issue: {res.get('key', 'UNKNOWN')}")

    return created_issues


def create_bug_report(
    client: JiraClient,
    summary: str,
    trace: str,
    screenshot_path: Optional[str] = None,
    suite_name: Optional[str] = None
) -> Dict[str, Any]:
    """Creates an automated Bug issue on Jira with error details and screenshot."""
    full_summary = f"[Auto-Bug][{suite_name or 'E2E'}] {summary}"
    desc = f"""h3. 🛑 Automated Test Failure Detected by Synapse Hub

*Suite:* {suite_name or 'Automated QA Suite'}
*Environment:* OS: {sys.platform} | Python: {sys.version.split()[0]} | Hub Core: v3.2.2
*Timestamp:* {time.strftime('%Y-%m-%d %H:%M:%S')}

h4. Stack Trace & Root Cause
{{noformat}}
{trace}
{{noformat}}

*Reported autonomously by Synapse Hub DoD Gatekeeper.*
"""
    print(f"🐞 Filing Jira Bug: '{full_summary}'...")
    res = client.create_issue(
        summary=full_summary,
        description=desc,
        issue_type=client.config.issue_type_bug,
        priority="High",
        labels=["synapse-hub", "auto-bug", "ci-failure"]
    )
    bug_key = res.get("key", "UNKNOWN")
    print(f"✅ Bug created successfully: {bug_key}")

    if screenshot_path and os.path.isfile(screenshot_path):
        print(f"📎 Attaching screenshot '{screenshot_path}' to {bug_key}...")
        client.attach_file(bug_key, screenshot_path)
        print("  [PASS] Screenshot attached.")

    return res


def import_junit_execution(client: JiraClient, xml_path: str) -> Dict[str, Any]:
    """Imports JUnit execution metrics to Jira / Xray Test Execution."""
    metrics = parse_junit_xml(xml_path)
    summary = f"[Test-Execution] Automated Test Run ({metrics['tests']} Tests, {metrics['failures']} Failures)"

    case_lines = []
    for c in metrics["cases"][:20]:  # Cap first 20 in summary
        status_icon = "(/)" if c["status"] == "PASSED" else "(x)"
        case_lines.append(f"* {status_icon} *{c['name']}* ({c['time']}s)")

    desc = f"""h3. 🚀 Synapse Hub Automated Test Execution Report

*Total Tests:* {metrics['tests']}
*Failures:* {metrics['failures']}
*Errors:* {metrics['errors']}
*Total Execution Time:* {metrics['time']}s

h4. Test Case Breakdown
{chr(10).join(case_lines)}

*Exported from JUnit XML: {os.path.basename(xml_path)}*
"""
    print(f"📊 Creating Test Execution issue on Jira ({metrics['tests']} tests)...")
    res = client.create_issue(
        summary=summary,
        description=desc,
        issue_type="Test Execution",
        labels=["synapse-hub", "test-execution", "junit-import"]
    )
    print(f"✅ Test Execution issue created: {res.get('key', 'UNKNOWN')}")
    return res


def main():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--url", default=None, help="Jira Base URL (or via JIRA_BASE_URL)")
    parent_parser.add_argument("--email", default=None, help="Jira Email address (or via JIRA_EMAIL)")
    parent_parser.add_argument("--token", default=None, help="Jira API Token (or via JIRA_API_TOKEN)")
    parent_parser.add_argument("--pat", default=None, help="Jira Personal Access Token (or via JIRA_PAT)")
    parent_parser.add_argument("--project", "-p", default=None, help="Jira Project Key (or via JIRA_PROJECT_KEY)")
    parent_parser.add_argument("--dry-run", action="store_true", help="Simulate API calls without writing to Jira")

    parser = argparse.ArgumentParser(
        description="Synapse Hub — Jira / Xray / Zephyr 2-Way Sync Engine",
        parents=[parent_parser]
    )
    subparsers = parser.add_subparsers(dest="action", help="Action to execute")

    # test-conn
    subparsers.add_parser("test-conn", parents=[parent_parser], help="Verify credentials and connectivity to Jira REST API")

    # pull-story
    p_pull = subparsers.add_parser("pull-story", parents=[parent_parser], help="Pull User Story requirement from Jira into Markdown")
    p_pull.add_argument("story_key", help="Jira Issue Key (e.g. KAN-1, PROJ-102)")
    p_pull.add_argument("--out-dir", default="requirements/jira", help="Output directory for requirement markdown")

    # push-tests
    p_push = subparsers.add_parser("push-tests", parents=[parent_parser], help="Push test cases from markdown file to Jira Test issues")
    p_push.add_argument("--file", "-f", required=True, help="Path to markdown or text file with test cases")
    p_push.add_argument("--story", "-s", default=None, help="Parent User Story Key to link test cases to")

    # create-bug
    p_bug = subparsers.add_parser("create-bug", parents=[parent_parser], help="File an automated Bug ticket on Jira from test failure")
    p_bug.add_argument("--summary", required=True, help="Short summary of the bug")
    p_bug.add_argument("--trace", default="No stack trace provided.", help="Failure stack trace or error log")
    p_bug.add_argument("--screenshot", default=None, help="Path to error screenshot (e.g. Screenshots/FAILED_*.png)")
    p_bug.add_argument("--suite", default="E2E", help="Test suite name")

    # import-exec
    p_import = subparsers.add_parser("import-exec", parents=[parent_parser], help="Import JUnit XML report as a Jira Test Execution")
    p_import.add_argument("--junit", required=True, help="Path to JUnit XML report file")

    args = parser.parse_args()

    cfg = JiraConfig(
        base_url=args.url,
        email=args.email,
        api_token=args.token,
        pat=args.pat,
        project_key=args.project
    )
    client = JiraClient(cfg, dry_run=args.dry_run)

    if args.action == "test-conn":
        client.test_connection()
    elif args.action == "pull-story":
        pull_story(client, args.story_key, args.out_dir)
    elif args.action == "push-tests":
        push_tests_from_file(client, args.file, args.story)
    elif args.action == "create-bug":
        create_bug_report(client, args.summary, args.trace, args.screenshot, args.suite)
    elif args.action == "import-exec":
        import_junit_execution(client, args.junit)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
