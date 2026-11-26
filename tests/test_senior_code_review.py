#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "tools")
sys.path.insert(0, TOOLS_DIR)

import senior_code_review
from senior_code_review import parse_diff, analyze_diff, format_report, run_review
from tools.lint.output_diff_sentinel import OutputDiffSentinel
from tools.ai.cove_verifier import ChainOfVerificationEngine


class TestSeniorCodeReview(unittest.TestCase):

    def test_parse_diff_added_lines(self):
        sample_diff = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -10,2 +10,4 @@
 def handle():
+    token = "secret_12345678"
+    Thread.sleep(5000)
     return True
"""
        files = parse_diff(sample_diff)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["path"], "src/app.py")
        self.assertEqual(len(files[0]["added_lines"]), 2)

    def test_analyze_diff_catches_secret_and_sleep(self):
        sample_diff = """diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,1 +1,4 @@
+api_key = "my_secret_token_abcdef123"
+time.sleep(5000)
+try:
+    pass
+except Exception: pass
"""
        files = parse_diff(sample_diff)
        findings, cuttable = analyze_diff(files, ".")
        severities = [f.severity for f in findings]
        self.assertIn("Must fix", severities)
        self.assertIn("Should fix", severities)

    def test_analyze_diff_catches_raw_settimeout_in_tests(self):
        sample_diff = """diff --git a/tests/test_flow.spec.ts b/tests/test_flow.spec.ts
--- a/tests/test_flow.spec.ts
+++ b/tests/test_flow.spec.ts
@@ -1,1 +1,3 @@
+test("flaky test", async () => {
+  setTimeout(() => {}, 2000);
+});
"""
        files = parse_diff(sample_diff)
        findings, _ = analyze_diff(files, ".")
        titles = [f.title for f in findings]
        self.assertTrue(any("setTimeout" in t for t in titles))

    def test_format_report_clean(self):
        report = format_report([], [], 0)
        self.assertIn("No changes found", report)

    def test_output_md_export(self):
        import tempfile
        from pathlib import Path
        from senior_code_review import run_review

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_report.md"
            exit_code = run_review(".", target="uncommitted", as_json=False, output_md=str(out_file))
            self.assertIn(exit_code, [0, 1])
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("Senior Developer Quality & Lean Code Review", content)

    def test_git_diff_failure_returns_error_exit_code(self):
        # Non-existent branch/ref should fail git diff and return 2
        exit_code = run_review(".", target="non_existent_branch_deadbeef_xyz", as_json=True)
        self.assertEqual(exit_code, 2)

    def test_run_review_json_surfaces_diff_bloat_without_breaking_json_or_exit_code(self):
        sample_diff = """diff --git a/src/clean.py b/src/clean.py
--- a/src/clean.py
+++ b/src/clean.py
@@ -1,1 +1,2 @@
+def ok():
+    return 1
"""
        violations = [{
            "file": "src/clean.py",
            "total_lines": 120,
            "added": 100,
            "deleted": 100,
            "issue": "MONOLITHIC_FULL_REWRITE: Entire file deleted and rewritten instead of targeted Search/Replace!"
        }]
        buf = io.StringIO()
        with patch.object(senior_code_review, "get_git_diff", return_value=sample_diff), \
             patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(False, violations)) as mock_audit, \
             redirect_stdout(buf):
            exit_code = run_review(".", target="uncommitted", as_json=True)

        mock_audit.assert_called_once()
        self.assertEqual(exit_code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertFalse(parsed["diff_bloat_passed"])
        self.assertEqual(parsed["diff_bloat_warnings"], 1)
        self.assertEqual(len(parsed["diff_bloat_violations"]), 1)
        self.assertEqual(parsed["diff_bloat_violations"][0]["file"], "src/clean.py")

    def test_run_review_must_fix_exit_code_preserved_with_clean_diff_audit(self):
        sample_diff = """diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,1 +1,2 @@
+api_key = "my_secret_token_abcdef123"
"""
        buf = io.StringIO()
        with patch.object(senior_code_review, "get_git_diff", return_value=sample_diff), \
             patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(True, [])), \
             redirect_stdout(buf):
            exit_code = run_review(".", target="uncommitted", as_json=True)

        self.assertEqual(exit_code, 1)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["diff_bloat_passed"])
        self.assertEqual(parsed["diff_bloat_warnings"], 0)

    def test_run_review_verify_report_markdown_runs_cove_and_surfaces_confidence(self):
        sample_diff = """diff --git a/src/helper.py b/src/helper.py
--- a/src/helper.py
+++ b/src/helper.py
@@ -1,1 +1,2 @@
+def add(a, b):
+    return a + b
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "review.md"
            buf = io.StringIO()
            with patch.object(senior_code_review, "get_git_diff", return_value=sample_diff), \
                 patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(True, [])), \
                 patch.object(ChainOfVerificationEngine, "verify", return_value={
                     "status": "PASS",
                     "factual_confidence_pct": 100.0,
                     "total_questions_verified": 1,
                     "passed_verifications": 1,
                     "discrepancies_count": 0,
                 }) as mock_verify, \
                 redirect_stdout(buf):
                exit_code = run_review(
                    ".",
                    target="uncommitted",
                    as_json=False,
                    output_md=str(out_file),
                    verify_report=True,
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.exists())
            mock_verify.assert_called_once_with(str(out_file))
            stdout_text = buf.getvalue()
            self.assertIn("100.0%", stdout_text)
            self.assertIn("CoVe", stdout_text)

    def test_run_review_json_with_output_md_and_verify_report_stays_valid_json(self):
        sample_diff = """diff --git a/src/helper.py b/src/helper.py
--- a/src/helper.py
+++ b/src/helper.py
@@ -1,1 +1,2 @@
+def sub(a, b):
+    return a - b
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "review_json.md"
            buf = io.StringIO()
            with patch.object(senior_code_review, "get_git_diff", return_value=sample_diff), \
                 patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(True, [])), \
                 redirect_stdout(buf):
                exit_code = run_review(
                    ".",
                    target="uncommitted",
                    as_json=True,
                    output_md=str(out_file),
                    verify_report=True,
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.exists())
            parsed = json.loads(buf.getvalue())
            self.assertIn("cove_confidence_pct", parsed)
            self.assertEqual(parsed["cove_confidence_pct"], 100.0)
            self.assertEqual(parsed["cove_verification"]["status"], "PASS")

    def test_run_review_boundary_verify_report_without_output_md_does_not_crash(self):
        buf = io.StringIO()
        with patch.object(senior_code_review, "get_git_diff", return_value=""), \
             patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(True, [])), \
             redirect_stdout(buf):
            exit_code = run_review(
                ".",
                target="uncommitted",
                as_json=True,
                output_md=None,
                verify_report=True,
            )

        self.assertEqual(exit_code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIsNone(parsed["cove_confidence_pct"])
        self.assertEqual(parsed["cove_verification"]["status"], "SKIPPED")

    def test_run_review_boundary_empty_markdown_report_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "empty_review.md"
            buf = io.StringIO()
            with patch.object(senior_code_review, "get_git_diff", return_value=""), \
                 patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(True, [])), \
                 patch.object(senior_code_review, "format_report", return_value=""), \
                 redirect_stdout(buf):
                exit_code = run_review(
                    ".",
                    target="uncommitted",
                    as_json=True,
                    output_md=str(out_file),
                    verify_report=True,
                )

            self.assertEqual(exit_code, 0)
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed["cove_verification"]["status"], "EMPTY_REPORT")
            self.assertEqual(parsed["cove_confidence_pct"], 0.0)

    def test_run_review_negative_sentinel_and_cove_errors_do_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "err_review.md"
            buf = io.StringIO()
            err_buf = io.StringIO()
            with patch.object(senior_code_review, "get_git_diff", return_value=""), \
                 patch.object(OutputDiffSentinel, "audit_git_diff", side_effect=RuntimeError("sentinel fail")), \
                 patch.object(ChainOfVerificationEngine, "verify", side_effect=RuntimeError("cove fail")), \
                 redirect_stdout(buf), \
                 redirect_stderr(err_buf):
                exit_code = run_review(
                    ".",
                    target="uncommitted",
                    as_json=True,
                    output_md=str(out_file),
                    verify_report=True,
                )

            self.assertEqual(exit_code, 0)
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed["diff_bloat_warnings"], 0)
            self.assertFalse(parsed["diff_bloat_passed"])
            self.assertIn("sentinel fail", parsed["diff_audit_error"])
            self.assertEqual(parsed["cove_verification"]["status"], "ERROR")
            self.assertIn("cove fail", parsed["cove_verification"]["error"])
            self.assertIsNone(parsed["cove_confidence_pct"])
            stderr_text = err_buf.getvalue()
            self.assertIn("OutputDiffSentinel audit failed", stderr_text)
            self.assertIn("CoVe report verification failed", stderr_text)

    def test_run_review_sentinel_git_error_entry_sets_audit_error_not_bloat_warning(self):
        buf = io.StringIO()
        with patch.object(senior_code_review, "get_git_diff", return_value=""), \
             patch.object(
                 OutputDiffSentinel,
                 "audit_git_diff",
                 return_value=(False, [{"file": "git", "issue": "Git diff execution failed: not a repo"}]),
             ), \
             redirect_stdout(buf):
            exit_code = run_review(".", target="uncommitted", as_json=True)

        self.assertEqual(exit_code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertFalse(parsed["diff_bloat_passed"])
        self.assertEqual(parsed["diff_bloat_warnings"], 0)
        self.assertEqual(parsed["diff_bloat_violations"], [])
        self.assertIn("Git diff execution failed", parsed["diff_audit_error"])

    def test_run_review_sentinel_false_with_empty_violations_marks_bloat_not_passed(self):
        buf = io.StringIO()
        with patch.object(senior_code_review, "get_git_diff", return_value=""), \
             patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(False, [])), \
             redirect_stdout(buf):
            exit_code = run_review(".", target="uncommitted", as_json=True)

        self.assertEqual(exit_code, 0)
        parsed = json.loads(buf.getvalue())
        self.assertFalse(parsed["diff_bloat_passed"])
        self.assertEqual(parsed["diff_bloat_warnings"], 0)

    def test_format_report_with_findings_renders_numbered_sections(self):
        sample_diff = """diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,1 +1,2 @@
+api_key = "my_secret_token_abcdef123"
"""
        files = parse_diff(sample_diff)
        findings, cuttable = analyze_diff(files, ".")
        report = format_report(findings, files, cuttable)
        self.assertIn("### 🚨 Must Fix (Blockers)\n\n#### 1. **", report)

    def test_analyze_diff_ignores_sleep_in_markdown_docs(self):
        sample_diff = (
            "diff --git a/docs/guide.md b/docs/guide.md\n"
            "--- a/docs/guide.md\n"
            "+++ b/docs/guide.md\n"
            "@@ -1,1 +1,2 @@\n"
            "+Avoid calling time." + "sleep(5000) in tests.\n"
        )
        files = parse_diff(sample_diff)
        findings, _ = analyze_diff(files, ".")
        self.assertEqual(findings, [])

    def test_cli_verify_cove_flag_passes_verify_report_true(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "cli_review.md"
            with patch.object(senior_code_review, "run_review", return_value=0) as mock_run, \
                 patch.object(sys, "argv", ["senior_code_review.py", ".", "--json", "-o", str(out_file), "--verify-cove"]):
                with self.assertRaises(SystemExit) as ctx:
                    senior_code_review.main()
                self.assertEqual(ctx.exception.code, 0)
            mock_run.assert_called_once_with(".", "uncommitted", True, output_md=str(out_file), verify_report=True)

    def test_markdown_report_surfaces_diff_bloat_warnings(self):
        violations = [{
            "file": "src/monolith.py",
            "total_lines": 200,
            "added": 180,
            "deleted": 180,
            "issue": "MONOLITHIC_FULL_REWRITE: Entire file deleted and rewritten instead of targeted Search/Replace!"
        }]
        buf = io.StringIO()
        with patch.object(senior_code_review, "get_git_diff", return_value=""), \
             patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(False, violations)), \
             redirect_stdout(buf):
            exit_code = run_review(".", target="uncommitted", as_json=False)

        self.assertEqual(exit_code, 0)
        out = buf.getvalue()
        self.assertIn("Diff Bloat", out)
        self.assertIn("src/monolith.py", out)

    def test_m2_positive_plan_and_signed_receipt_integration(self):
        plan_md = """# Spec-Driven Implementation Plan: Widget

## 1. Affected Files & Blast Radius

| Action | File Path & Structural Anchor | Scope & Responsibility |
|---|---|---|
| `[CREATE]` | `src/widget.py` (New) | Widget module |
| `[CREATE]` | `tests/test_widget.py` (New) | Widget tests |

## 2. Data Flow & Interface Signatures

```python
def build_widget(name: str) -> str:
    ...
```

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Widget
- **Node ID:** `M1` | **depends_on:** `[]`
- **Write Set:** `['src/widget.py', 'tests/test_widget.py']`

## 4. Verification Matrix

| ID | Test Scenario | Input / Precondition | Expected Output / Assertion | Verification Command |
|---|---|---|---|---|
| **TC-01** | Positive | Name | Formatted | `python3 -m pytest tests/test_widget.py -k "test_build_widget"` |
"""
        sample_diff = """diff --git a/src/widget.py b/src/widget.py
--- /dev/null
+++ b/src/widget.py
@@ -0,0 +1,2 @@
+def build_widget(name: str) -> str:
+    return name.strip()
diff --git a/tests/test_widget.py b/tests/test_widget.py
--- /dev/null
+++ b/tests/test_widget.py
@@ -0,0 +1,4 @@
+from src.widget import build_widget
+
+def test_build_widget():
+    assert build_widget(" ok ") == "ok"
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "plan.md").write_text(plan_md, encoding="utf-8")
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "widget.py").write_text(
                "def build_widget(name: str) -> str:\n    return name.strip()\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_widget.py").write_text(
                'from src.widget import build_widget\n\ndef test_build_widget():\n    assert build_widget(" ok ") == "ok"\n',
                encoding="utf-8",
            )
            receipt_file = root / "reports" / "code_review_receipt.json"
            out_md = root / "review.md"
            buf = io.StringIO()
            with patch.object(senior_code_review, "get_git_diff", return_value=sample_diff), \
                 patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(True, [])), \
                 redirect_stdout(buf):
                exit_code = run_review(
                    str(root),
                    target="uncommitted",
                    as_json=True,
                    output_md=str(out_md),
                    plan_path="plan.md",
                    receipt_out=str(receipt_file),
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(receipt_file.is_file())
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed["verdict"], "APPROVED")
            self.assertTrue(parsed["passed"])
            self.assertEqual(parsed["plan_reconciliation"]["alignment_score_pct"], 100.0)
            self.assertEqual(len(parsed["receipt_hmac"]), 64)
            md_content = out_md.read_text(encoding="utf-8")
            self.assertIn("Plan Reconciliation", md_content)

    def test_m2_negative_ast_multiline_swallowed_mutable_default_shell_clock_and_nesting(self):
        sample_diff = """diff --git a/src/risky.py b/src/risky.py
--- a/src/risky.py
+++ b/src/risky.py
@@ -1,1 +1,24 @@
+import subprocess
+import time
+
+def bad_handler(items=[]):
+    start = time.time()
+    try:
+        subprocess.run("echo hi", shell=True)
+    except Exception:
+        pass
+    if time.time() - start > 5:
+        for x in items:
+            if x > 0:
+                while x > 1:
+                    if x == 2:
+                        if x < 10:
+                            break
+                    x -= 1
+    return items
diff --git a/tests/test_risky.py b/tests/test_risky.py
--- a/tests/test_risky.py
+++ b/tests/test_risky.py
@@ -1,1 +1,3 @@
+def test_fake():
+    assert False
"""
        files = parse_diff(sample_diff)
        findings, _ = analyze_diff(files, ".")
        titles = [f.title.lower() for f in findings]
        severities = {f.title.lower(): f.severity for f in findings}
        self.assertTrue(any("swallowed exception" in t for t in titles), titles)
        self.assertTrue(any("mutable default" in t for t in titles), titles)
        self.assertTrue(any("shell=true" in t or "eval" in t for t in titles), titles)
        self.assertTrue(any("monotonic" in t or "time.time" in t for t in titles), titles)
        self.assertTrue(any("tautological" in t for t in titles), titles)
        self.assertTrue(any("nesting" in t for t in titles), titles)
        for title, sev in severities.items():
            if "mutable default" in title or "shell=true" in title or "tautological" in title:
                self.assertEqual(sev, "Must fix")

        # Direct boundary checks on AST helpers to ensure zero blind spots
        import ast as _ast
        self.assertFalse(senior_code_review._is_swallowed_handler_body([]))
        self.assertTrue(senior_code_review._is_swallowed_handler_body(_ast.parse("...").body))
        self.assertFalse(senior_code_review._is_swallowed_handler_body(_ast.parse("'ok'").body))
        self.assertTrue(senior_code_review._is_swallowed_handler_body(_ast.parse("_ = e").body))
        self.assertFalse(senior_code_review._is_swallowed_handler_body(_ast.parse("a = b = e").body))
        self.assertFalse(senior_code_review._is_swallowed_handler_body(_ast.parse("err = e").body))
        self.assertFalse(senior_code_review._is_swallowed_handler_body(_ast.parse("raise").body))

        self.assertFalse(senior_code_review._is_mutable_default(None))
        self.assertTrue(senior_code_review._is_mutable_default(_ast.parse("set()").body[0].value))
        self.assertFalse(senior_code_review._is_mutable_default(_ast.parse("tuple()").body[0].value))
        self.assertFalse(senior_code_review._is_mutable_default(_ast.parse("42").body[0].value))

    def test_m2_boundary_strict_escalates_should_fix(self):
        sample_diff = """diff --git a/src/slow.py b/src/slow.py
--- a/src/slow.py
+++ b/src/slow.py
@@ -1,1 +1,3 @@
+import time
+def wait_briefly():
+    time.sleep(1)
"""
        buf_norm = io.StringIO()
        buf_strict = io.StringIO()
        with patch.object(senior_code_review, "get_git_diff", return_value=sample_diff), \
             patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(True, [])):
            with redirect_stdout(buf_norm):
                rc_norm = run_review(".", target="uncommitted", as_json=True, strict=False)
            with redirect_stdout(buf_strict):
                rc_strict = run_review(".", target="uncommitted", as_json=True, strict=True)

        self.assertEqual(rc_norm, 0)
        self.assertEqual(json.loads(buf_norm.getvalue())["verdict"], "APPROVED_WITH_NOTES")
        self.assertEqual(rc_strict, 1)
        self.assertEqual(json.loads(buf_strict.getvalue())["verdict"], "CHANGES_REQUESTED")

    def test_m2_cli_plan_and_strict_flags_forwarded(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            receipt_file = Path(tmp_dir) / "rcpt.json"
            with patch.object(senior_code_review, "run_review", return_value=0) as mock_run, \
                 patch.object(
                     sys,
                     "argv",
                     [
                         "senior_code_review.py",
                         ".",
                         "--plan",
                         "review_super_plan.md",
                         "--milestone",
                         "M2",
                         "--strict",
                         "--strict-solo",
                         "--receipt-out",
                         str(receipt_file),
                         "--json",
                     ],
                 ):
                with self.assertRaises(SystemExit) as ctx:
                    senior_code_review.main()
                self.assertEqual(ctx.exception.code, 0)
            mock_run.assert_called_once_with(
                ".",
                "uncommitted",
                True,
                output_md=None,
                verify_report=False,
                plan_path="review_super_plan.md",
                milestone_id="M2",
                strict=True,
                strict_solo=True,
                receipt_out=str(receipt_file),
            )

    def test_v21_untracked_create_files_and_true_tautology(self):
        import subprocess
        from senior_code_review import evaluate_review

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=root, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=root, capture_output=True, check=True)
            (root / "README.md").write_text("# init\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True, check=True)

            # Untracked [CREATE] files (not staged with git add)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "leak.py").write_text('api_key = "hardcoded_secret_123456"\n', encoding="utf-8")
            (root / "tests" / "test_fake_pass.py").write_text(
                "def test_fake():\n    assert True\n", encoding="utf-8"
            )
            (root / "tests" / "test_except_ok.py").write_text(
                "def test_ok():\n    try:\n        int('x')\n        assert False\n    except ValueError:\n        assert True\n",
                encoding="utf-8",
            )

            exit_code, payload, _, _ = evaluate_review(str(root), target="uncommitted")
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["verdict"], "CHANGES_REQUESTED")
            self.assertEqual(payload["files_count"], 3)
            titles = [f["title"].lower() for f in payload["findings"]]
            self.assertTrue(any("secret" in t for t in titles), titles)
            taut_findings = [f for f in payload["findings"] if "tautological" in f["title"].lower()]
            self.assertTrue(any(f["file"].endswith("test_fake_pass.py") for f in taut_findings), taut_findings)
            # except ValueError: assert True must not be flagged as a true tautology
            self.assertFalse(
                any(f["file"].endswith("test_except_ok.py") and f["line"] == 6 for f in taut_findings),
                taut_findings,
            )

    def test_v21_edited_body_nesting_and_no_newline_line_accuracy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "src").mkdir()
            target_py = root / "src" / "nested.py"
            target_py.write_text(
                "def existing_fn(items):\n"
                "    for x in items:\n"
                "        if x > 0:\n"
                "            while x > 1:\n"
                "                if x == 2:\n"
                "                    if x < 10:\n"
                "                        return x\n"
                "    return 0\n",
                encoding="utf-8",
            )
            # Note: def line (line 1) is context, only inner body line 6 was added!
            sample_diff = (
                "diff --git a/src/nested.py b/src/nested.py\n"
                "--- a/src/nested.py\n"
                "+++ b/src/nested.py\n"
                "@@ -1,6 +1,8 @@\n"
                " def existing_fn(items):\n"
                "     for x in items:\n"
                "         if x > 0:\n"
                "             while x > 1:\n"
                "                 if x == 2:\n"
                "+                    if x < 10:\n"
                "+                        return x\n"
                "diff --git a/src/nl.py b/src/nl.py\n"
                "--- a/src/nl.py\n"
                "+++ b/src/nl.py\n"
                "@@ -1,2 +1,3 @@\n"
                " import time\n"
                "-x = 1\n"
                "\\ No newline at end of file\n"
                "+x = 1\n"
                "+time.sleep(2)\n"
            )
            files = parse_diff(sample_diff)
            findings, _ = analyze_diff(files, str(root))
            titles = [f.title.lower() for f in findings]
            self.assertTrue(any("nesting" in t for t in titles), titles)
            sleep_findings = [f for f in findings if "static sleep" in f.title.lower()]
            self.assertEqual(len(sleep_findings), 1)
            self.assertEqual(sleep_findings[0].line_no, 3, "Line offset shifted by '\\ No newline at end of file'")

    def test_v21_unused_import_simplify_and_md_dead_code_guard(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "src").mkdir()
            (root / "docs").mkdir()
            (root / "src" / "clean.py").write_text(
                "import json\nimport os\n\ndef get_cwd() -> str:\n    return os.getcwd()\n",
                encoding="utf-8",
            )
            sample_diff = (
                "diff --git a/src/clean.py b/src/clean.py\n"
                "--- a/src/clean.py\n"
                "+++ b/src/clean.py\n"
                "@@ -1,5 +1,6 @@\n"
                "+import json\n"
                " import os\n"
                "+# return False\n"
                " def get_cwd() -> str:\n"
                "     return os.getcwd()\n"
                "diff --git a/docs/notes.md b/docs/notes.md\n"
                "--- a/docs/notes.md\n"
                "+++ b/docs/notes.md\n"
                "@@ -1,0 +1,1 @@\n"
                "+# return value semantics and design notes\n"
            )
            files = parse_diff(sample_diff)
            findings, _ = analyze_diff(files, str(root))
            self.assertTrue(
                any("unused import" in f.title.lower() and "json" in f.title.lower() for f in findings),
                [f.title for f in findings],
            )
            self.assertTrue(
                any(f.file_path == "src/clean.py" and "dead code" in f.title.lower() for f in findings),
                [f.title for f in findings],
            )
            self.assertFalse(
                any(f.file_path == "docs/notes.md" and "dead code" in f.title.lower() for f in findings),
                [f.title for f in findings],
            )

    def test_v21_staged_bloat_factual_cove_and_readonly_hmac_key(self):
        from tools.orchestration.solo_contracts import get_receipt_hmac_key_readonly

        sample_diff = (
            "diff --git a/src/slow.py b/src/slow.py\n"
            "--- a/src/slow.py\n"
            "+++ b/src/slow.py\n"
            "@@ -1,1 +1,3 @@\n"
            "+import time\n"
            "+def wait_briefly():\n"
            "+    time.sl" + "eep(1)\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            (root / "src").mkdir()
            (root / "src" / "slow.py").write_text(
                "import time\ndef wait_briefly():\n    time.sl" + "eep(1)\n",
                encoding="utf-8",
            )
            out_md = root / "review.md"
            buf = io.StringIO()
            with patch.object(senior_code_review, "get_git_diff", return_value=sample_diff), \
                 patch.object(OutputDiffSentinel, "audit_git_diff", return_value=(True, [])) as mock_audit, \
                 redirect_stdout(buf):
                rc = run_review(
                    str(root),
                    target="staged",
                    as_json=True,
                    output_md=str(out_md),
                    verify_report=True,
                )

            self.assertEqual(rc, 0)
            mock_audit.assert_called_once_with(str(root), target="staged")
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed["cove_verification"]["status"], "PASS")
            self.assertEqual(parsed["cove_confidence_pct"], 100.0)

            # Tampered report citing a non-existent file must fail factual claim check
            tampered_md = root / "tampered_review.md"
            tampered_md.write_text(
                out_md.read_text(encoding="utf-8") + "\n#### 9. **Ghost** (`src/ghost_missing.py:99`)\n",
                encoding="utf-8",
            )
            cove_bad = senior_code_review.verify_markdown_report(str(tampered_md), repo_dir=str(root))
            self.assertEqual(cove_bad["status"], "DISCREPANCY_DETECTED")
            self.assertLess(cove_bad["factual_confidence_pct"], 100.0)

            # Read-only HMAC lookup never creates .git/synapse_receipt_hmac.key
            with patch.dict(os.environ, {"SYNAPSE_RECEIPT_HMAC_KEY": ""}, clear=False):
                os.environ.pop("SYNAPSE_RECEIPT_HMAC_KEY", None)
                key_path = root / ".git" / "synapse_receipt_hmac.key"
                self.assertFalse(key_path.exists())
                _ = get_receipt_hmac_key_readonly(str(root))
                self.assertFalse(key_path.exists())

    def test_v21_untracked_diff_boundaries_quoted_paths_and_frozen_dtos(self):
        import subprocess
        from dataclasses import FrozenInstanceError
        from senior_code_review import (
            ReportClaimVerificationDTO,
            UntrackedFileDiffDTO,
            build_untracked_file_diff,
            get_git_diff,
        )

        # 1. Verify frozen immutability of new DTOs
        u_dto = UntrackedFileDiffDTO(rel_path="a.py", line_count=1, is_binary=False, truncated=False)
        r_dto = ReportClaimVerificationDTO(
            status="PASS", factual_confidence_pct=100.0, total_claims_checked=1, verified_claims=1, discrepancies=()
        )
        with self.assertRaises(FrozenInstanceError):
            u_dto.line_count = 2  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            r_dto.status = "FAIL"  # type: ignore[misc]

        # 2. Quoted git diff path with spaces
        quoted_diff = (
            'diff --git "a/dir name/my file.py" "b/dir name/my file.py"\n'
            '--- "a/dir name/my file.py"\n'
            '+++ "b/dir name/my file.py"\n'
            "@@ -1,0 +1,1 @@\n"
            "+x = 1\n"
        )
        q_files = parse_diff(quoted_diff)
        self.assertEqual(len(q_files), 1)
        self.assertEqual(q_files[0]["path"], "dir name/my file.py")
        self.assertEqual(senior_code_review._unquote_git_path('"b/a b.py"'), "a b.py")
        self.assertEqual(senior_code_review._unquote_git_path("x"), "x")

        # 3. Git repo boundaries: clean untracked, .cache skip, binary skip, max_bytes truncation, tracked without trailing NL
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            subprocess.run(["git", "init"], cwd=root, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=root, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=root, capture_output=True, check=True)
            (root / "tracked.txt").write_bytes(b"line1")
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True, check=True)

            # Empty untracked
            self.assertEqual(build_untracked_file_diff(str(root)), "")

            # Non-zero git ls-files exit with non-empty stdout must return ""
            fake_err = type("P", (), {"returncode": 1, "stdout": "stale.py\n"})()
            with patch("senior_code_review.subprocess.run", return_value=fake_err):
                self.assertEqual(build_untracked_file_diff(str(root)), "")

            # Ignored prefix (.cache), binary file, and oversized text file
            (root / ".cache").mkdir()
            (root / ".cache" / "skip.py").write_text("x = 1\n", encoding="utf-8")
            (root / "bin.dat").write_bytes(b"ELF\x00\x01\x02")
            (root / "big.py").write_text("a = 1\n" * 20, encoding="utf-8")
            (root / "tracked.txt").write_bytes(b"line1\nline2_no_nl")

            trunc_diff = build_untracked_file_diff(str(root), max_bytes=12)
            self.assertIn("+++ b/big.py", trunc_diff)
            self.assertIn("+a = 1\n+a = 1", trunc_diff)
            self.assertNotIn(".cache/skip.py", trunc_diff)
            self.assertNotIn("bin.dat", trunc_diff)
            self.assertLessEqual(len(trunc_diff.splitlines()), 10)

            full_untracked = get_git_diff(str(root), target="uncommitted")
            self.assertIn("diff --git a/big.py b/big.py", full_untracked)
            self.assertIn("+line2_no_nl\n\\ No newline at end of file\ndiff --git", full_untracked)


if __name__ == "__main__":
    unittest.main()
