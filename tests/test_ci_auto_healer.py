#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tests/test_ci_auto_healer.py — 4-Scenario Test Battery for CI/CD Auto-Healer
-----------------------------------------------------------------------------
Covers:
  1. Positive Scenarios: JUnit XML + stacktrace ingestion, eligible lint/locator healing,
     --apply patch application, --verify-cmd pass, PR markdown generation.
  2. Negative Scenarios: AUT/logic defect rejection (no bug masking), verification failure
     triggering path-scoped rollback, Clean POM violation rejection, failed gh CLI handling.
  3. Boundary Scenarios: Empty artifacts directory, malformed JUnit XML, max_fixes cap,
     missing target files.
  4. CLI Flag Scenarios: --dry-run, --json, --out-pr, --artifacts-dir, --max-fixes, --run-id, --fetch-gh.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
for _p in (ROOT_DIR, TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.heal.ci_auto_healer import (
    AUT_OR_LOGIC_DEFECT,
    AUTO_FIX_LINT,
    CI_ENV_DEFECT,
    LOCATOR_HEAL,
    build_parser,
    classify_failure,
    collect_ci_failures,
    fetch_gh_failed_run,
    main,
    run_ci_auto_heal,
)


def _write_junit_xml(path, tc_name: str, reason: str, trace: str) -> None:
    xml_body = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<testsuite name="ci-suite" tests="1" failures="1" errors="0">\n'
        f'  <testcase classname="suite.e2e" name="{tc_name}" time="1.2">\n'
        f'    <failure message="{reason}">{trace}</failure>\n'
        "  </testcase>\n"
        "</testsuite>\n"
    )
    path.write_text(xml_body, encoding="utf-8")


class TestCIAutoHealerPositive:
    """Scenario 1: Positive end-to-end ingestion, healing, verification, and PR draft."""

    def test_heals_eligible_lint_and_locator_failures_and_verifies(self, tmp_path):
        page_file = tmp_path / "src" / "pages" / "LoginPage.ts"
        page_file.parent.mkdir(parents=True)
        page_file.write_text(
            "export class LoginPage {\n"
            "  async submit() {\n"
            "    await page.waitForTimeout(3000);\n"
            "    await page.click('#old-btn');\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        junit_file = artifacts / "e2e_junit.xml"
        _write_junit_xml(
            junit_file,
            "test_login_submit",
            "TimeoutError: waiting for locator('#old-btn') to be visible",
            f"TimeoutError: waiting for locator('#old-btn')\n    at LoginPage.submit ({page_file}:4:11)",
        )

        pr_out = tmp_path / "auto_heal_pr.md"
        result = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(artifacts),
            apply_patches=True,
            verify_cmd=f"{sys.executable} -c \"import sys; sys.exit(0)\"",
            out_pr=str(pr_out),
            run_id="998877",
        )

        assert result["status"] == "HEALED_AND_VERIFIED"
        assert result["applied_count"] >= 1
        assert result["verified"] is True
        assert result["rolled_back"] is False
        assert result["triage_breakdown"]["auto_fix_lint"] >= 1
        assert pr_out.is_file()
        pr_text = pr_out.read_text(encoding="utf-8")
        assert "998877" in pr_text
        assert "LoginPage.ts" in pr_text
        assert "### Skipped CI / Environment Defects (Runner / Setup)\n- None" in pr_text

        updated = page_file.read_text(encoding="utf-8")
        assert "waitForTimeout(3000)" not in updated
        assert "#old-btn" not in updated
        assert not (page_file.parent / "LoginPage.ts.bak").exists()

    def test_dry_run_plans_patches_without_mutating_disk(self, tmp_path):
        test_file = tmp_path / "tests" / "checkout.spec.ts"
        test_file.parent.mkdir(parents=True)
        original = (
            "test('checkout', async ({ page }) => {\n"
            "  await page.waitForTimeout(2000);\n"
            "  expect(page.getByText('Done'));\n"
            "});\n"
        )
        test_file.write_text(original, encoding="utf-8")

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        log_file = artifacts / "ci_failed.log"
        log_file.write_text(
            f"EXCESSIVE_HARD_DELAY detected at {test_file}:2:3\n",
            encoding="utf-8",
        )

        result = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(artifacts),
            apply_patches=False,
        )

        assert result["status"] == "DRY_RUN_PLANNED"
        assert result["applied_count"] == 0
        assert result["planned_count"] >= 1
        assert test_file.read_text(encoding="utf-8") == original


class TestCIAutoHealerNegative:
    """Scenario 2: Negative cases, AUT defect isolation, and rollback on failed verification."""

    def test_refuses_to_mask_aut_or_logic_defects(self, tmp_path):
        api_test = tmp_path / "tests" / "test_api.py"
        api_test.parent.mkdir(parents=True)
        original = "def test_create_order():\n    assert response.status_code == 201\n"
        api_test.write_text(original, encoding="utf-8")

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        junit_file = artifacts / "api_junit.xml"
        _write_junit_xml(
            junit_file,
            "test_create_order",
            "AssertionError: expected HTTP 201 but got 500 Internal Server Error",
            f'File "{api_test}", line 2, in test_create_order\nAssertionError: 500 != 201',
        )

        classified = classify_failure(
            {
                "tc": "test_create_order",
                "reason": "AssertionError: expected HTTP 201 but got 500 Internal Server Error",
                "file": str(api_test),
                "line": "2",
            }
        )
        assert classified["category"] == AUT_OR_LOGIC_DEFECT
        assert classified["eligible"] is False

        result = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(artifacts),
            apply_patches=True,
        )
        assert result["applied_count"] == 0
        assert len(result["skipped_aut_defects"]) == 1
        assert api_test.read_text(encoding="utf-8") == original

    def test_verification_failure_rolls_back_patched_files(self, tmp_path):
        page_file = tmp_path / "pages" / "OrderPage.ts"
        page_file.parent.mkdir(parents=True)
        original = (
            "export class OrderPage {\n"
            "  async confirm() {\n"
            "    await page.click('#confirm-old');\n"
            "  }\n"
            "}\n"
        )
        page_file.write_text(original, encoding="utf-8")

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        junit_file = artifacts / "ui_junit.xml"
        _write_junit_xml(
            junit_file,
            "test_confirm_order",
            "TimeoutError: waiting for locator('#confirm-old')",
            f"TimeoutError: locator('#confirm-old')\n    at OrderPage.confirm ({page_file}:3:11)",
        )

        result = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(artifacts),
            apply_patches=True,
            verify_cmd=f"{sys.executable} -c \"import sys; sys.exit(1)\"",
        )

        assert result["status"] == "VERIFICATION_FAILED_ROLLED_BACK"
        assert result["verified"] is False
        assert result["rolled_back"] is True
        assert page_file.read_text(encoding="utf-8") == original

    def test_fetch_gh_handles_missing_cli_gracefully(self, tmp_path):
        with patch("tools.heal.ci_auto_healer.shutil.which", return_value=None):
            res = fetch_gh_failed_run(repo_root=str(tmp_path), run_id="12345")
        assert res["ok"] is False
        assert "gh" in res["error"].lower()

    def test_fetch_gh_handles_subprocess_error_gracefully(self, tmp_path):
        mock_proc = MagicMock(returncode=1, stdout="", stderr="not authenticated")
        with patch("tools.heal.ci_auto_healer.shutil.which", return_value="/usr/bin/gh"), patch(
            "tools.heal.ci_auto_healer.subprocess.run", return_value=mock_proc
        ):
            res = fetch_gh_failed_run(repo_root=str(tmp_path), run_id=None)
        assert res["ok"] is False
        assert "not authenticated" in res["error"]


class TestCIAutoHealerBoundary:
    """Scenario 3: Boundary cases (empty dirs, malformed XML, max_fixes cap)."""

    def test_empty_artifacts_directory_returns_no_failures(self, tmp_path):
        empty_dir = tmp_path / "empty_artifacts"
        empty_dir.mkdir()
        collected = collect_ci_failures(str(empty_dir))
        assert collected["failures"] == []

        result = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(empty_dir),
            apply_patches=True,
        )
        assert result["status"] == "NO_FAILURES_FOUND"
        assert result["applied_count"] == 0
        assert result["triage_breakdown"]["ci_env_defect"] == 0

    def test_malformed_xml_does_not_crash_collector(self, tmp_path):
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        bad_xml = artifacts / "corrupt_junit.xml"
        bad_xml.write_text("<testsuite><broken", encoding="utf-8")

        collected = collect_ci_failures(str(artifacts))
        assert isinstance(collected["failures"], list)
        assert len(collected["failures"]) == 0

    def test_max_fixes_caps_number_of_applied_repairs(self, tmp_path):
        pages = tmp_path / "pages"
        pages.mkdir()
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()

        for idx in range(3):
            p = pages / f"Page{idx}.ts"
            p.write_text(
                f"export class Page{idx} {{\n  async act() {{ await page.click('#btn-{idx}'); }}\n}}\n",
                encoding="utf-8",
            )
            _write_junit_xml(
                artifacts / f"suite_{idx}.xml",
                f"tc_{idx}",
                f"TimeoutError: waiting for locator('#btn-{idx}')",
                f"TimeoutError: locator('#btn-{idx}')\n    at Page{idx}.act ({p}:2:24)",
            )

        result = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(artifacts),
            apply_patches=True,
            max_fixes=1,
        )
        assert result["applied_count"] == 1
        assert result["skipped_cap_count"] >= 2


class TestCIAutoHealerCLI:
    """Scenario 4: CLI flags, parser contract, and --json / --out-pr / --run-id behavior."""

    def test_cli_json_dry_run_and_out_pr_flags(self, tmp_path, capsys):
        page_file = tmp_path / "pages" / "ProfilePage.ts"
        page_file.parent.mkdir(parents=True)
        page_file.write_text(
            "export class ProfilePage {\n  async save() {\n    await page.click('#save-old');\n  }\n}\n",
            encoding="utf-8",
        )
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        _write_junit_xml(
            artifacts / "profile_junit.xml",
            "test_profile_save",
            "TimeoutError: waiting for locator('#save-old')",
            f"TimeoutError: locator('#save-old')\n    at ProfilePage.save ({page_file}:3:11)",
        )
        pr_file = tmp_path / "pr_body.md"

        exit_code = main(
            [
                "--repo-root",
                str(tmp_path),
                "--artifacts-dir",
                str(artifacts),
                "--dry-run",
                "--max-fixes",
                "3",
                "--run-id",
                "445566",
                "--out-pr",
                str(pr_file),
                "--json",
            ]
        )

        assert exit_code == 0
        captured = capsys.readouterr().out
        payload = json.loads(captured)
        assert payload["status"] == "DRY_RUN_PLANNED"
        assert payload["run_id"] == "445566"
        assert pr_file.is_file()

    def test_cli_fetch_gh_flag_with_mocked_gh(self, tmp_path, capsys):
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        mock_view = MagicMock(returncode=0, stdout="", stderr="")
        with patch("tools.heal.ci_auto_healer.shutil.which", return_value="/usr/bin/gh"), patch(
            "tools.heal.ci_auto_healer.subprocess.run", return_value=mock_view
        ):
            exit_code = main(
                [
                    "--repo-root",
                    str(tmp_path),
                    "--artifacts-dir",
                    str(artifacts),
                    "--fetch-gh",
                    "--run-id",
                    "778899",
                    "--json",
                ]
            )
        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["run_id"] == "778899"

    def test_parser_exposes_expected_cli_flags(self):
        parser = build_parser()
        args = parser.parse_args(["--artifacts-dir", "artifacts", "--apply", "--create-pr", "--json"])
        assert args.artifacts_dir == "artifacts"
        assert args.apply is True
        assert args.create_pr is True
        assert args.json is True


class TestCIAutoHealerEdgeAndTriageCoverage:
    """Additional triage, trace-fallback, and file-collection assertions."""

    def test_classify_failure_uses_trace_and_rejects_unclassified(self):
        lint_case = classify_failure({"reason": "Test failed due to waitForTimeout(3000)"})
        assert lint_case["category"] == AUTO_FIX_LINT
        assert lint_case["eligible"] is True

        locator_case = classify_failure({"reason": "TimeoutError: waiting for locator('#btn')"})
        assert locator_case["category"] == LOCATOR_HEAL
        assert locator_case["eligible"] is True

        trace_only = classify_failure({"reason": "Test failed", "trace": "AssertionError: 500"})
        assert trace_only["category"] == AUT_OR_LOGIC_DEFECT
        assert trace_only["eligible"] is False

        unknown = classify_failure({"reason": "Unexpected cosmic ray event"})
        assert unknown["category"] == AUT_OR_LOGIC_DEFECT
        assert unknown["eligible"] is False

    def test_collect_ci_failures_dedupes_logs_ignores_png_and_preserves_unknown_file(self, tmp_path):
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        log_file = artifacts / "ci.log"
        log_file.write_text("TimeoutError: waiting for locator('#x') at UnknownFile:12\n", encoding="utf-8")
        (artifacts / "screenshot.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        _write_junit_xml(
            artifacts / "no_stack.xml",
            "test_missing_stack",
            "TimeoutError: waiting for locator('#missing')",
            "No stack frame available",
        )

        collected = collect_ci_failures(
            artifacts_dir=str(artifacts),
            error_log=str(log_file),
            repo_root=str(tmp_path),
        )
        assert collected["log_files"] == [str(log_file)]
        assert any(f["file"] == "UnknownFile" for f in collected["failures"])
        assert all(not p.endswith(".png") for p in collected["log_files"])

    def test_create_pr_creates_branch_and_returns_pr_url(self, tmp_path):
        page_file = tmp_path / "pages" / "CheckoutPage.ts"
        page_file.parent.mkdir(parents=True)
        page_file.write_text(
            "export class CheckoutPage {\n  async pay() {\n    await page.click('#pay-old');\n  }\n}\n",
            encoding="utf-8",
        )
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        _write_junit_xml(
            artifacts / "checkout_junit.xml",
            "test_checkout_pay",
            "TimeoutError: waiting for locator('#pay-old')",
            f"TimeoutError: locator('#pay-old')\n    at CheckoutPage.pay ({page_file}:3:11)",
        )

        def _fake_run(cmd, **kwargs):
            if cmd and cmd[0] == "/usr/bin/gh" and "pr" in cmd:
                return MagicMock(returncode=0, stdout="https://github.com/org/repo/pull/42\n", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("tools.heal.ci_auto_healer.shutil.which", return_value="/usr/bin/gh"), patch(
            "tools.heal.ci_auto_healer.subprocess.run", side_effect=_fake_run
        ):
            result = run_ci_auto_heal(
                repo_root=str(tmp_path),
                artifacts_dir=str(artifacts),
                apply_patches=True,
                create_pr=True,
                run_id="556677",
            )

        assert result["status"] == "HEALED"
        assert result["pr_info"]["created"] is True
        assert result["pr_info"]["pr_url"] == "https://github.com/org/repo/pull/42"

    def test_verify_cmd_timeout_or_invalid_command_rolls_back(self, tmp_path):
        import subprocess

        page_file = tmp_path / "pages" / "BillingPage.ts"
        page_file.parent.mkdir(parents=True)
        original = (
            "export class BillingPage {\n"
            "  async pay() {\n"
            "    await page.click('#bill-old');\n"
            "  }\n"
            "}\n"
        )
        page_file.write_text(original, encoding="utf-8")
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        _write_junit_xml(
            artifacts / "bill_junit.xml",
            "test_bill_pay",
            "TimeoutError: waiting for locator('#bill-old')",
            f"TimeoutError: locator('#bill-old')\n    at BillingPage.pay ({page_file}:3:11)",
        )

        with patch(
            "tools.heal.ci_auto_healer.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="verify", timeout=300),
        ):
            res_timeout = run_ci_auto_heal(
                repo_root=str(tmp_path),
                artifacts_dir=str(artifacts),
                apply_patches=True,
                verify_cmd="pytest tests/nonexistent.py",
            )
        assert res_timeout["status"] == "VERIFICATION_FAILED_ROLLED_BACK"
        assert res_timeout["verified"] is False
        assert res_timeout["rolled_back"] is True
        assert page_file.read_text(encoding="utf-8") == original

        res_bad_quote = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(artifacts),
            apply_patches=True,
            verify_cmd="pytest 'unclosed",
        )
        assert res_bad_quote["status"] == "VERIFICATION_FAILED_ROLLED_BACK"
        assert res_bad_quote["rolled_back"] is True
        assert page_file.read_text(encoding="utf-8") == original

    def test_multi_failure_same_file_and_unhealable_locator_does_not_patch_lint(self, tmp_path):
        page_file = tmp_path / "pages" / "MultiPage.ts"
        page_file.parent.mkdir(parents=True)
        page_file.write_text(
            "export class MultiPage {\n"
            "  async stepOne() {\n"
            "    await page.click('#first-old');\n"
            "  }\n"
            "  async stepTwo() {\n"
            "    await page.click('#second-old');\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        unhealable = tmp_path / "pages" / "NoLocPage.ts"
        unhealable_orig = (
            "export class NoLocPage {\n"
            "  async noop() {\n"
            "    await page.waitForTimeout(1000);\n"
            "    return true;\n"
            "  }\n"
            "}\n"
        )
        unhealable.write_text(unhealable_orig, encoding="utf-8")

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        _write_junit_xml(
            artifacts / "m1.xml",
            "test_step_one",
            "TimeoutError: waiting for locator('#first-old')",
            f"TimeoutError: locator('#first-old')\n    at MultiPage.stepOne ({page_file}:3:11)",
        )
        _write_junit_xml(
            artifacts / "m2.xml",
            "test_step_two",
            "TimeoutError: waiting for locator('#second-old')",
            f"TimeoutError: locator('#second-old')\n    at MultiPage.stepTwo ({page_file}:6:11)",
        )
        _write_junit_xml(
            artifacts / "noloc.xml",
            "test_unhealable",
            "TimeoutError: waiting for locator('#missing')",
            f"TimeoutError: locator('#missing')\n    at NoLocPage.noop ({unhealable}:4:5)",
        )

        result = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(artifacts),
            apply_patches=True,
        )
        updated_multi = page_file.read_text(encoding="utf-8")
        assert "#first-old" not in updated_multi
        assert "#second-old" not in updated_multi
        assert unhealable.read_text(encoding="utf-8") == unhealable_orig
        assert result["applied_count"] == 2

    def test_create_pr_restores_original_branch_on_failure(self, tmp_path):
        page_file = tmp_path / "pages" / "BranchPage.ts"
        page_file.parent.mkdir(parents=True)
        page_file.write_text(
            "export class BranchPage {\n  async go() {\n    await page.click('#go-old');\n  }\n}\n",
            encoding="utf-8",
        )
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        _write_junit_xml(
            artifacts / "branch_junit.xml",
            "test_branch_go",
            "TimeoutError: waiting for locator('#go-old')",
            f"TimeoutError: locator('#go-old')\n    at BranchPage.go ({page_file}:3:11)",
        )

        cmds = []

        def _fake_run(cmd, **kwargs):
            cmds.append(cmd)
            if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
                return MagicMock(returncode=0, stdout="feature/ci-target\n", stderr="")
            if cmd[:2] == ["git", "commit"]:
                return MagicMock(returncode=1, stdout="", stderr="commit rejected")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("tools.heal.ci_auto_healer.shutil.which", return_value="/usr/bin/gh"), patch(
            "tools.heal.ci_auto_healer.subprocess.run", side_effect=_fake_run
        ):
            result = run_ci_auto_heal(
                repo_root=str(tmp_path),
                artifacts_dir=str(artifacts),
                apply_patches=True,
                create_pr=True,
                run_id="334455",
            )

        assert result["pr_info"]["created"] is False
        assert any(c[:3] == ["git", "checkout", "feature/ci-target"] for c in cmds)


class TestCIAutoHealerCopilotIntegration:
    """Milestone M2: Copilot CLI fallback, Copilot Issue escalation, and prompt generation."""

    def test_copilot_prompt_generated_and_skips_cli_when_deterministic_succeeds(self, tmp_path):
        page_file = tmp_path / "pages" / "DonePage.ts"
        page_file.parent.mkdir(parents=True)
        page_file.write_text(
            "export class DonePage {\n  async ok() {\n    await page.click('#ok-old');\n  }\n}\n",
            encoding="utf-8",
        )
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        _write_junit_xml(
            artifacts / "done_junit.xml",
            "test_done_ok",
            "TimeoutError: waiting for locator('#ok-old')",
            f"TimeoutError: locator('#ok-old')\n    at DonePage.ok ({page_file}:3:11)",
        )
        prompt_out = tmp_path / "copilot_prompt.md"

        with patch("tools.heal.ci_auto_healer.shutil.which") as mock_which:
            result = run_ci_auto_heal(
                repo_root=str(tmp_path),
                artifacts_dir=str(artifacts),
                apply_patches=True,
                copilot_fallback=True,
                out_copilot_prompt=str(prompt_out),
            )

        assert result["status"] == "HEALED"
        assert result["needs_ai_escalation"] is False
        assert prompt_out.is_file()
        mock_which.assert_not_called()

    def test_copilot_fallback_heals_unresolved_locator_and_verifies(self, tmp_path):
        page_file = tmp_path / "pages" / "ComplexPage.ts"
        page_file.parent.mkdir(parents=True)
        original = (
            "export class ComplexPage {\n"
            "  async submit() {\n"
            "    await this.customHelper();\n"
            "  }\n"
            "}\n"
        )
        page_file.write_text(original, encoding="utf-8")
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        _write_junit_xml(
            artifacts / "complex_junit.xml",
            "test_complex_submit",
            "TimeoutError: waiting for locator('#dynamic-shadow')",
            f"TimeoutError: waiting for locator('#dynamic-shadow')\n    at ComplexPage.submit ({page_file}:3:5)",
        )
        prompt_out = tmp_path / "copilot_prompt.md"

        status_calls = {"n": 0}

        def _fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "status"]:
                status_calls["n"] += 1
                if status_calls["n"] == 1:
                    return MagicMock(returncode=0, stdout="", stderr="")
                return MagicMock(returncode=0, stdout=" M pages/ComplexPage.ts\n", stderr="")
            if cmd and cmd[0] == "/usr/bin/copilot":
                page_file.write_text(
                    "export class ComplexPage {\n"
                    "  async submit() {\n"
                    "    await this.page.getByRole('button', { name: 'Submit' }).click();\n"
                    "  }\n"
                    "}\n",
                    encoding="utf-8",
                )
                return MagicMock(returncode=0, stdout="Patched ComplexPage.ts", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("tools.heal.ci_auto_healer.shutil.which", return_value="/usr/bin/copilot"), patch(
            "tools.heal.ci_auto_healer.subprocess.run", side_effect=_fake_run
        ):
            result = run_ci_auto_heal(
                repo_root=str(tmp_path),
                artifacts_dir=str(artifacts),
                apply_patches=True,
                verify_cmd=f"{sys.executable} -c \"import sys; sys.exit(0)\"",
                copilot_fallback=True,
                out_copilot_prompt=str(prompt_out),
                run_id="889900",
            )

        assert result["status"] == "COPILOT_HEALED_AND_VERIFIED"
        assert result["verified"] is True
        assert result["copilot_fallback"]["attempted"] is True
        assert result["copilot_fallback"]["ok"] is True
        assert prompt_out.is_file()
        assert "DO NOT weaken assertions" in prompt_out.read_text(encoding="utf-8")

    def test_copilot_fallback_rolls_back_on_verify_failure_and_skips_pure_aut_bugs(self, tmp_path):
        # 1. Pure AUT defect must NEVER invoke Copilot CLI to alter test assertions
        api_test = tmp_path / "tests" / "test_orders.py"
        api_test.parent.mkdir(parents=True)
        api_test.write_text("def test_order():\n    assert False\n", encoding="utf-8")
        aut_artifacts = tmp_path / "aut_artifacts"
        aut_artifacts.mkdir()
        _write_junit_xml(
            aut_artifacts / "aut.xml",
            "test_order",
            "AssertionError: HTTP 500 Internal Server Error",
            f'File "{api_test}", line 2, in test_order',
        )

        with patch("tools.heal.ci_auto_healer.shutil.which") as mock_which:
            aut_res = run_ci_auto_heal(
                repo_root=str(tmp_path),
                artifacts_dir=str(aut_artifacts),
                apply_patches=True,
                copilot_fallback=True,
            )
        assert aut_res["status"] == "AUT_DEFECTS_ONLY_NO_PATCH"
        assert aut_res["needs_ai_escalation"] is False
        mock_which.assert_not_called()

        # 2. Failed verification after Copilot edit must roll back file to pre-Copilot state
        page_file = tmp_path / "pages" / "BrokenPage.ts"
        page_file.parent.mkdir(parents=True)
        original = "export class BrokenPage {\n  async go() {\n    await this.missing();\n  }\n}\n"
        page_file.write_text(original, encoding="utf-8")
        ui_artifacts = tmp_path / "ui_artifacts"
        ui_artifacts.mkdir()
        _write_junit_xml(
            ui_artifacts / "ui.xml",
            "test_broken_go",
            "TimeoutError: waiting for locator('#ghost')",
            f"TimeoutError: waiting for locator('#ghost')\n    at BrokenPage.go ({page_file}:3:5)",
        )

        status_calls = {"n": 0}

        def _fake_run_fail_verify(cmd, **kwargs):
            if cmd[:2] == ["git", "status"]:
                status_calls["n"] += 1
                if status_calls["n"] == 1:
                    return MagicMock(returncode=0, stdout="", stderr="")
                return MagicMock(returncode=0, stdout=" M pages/BrokenPage.ts\n", stderr="")
            if cmd and cmd[0] == "/usr/bin/copilot":
                page_file.write_text("export class BrokenPage { broken }\n", encoding="utf-8")
                return MagicMock(returncode=0, stdout="Edited", stderr="")
            if cmd and cmd[0] == sys.executable:
                return MagicMock(returncode=1, stdout="", stderr="verify failed")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("tools.heal.ci_auto_healer.shutil.which", return_value="/usr/bin/copilot"), patch(
            "tools.heal.ci_auto_healer.subprocess.run", side_effect=_fake_run_fail_verify
        ):
            fail_res = run_ci_auto_heal(
                repo_root=str(tmp_path),
                artifacts_dir=str(ui_artifacts),
                apply_patches=True,
                verify_cmd=f"{sys.executable} -c \"import sys; sys.exit(1)\"",
                copilot_fallback=True,
            )

        assert fail_res["status"] == "VERIFICATION_FAILED_ROLLED_BACK"
        assert fail_res["copilot_fallback"]["rolled_back"] is True
        assert page_file.read_text(encoding="utf-8") == original

    def test_copilot_issue_opens_issue_and_cli_flags_accepted(self, tmp_path, capsys):
        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        _write_junit_xml(
            artifacts / "aut.xml",
            "test_checkout_500",
            "AssertionError: HTTP 500 Internal Server Error",
            "AssertionError: 500 != 200",
        )
        prompt_out = tmp_path / "prompt.md"

        def _fake_gh_issue(cmd, **kwargs):
            if cmd and "issue" in cmd and "create" in cmd:
                return MagicMock(returncode=0, stdout="https://github.com/org/repo/issues/101\n", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("tools.heal.ci_auto_healer.shutil.which", return_value="/usr/bin/gh"), patch(
            "tools.heal.ci_auto_healer.subprocess.run", side_effect=_fake_gh_issue
        ):
            rc = main(
                [
                    "--repo-root",
                    str(tmp_path),
                    "--artifacts-dir",
                    str(artifacts),
                    "--apply",
                    "--copilot-issue",
                    "--out-copilot-prompt",
                    str(prompt_out),
                    "--run-id",
                    "112233",
                    "--json",
                ]
            )

        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["copilot_issue"]["created"] is True
        assert payload["copilot_issue"]["issue_url"] == "https://github.com/org/repo/issues/101"
        assert prompt_out.is_file()

        parser = build_parser()
        parsed = parser.parse_args(["--copilot-fallback", "--copilot-issue", "--out-copilot-prompt", "p.md"])
        assert parsed.copilot_fallback is True
        assert parsed.copilot_issue is True
        assert parsed.out_copilot_prompt == "p.md"


class TestCIAutoHealerEnvDefects:
    """CI/Environment defect classification (never mislabeled as AUT product bugs)."""

    def test_classifies_missing_playwright_browser_as_ci_env_defect(self, tmp_path):
        spec_file = tmp_path / "tests" / "auth.spec.ts"
        spec_file.parent.mkdir(parents=True)
        original = "test('login', async ({ page }) => { await page.goto('/'); });\n"
        spec_file.write_text(original, encoding="utf-8")

        missing_target = classify_failure(
            {"tc": "rc-lane", "reason": "Missing required release-candidate target CRM_BASE_URL"}
        )
        assert missing_target["category"] == CI_ENV_DEFECT
        assert missing_target["eligible"] is False

        classified = classify_failure(
            {
                "tc": "TC-LOGIN-01",
                "reason": f"browserType.launch: Executable doesn't exist at {tmp_path}/ms-playwright/webkit-2388/pw_run.sh",
                "file": str(spec_file),
                "line": "1",
            }
        )
        assert classified["category"] == CI_ENV_DEFECT
        assert classified["eligible"] is False

        artifacts = tmp_path / "artifacts"
        artifacts.mkdir()
        _write_junit_xml(
            artifacts / "e2e_junit.xml",
            "TC-LOGIN-01",
            f"browserType.launch: Executable doesn't exist at {tmp_path}/ms-playwright/firefox-1572/firefox/firefox",
            f"browserType.launch: Executable doesn't exist\n    at {spec_file}:1:1",
        )
        pr_out = tmp_path / "auto_heal_pr.md"
        result = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(artifacts),
            apply_patches=True,
            out_pr=str(pr_out),
        )

        assert result["status"] == "CI_ENV_DEFECTS_ONLY_NO_PATCH"
        assert result["applied_count"] == 0
        assert result["triage_breakdown"]["ci_env_defect"] == 1
        assert len(result["skipped_env_defects"]) == 1
        assert result["skipped_aut_defects"] == []
        assert spec_file.read_text(encoding="utf-8") == original
        pr_text = pr_out.read_text(encoding="utf-8")
        assert "Skipped CI / Environment Defects" in pr_text
        assert "Executable doesn't exist" in pr_text

    def test_mixed_env_aut_and_missing_target_statuses_and_cli_summary(self, tmp_path, capsys):
        mixed_artifacts = tmp_path / "mixed"
        mixed_artifacts.mkdir()
        _write_junit_xml(
            mixed_artifacts / "env.xml",
            "tc_env",
            "Missing required release-candidate target CRM_BASE_URL",
            "env error",
        )
        _write_junit_xml(
            mixed_artifacts / "aut.xml",
            "tc_aut",
            "AssertionError: expected 200 got 500",
            "AssertionError",
        )

        dry_mixed = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(mixed_artifacts),
            apply_patches=False,
        )
        assert dry_mixed["status"] == "AUT_DEFECTS_ONLY_NO_PATCH"

        apply_mixed = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(mixed_artifacts),
            apply_patches=True,
        )
        assert apply_mixed["status"] == "AUT_DEFECTS_ONLY_NO_PATCH"

        missing_artifacts = tmp_path / "missing_file"
        missing_artifacts.mkdir()
        _write_junit_xml(
            missing_artifacts / "loc.xml",
            "tc_loc",
            "TimeoutError: waiting for locator('#x')",
            "TimeoutError at nonexistent/Page.ts:10:5",
        )
        res_missing = run_ci_auto_heal(
            repo_root=str(tmp_path),
            artifacts_dir=str(missing_artifacts),
            apply_patches=True,
        )
        assert res_missing["status"] == "NO_ELIGIBLE_PATCHES"

        env_only = tmp_path / "env_only"
        env_only.mkdir()
        _write_junit_xml(
            env_only / "env.xml",
            "tc_env_cli",
            "Missing required release-candidate target API_URL",
            "env error",
        )
        copilot_out = tmp_path / "env_copilot_prompt.md"
        rc = main(
            [
                "--repo-root",
                str(tmp_path),
                "--artifacts-dir",
                str(env_only),
                "--out-copilot-prompt",
                str(copilot_out),
            ]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "Skipped Env: 1" in out
        assert "## Skipped CI / Environment Defects" in copilot_out.read_text(encoding="utf-8")





