#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
Comprehensive 4-Scenario Regression Suite for Hub Rules & Skills Perfection Overhaul (M1-M14).
Covers Positive, Negative, Boundary, and CLI/Subprocess contracts across:
  - M1-M3: Dynamic AGENTS.md AST parser & Multi-IDE rule synchronization
  - M4: Canonical 12/13-column Manual QA contract & @REQ-xxx RTM traceability
  - M5, M8: Skill canonical code-fence linting (ban waitForTimeout & networkidle)
  - M6: Mode-split Gate 10 Performance SLA (HUB microbenchmark vs CLIENT fail-closed)
  - M7: Fail-closed PreToolUse hook & context-aware Safety Firewall risk tiers
  - M9: Invariant 16 English-only enforcement across standards/ and testing/
  - M10-M12: lean-impact-scoreboard relocation & skill router/manifest parity
  - M13-M14: Bilingual # language: vi Gherkin compiler & ADR-0021 verification
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

_DEFAULT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.getcwd() if os.path.isfile(os.path.join(os.getcwd(), "AGENTS.md")) else _DEFAULT_ROOT
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# ============================================================================
# M1 - M3: Dynamic AGENTS.md Rule Compiler & Bridge Synchronization
# ============================================================================

def test_m1_m3_positive_dynamic_agents_md_parser_and_bridge_parity(tmp_path: Path):
    from tools.core import sync_agent_rules

    assert hasattr(sync_agent_rules, "extract_agents_md_sections"), "Missing extract_agents_md_sections"
    bundle = sync_agent_rules.extract_agents_md_sections(os.path.join(REPO_ROOT, "AGENTS.md"))
    assert bundle.invariant_count == 17
    assert "non-trivial implementation" in bundle.invariants_markdown
    assert ".agent/rules" not in bundle.invariants_markdown
    assert ".agents/rules" not in bundle.invariants_markdown

    # Dynamic extraction proof: altering AGENTS.md copy updates extracted invariants
    sample_agents = tmp_path / "AGENTS.md"
    sample_agents.write_text(
        "# AGENTS.md\n\n## 1. ALWAYS — Universal Invariants\n\n"
        "1. **Custom Rule Alpha:** Deterministic verification anchor.\n"
        "2. **Custom Rule Beta:** Zero static sleeps.\n\n---\n\n"
        "## 1.1 PRE-FLIGHT REASONING CHECKLIST (Mandatory Pre-Action Analysis)\n\n"
        "- **Pillar A:** Check alpha.\n\n---\n\n## 2. RECOMMENDED\n",
        encoding="utf-8",
    )
    custom_bundle = sync_agent_rules.extract_agents_md_sections(str(sample_agents))
    assert custom_bundle.invariant_count == 2
    assert "Custom Rule Alpha:" in custom_bundle.invariants_markdown
    assert "- **Custom Rule Beta:**" in custom_bundle.invariants_bullets
    assert "Pillar A" in custom_bundle.checklist_markdown

    # Boundary fallback when AGENTS.md is absent
    missing_bundle = sync_agent_rules.extract_agents_md_sections(str(tmp_path / "nonexistent.md"))
    assert missing_bundle.invariant_count >= 1

    # Protected stack rules must include security.mdc and repo sync check must pass
    assert ".cursor/rules/security.mdc" in sync_agent_rules.PROTECTED_STACK_RULES
    assert os.path.isfile(os.path.join(REPO_ROOT, ".cursor", "rules", "security.mdc"))
    assert sync_agent_rules.sync_all(check_only=True) == 0


# ============================================================================
# M4: Manual QA 12/13-Column Contract & @REQ-xxx Traceability
# ============================================================================

def test_m4_boundary_manual_qa_12_and_13_column_schema_and_rtm(tmp_path: Path):
    from tools.lint.manual_tc_linter import STANDARD_12_COLUMNS, STANDARD_13_COLUMNS, lint_test_case_file

    assert len(STANDARD_13_COLUMNS) == 13
    assert STANDARD_13_COLUMNS == ["TC ID", "REQ ID", *STANDARD_12_COLUMNS[1:]]

    missing_res = lint_test_case_file(str(tmp_path / "does_not_exist.md"))
    assert missing_res["passed"] is False
    assert missing_res["metrics"]["rtm_linked_cases"] == 0
    assert missing_res["metrics"]["vague_preconditions"] == 0

    manual_mdc = Path(REPO_ROOT, ".cursor", "rules", "manual-qa.mdc").read_text(encoding="utf-8")
    assert "TC ID | Module | Risk Level | Test Title | Pre-Condition" in manual_mdc
    assert "Risk/Priority" not in manual_mdc

    # 1. Valid canonical 12-column table with @REQ-101 in Tags
    tc_12 = tmp_path / "suite_12col.md"
    tc_12.write_text(
        "## Ambiguity & Assumptions Log\n| ID | Gap |\n|---|---|\n| A1 | Confirmed trim policy |\n\n"
        "## Test Cases\n"
        "| TC ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| TC_001 | Auth | High | Submit login with valid credentials | User registered | 1. Fill email<br>2. Click Login | Redirects to /dashboard with HTTP 200 | P0 | user@test.local | Yes | UI | @Smoke, @REQ-101 |\n",
        encoding="utf-8",
    )
    res_12 = lint_test_case_file(str(tc_12))
    assert res_12["passed"] is True
    assert res_12["column_counts"] == [12]
    assert res_12["metrics"].get("rtm_linked_cases", 0) == 1

    # 2. Valid optional 13-column table with dedicated REQ ID column
    tc_13 = tmp_path / "suite_13col.md"
    tc_13.write_text(
        "## Ambiguity & Assumptions Log\n| ID | Gap |\n|---|---|\n| A1 | Confirmed rate limit |\n\n"
        "## Test Cases\n"
        "| TC ID | REQ ID | Module | Risk Level | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Automatable | Auto Type | Tags |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| TC_002 | REQ-205 | Checkout | High | Reject whitespace-only coupon code | Cart has 1 item | 1. Enter spaces<br>2. Click Apply | Inline error 'Coupon required' shown | P1 | '   ' | Yes | UI | @Negative |\n",
        encoding="utf-8",
    )
    res_13 = lint_test_case_file(str(tc_13))
    assert res_13["passed"] is True
    assert res_13["column_counts"] == [13]
    assert res_13["metrics"].get("rtm_linked_cases", 0) == 1

    # 3. Negative: 10-column malformed table fails
    tc_bad = tmp_path / "suite_10col.md"
    tc_bad.write_text(
        "| TC ID | Module | Test Title | Pre-Condition | Test Steps | Expected Result | Priority | Test Data | Auto Type | Tags |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| TC_003 | Auth | Short table | Logged out | 1. Open | Login visible | P2 | N/A | UI | @Smoke |\n",
        encoding="utf-8",
    )
    res_bad = lint_test_case_file(str(tc_bad))
    assert res_bad["passed"] is False
    assert any(d["type"] == "COLUMN_COUNT_VIOLATION" for d in res_bad["defects"])


# ============================================================================
# M5 & M8: Clean POM Docs & Canonical Skill Code-Fence Linter
# ============================================================================

def test_m5_m8_negative_skill_code_fences_and_playwright_mdc(tmp_path: Path):
    from tools.lint import lint_ai_docs

    pw_mdc = Path(REPO_ROOT, ".cursor", "rules", "playwright.mdc").read_text(encoding="utf-8")
    assert "networkidle" not in pw_mdc

    assert hasattr(lint_ai_docs, "check_skill_code_fences"), "Missing check_skill_code_fences"
    repo_audit = lint_ai_docs.check_skill_code_fences(REPO_ROOT)
    assert repo_audit.scanned_blocks >= 20
    assert repo_audit.violations == [], f"Skill code-fence anti-patterns found: {repo_audit.violations}"

    # Empty repo without skills/ directory returns scanned_blocks == 0
    empty_audit = lint_ai_docs.check_skill_code_fences(str(tmp_path / "no_skills_dir"))
    assert empty_audit.scanned_blocks == 0
    assert empty_audit.violations == []

    # Negative & Boundary tests on synthetic skills directory
    fake_repo = tmp_path / "repo"
    skill_dir = fake_repo / "skills" / "01-web-automation" / "demo-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "# Demo Skill\n"
        "<!-- classification: illustrative -->\n"
        "```typescript\n"
        "await page.waitForTimeout(500);\n"
        "await page.waitForLoadState('networkidle');\n"
        "```\n"
        "<!-- classification: anti-pattern -->\n"
        "```typescript\n"
        "await page.waitForTimeout(9999);\n"
        "```\n\n"
        "Follow-up canonical section after anti-pattern:\n"
        "<!-- classification: illustrative -->\n"
        "```typescript\n"
        "await page.waitForTimeout(250);\n"
        "```\n",
        encoding="utf-8",
    )
    ref_dir = skill_dir / "references"
    ref_dir.mkdir(parents=True)
    (ref_dir / "sample_ref.md").write_text(
        "# Ref\n```javascript\nawait page.waitForNavigation({ waitUntil: 'networkidle' });\n```\n",
        encoding="utf-8",
    )
    neg_audit = lint_ai_docs.check_skill_code_fences(str(fake_repo))
    assert neg_audit.scanned_blocks == 4
    assert len(neg_audit.violations) == 4
    assert "[skills/01-web-automation/demo-skill/SKILL.md:4]" in neg_audit.violations[0]
    assert any("waitForTimeout" in v for v in neg_audit.violations)
    assert any("networkidle" in v for v in neg_audit.violations)
    assert any("sample_ref.md" in v for v in neg_audit.violations)
    with pytest.raises(Exception):
        neg_audit.scanned_blocks = 99  # type: ignore[misc]

    doc_errors, _ = lint_ai_docs.lint_docs(str(fake_repo))
    assert any("waitForTimeout" in err for err in doc_errors)


# ============================================================================
# M6: Gate 10 Performance SLA Mode-Split (HUB vs CLIENT)
# ============================================================================

def test_m6_gate_10_hub_vs_client_fail_closed(tmp_path: Path):
    from tools.core.gates.gate_10_perf_sla import gate_10_performance_sla

    perf_mdc = Path(REPO_ROOT, ".cursor", "rules", "perf.mdc").read_text(encoding="utf-8")
    assert "reports/perf/" in perf_mdc
    assert "Reports/perf/" not in perf_mdc

    # 1. CLIENT mode with empty reports/perf must FAIL CLOSED (no synthetic CPU fallback)
    client_empty = tmp_path / "client_empty"
    (client_empty / "reports" / "perf").mkdir(parents=True)
    assert gate_10_performance_sla(str(client_empty), mode="CLIENT") is False

    # 2. CLIENT mode with stale (>48h old) k6 report must FAIL CLOSED
    client_stale = tmp_path / "client_stale"
    stale_dir = client_stale / "reports" / "perf"
    stale_dir.mkdir(parents=True)
    stale_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 72 * 3600))
    (stale_dir / "k6_summary.json").write_text(
        json.dumps({
            "metrics": {
                "http_req_duration": {"values": {"p(95)": 120.0, "p(99)": 200.0}},
                "http_req_failed": {"values": {"rate": 0.0}},
            },
            "metadata": {"generated_at": stale_ts},
        }),
        encoding="utf-8",
    )
    assert gate_10_performance_sla(str(client_stale), mode="CLIENT") is False

    # 2b. CLIENT mode with explicit sla.require_fresh=False accepts stale report; require_fresh=True rejects
    (client_stale / "synapse.config.json").write_text(
        json.dumps({"performance": {"sla": {"require_fresh": False}}}),
        encoding="utf-8",
    )
    assert gate_10_performance_sla(str(client_stale), mode="CLIENT") is True

    (client_stale / "synapse.config.json").write_text(
        json.dumps({"performance": {"require_fresh": True}}),
        encoding="utf-8",
    )
    assert gate_10_performance_sla(str(client_stale), mode="CLIENT") is False

    # 2c. HUB mode with stale report and auto_benchmark_fallback=False still passes SLA check
    (client_stale / "synapse.config.json").write_text(
        json.dumps({"performance": {"auto_benchmark_fallback": False}}),
        encoding="utf-8",
    )
    assert gate_10_performance_sla(str(client_stale), mode="HUB") is True

    # 3. CLIENT mode with fresh compliant k6 report must PASS
    client_fresh = tmp_path / "client_fresh"
    fresh_dir = client_fresh / "reports" / "perf"
    fresh_dir.mkdir(parents=True)
    fresh_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (fresh_dir / "k6_summary.json").write_text(
        json.dumps({
            "metrics": {
                "http_req_duration": {"values": {"p(95)": 110.0, "p(99)": 190.0}},
                "http_req_failed": {"values": {"rate": 0.001}},
            },
            "metadata": {"generated_at": fresh_ts},
        }),
        encoding="utf-8",
    )
    assert gate_10_performance_sla(str(client_fresh), mode="CLIENT") is True

    # 4. HUB mode with empty reports/perf skips cleanly without synthetic JTL masquerade
    hub_empty = tmp_path / "hub_empty"
    (hub_empty / "reports" / "perf").mkdir(parents=True)
    assert gate_10_performance_sla(str(hub_empty), mode="HUB") is True
    assert list((hub_empty / "reports" / "perf").glob("*.jtl")) == []


# ============================================================================
# M7: Fail-Closed PreToolUse Hook & Context-Aware Safety Firewall
# ============================================================================

def test_m7_cli_resilience_security_hook_and_firewall():
    from tools.security import safety_firewall

    # 1. Verify reversible_sandbox import fixed
    assert safety_firewall.reversible_sandbox is not None

    # 2. Safety Firewall: bulk destructive actions are ALWAYS dangerous even on localhost/AUTO_
    blk_danger, _ = safety_firewall.is_action_dangerous(
        "click", text="Delete All Records", selector="#btn-purge", target_env="http://localhost:3000"
    )
    assert blk_danger is True
    drop_danger, _ = safety_firewall.is_action_dangerous(
        "drop_database", text="AUTO_DB", target_env="localhost"
    )
    assert drop_danger is True

    # 3. Safety Firewall: single-entity delete/pay on AUTO_ test data or localhost/staging is allowed
    auto_del_danger, _ = safety_firewall.is_action_dangerous(
        "deleteRecord", text="AUTO_USER_991", selector="", target_env=""
    )
    assert auto_del_danger is False
    staging_pay_danger, _ = safety_firewall.is_action_dangerous(
        "click", text="Place Order", selector="[data-testid='submit-order']", target_env="https://staging.synapse.local"
    )
    assert staging_pay_danger is False
    benign_empty_sel, _ = safety_firewall.is_action_dangerous(
        "click", text="View Details", selector="", target_env="http://localhost:8080"
    )
    assert benign_empty_sel is False

    # 4. Safety Firewall: single-entity delete/pay on production or non-allowlisted external host is BLOCKED
    prod_pay_danger, _ = safety_firewall.is_action_dangerous(
        "click", text="Place Order", selector="#pay", target_env="https://portal.prod.example.com"
    )
    assert prod_pay_danger is True
    ext_del_danger, _ = safety_firewall.is_action_dangerous(
        "click", text="Delete", selector="#btn-delete", target_env="https://bank.example.com"
    )
    assert ext_del_danger is True
    ext_auto_danger, _ = safety_firewall.is_action_dangerous(
        "deleteRecord", text="AUTO_USER_991", selector="", target_env="https://bank.example.com"
    )
    assert ext_auto_danger is True
    exec_pay_danger, _ = safety_firewall.is_action_dangerous(
        "execute_payment", text="Submit", selector="", target_env="https://bank.example.com"
    )
    assert exec_pay_danger is True
    unscoped_del_danger, _ = safety_firewall.is_action_dangerous(
        "click", text="Delete", selector="#btn-delete"
    )
    assert unscoped_del_danger is True

    # 5. PreToolUse Hook (direct module + subprocess): Fail-Closed on malformed JSON & dangerous stdin command
    hooks_dir = os.path.join(REPO_ROOT, "ai-agents", "hooks")
    if hooks_dir not in sys.path:
        sys.path.append(hooks_dir)
    import pre_tool_use as hook_mod
    hook_script = hook_mod.__file__
    from io import StringIO
    buf = StringIO()
    old_stdout = sys.stdout
    try:
        sys.stdout = buf
        rc_deny = hook_mod._emit_deny("Lỗi bảo mật", tool_name="Bash", command="rm")  # synapse-ignore: VIETNAMESE
    finally:
        sys.stdout = old_stdout
    assert rc_deny == 1
    assert "Lỗi bảo mật" in buf.getvalue()  # synapse-ignore: VIETNAMESE

    env_malformed = os.environ.copy()
    env_malformed["TOOL_INPUT"] = "{malformed_json_payload"
    proc_bad_env = subprocess.run(
        [sys.executable, hook_script],
        input="",
        text=True,
        capture_output=True,
        env=env_malformed,
        check=False,
    )
    assert proc_bad_env.returncode == 1
    assert json.loads(proc_bad_env.stdout)["permissionDecision"] == "deny"

    env_clean = os.environ.copy()
    env_clean.pop("TOOL_INPUT", None)
    proc_bad_stdin = subprocess.run(
        [sys.executable, hook_script],
        input="{broken_stdin_json",
        text=True,
        capture_output=True,
        env=env_clean,
        check=False,
    )
    assert proc_bad_stdin.returncode == 1
    assert json.loads(proc_bad_stdin.stdout)["permissionDecision"] == "deny"

    proc_dangerous_stdin = subprocess.run(
        [sys.executable, hook_script],
        input=json.dumps({"command": "rm -rf /"}),
        text=True,
        capture_output=True,
        env=env_clean,
        check=False,
    )
    assert proc_dangerous_stdin.returncode == 1
    assert json.loads(proc_dangerous_stdin.stdout)["permissionDecision"] == "deny"

    # CLI argument takes precedence over TOOL_INPUT
    proc_cli_precedence = subprocess.run(
        [sys.executable, hook_script, "echo ok"],
        input="",
        text=True,
        capture_output=True,
        env=env_malformed,
        check=False,
    )
    assert proc_cli_precedence.returncode == 0
    assert json.loads(proc_cli_precedence.stdout)["permissionDecision"] == "allow"

    # Empty stdin + unset TOOL_INPUT (benign non-Bash tool call) -> allow
    proc_benign = subprocess.run(
        [sys.executable, hook_script],
        input="",
        text=True,
        capture_output=True,
        env=env_clean,
        check=False,
    )
    assert proc_benign.returncode == 0
    assert json.loads(proc_benign.stdout)["permissionDecision"] == "allow"


# ============================================================================
# M9: English-Only Rules Across standards/ & testing/ (Invariant 16)
# ============================================================================

def test_m9_invariant_16_covers_standards_and_testing(tmp_path: Path):
    from tools.lint.invariant_checker import check_rule_16_english_codebase

    # Live repository must have 0 violations across AGENTS.md, standards/, testing/, .cursor/rules/
    live_violations = check_rule_16_english_codebase(REPO_ROOT)
    assert live_violations == [], f"Rule 16 violations in repo: {live_violations}"

    # Synthetic negative check: Vietnamese text inside testing/ and standards/ must be flagged
    fake_root = tmp_path / "fake_repo"
    (fake_root / "testing" / "performance").mkdir(parents=True)
    (fake_root / "standards" / "qa-process").mkdir(parents=True)
    (fake_root / "testing" / "performance" / "performance_testing_rules.md").write_text(
        "# Perf Rule\nThiết kế kịch bản kiểm thử tải\n",  # synapse-ignore: VIETNAMESE
        encoding="utf-8",
    )
    (fake_root / "standards" / "qa-process" / "sample_rule.md").write_text(
        "# Standard\nKiểm tra dữ liệu đầu vào\n",  # synapse-ignore: VIETNAMESE
        encoding="utf-8",
    )
    # Whitelisted .vi.md and non-.md files must NOT be flagged by Rule 16
    (fake_root / "standards" / "qa-process" / "guide.vi.md").write_text(
        "# Tài liệu tiếng Việt hợp lệ\n",  # synapse-ignore: VIETNAMESE
        encoding="utf-8",
    )
    (fake_root / "standards" / "qa-process" / "config.json").write_text(
        "{\"note\": \"Tiếng Việt trong JSON\"}\n",  # synapse-ignore: VIETNAMESE
        encoding="utf-8",
    )
    synth_violations = check_rule_16_english_codebase(str(fake_root))
    flagged_files = {v["file"].replace("\\", "/") for v in synth_violations}
    assert flagged_files == {
        "testing/performance/performance_testing_rules.md",
        "standards/qa-process/sample_rule.md",
    }


# ============================================================================
# M10 - M12: Skill Relocation & Router / Manifest Parity
# ============================================================================

def test_m10_m12_scoreboard_relocation_and_trigger_hygiene():
    from tools.core.rules_router import TASK_TYPE_CONFIGS
    from tools.lint.invariant_checker import check_rule_7_skills

    old_path = os.path.join(REPO_ROOT, "skills", "04-performance-and-load", "lean-impact-scoreboard", "SKILL.md")
    new_path = os.path.join(REPO_ROOT, "skills", "08-code-quality", "lean-impact-scoreboard", "SKILL.md")
    assert not os.path.exists(old_path)
    assert os.path.isfile(new_path)

    idx_data = json.loads(Path(REPO_ROOT, "skills_index.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in idx_data["skills"]}

    assert by_id["lean-impact-scoreboard"]["domain"] == "08-code-quality"
    assert "perf" not in by_id["lean-impact-scoreboard"]["stack_triggers"]
    assert "security" not in by_id["wcag-audit-patterns"]["stack_triggers"]
    assert "rag" not in by_id["auth-session-and-cookie-manager"]["stack_triggers"]
    assert "rag" not in by_id["gherkin-to-suite"]["stack_triggers"]

    assert "lean-impact-scoreboard" not in TASK_TYPE_CONFIGS["perf"]["secondary_skills"]
    assert "wcag-audit-patterns" not in TASK_TYPE_CONFIGS["security"]["secondary_skills"]
    assert check_rule_7_skills(REPO_ROOT) == []


# ============================================================================
# M13 - M14: Bilingual # language: vi Gherkin Compiler & ADR-0021
# ============================================================================

def test_m13_m14_vietnamese_gherkin_compiler_and_adr():
    from tools.transpiler import gherkin_suite
    from tools.transpiler.universal_ir import ActionType, AssertionType

    assert hasattr(gherkin_suite, "resolve_gherkin_locale"), "Missing resolve_gherkin_locale"

    vi_feature_text = (
        "# language: vi\n"
        "@ThanhToan @P0\n"
        "Tính năng: Thanh toán đơn hàng trực tuyến\n"  # synapse-ignore: VIETNAMESE
        "  Bối cảnh:\n"  # synapse-ignore: VIETNAMESE
        "    Cho biết người dùng đã đăng nhập thành công\n\n"  # synapse-ignore: VIETNAMESE
        "  @Khung\n"
        "  Khung kịch bản: Áp dụng mã giảm giá khi thanh toán\n"  # synapse-ignore: VIETNAMESE
        "    Khi người dùng truy cập \"https://staging.shop.local/checkout\"\n"  # synapse-ignore: VIETNAMESE
        "    Và nhập \"<ma_voucher>\" vào ô \"Mã giảm giá\"\n"  # synapse-ignore: VIETNAMESE
        "    Và nhấn \"Áp dụng\"\n"  # synapse-ignore: VIETNAMESE
        "    Thì hệ thống hiển thị \"<thong_bao>\"\n"  # synapse-ignore: VIETNAMESE
        "    Và màn hình hiển thị bảng tổng kết\n\n"  # synapse-ignore: VIETNAMESE
        "    Dữ liệu:\n"  # synapse-ignore: VIETNAMESE
        "      | ma_voucher | thong_bao             |\n"
        "      | GIAM10     | Giảm giá thành công   |\n"  # synapse-ignore: VIETNAMESE
        "      | HET_HAN    | Mã giảm giá không hợp lệ |\n"  # synapse-ignore: VIETNAMESE
    )
    parser = gherkin_suite.GherkinParser()
    feat = parser.parse(vi_feature_text, filename="checkout_vi.feature")
    assert parser.errors == [], f"Unexpected Vietnamese Gherkin parse errors: {parser.errors}"
    assert feat.name == "Thanh toán đơn hàng trực tuyến"  # synapse-ignore: VIETNAMESE
    assert len(feat.background) == 1
    assert len(feat.scenarios) == 1
    assert feat.scenarios[0].is_outline is True

    expand_errors = []
    cases = gherkin_suite.expand_feature(feat, expand_errors)
    assert expand_errors == []
    assert len(cases) == 2

    ir_case = gherkin_suite.build_test_case_ir(cases[0])
    actions = [s.action for s in ir_case.steps]
    assert actions == [
        ActionType.CUSTOM_CALL,
        ActionType.GOTO,
        ActionType.FILL,
        ActionType.CLICK,
        ActionType.ASSERT,
        ActionType.ASSERT,
    ]
    assert ir_case.steps[3].target == "Áp dụng"  # synapse-ignore: VIETNAMESE
    assert ir_case.steps[4].assertion_type == AssertionType.CONTAINS_TEXT
    assert ir_case.steps[5].assertion_type == AssertionType.VISIBLE

    # Boundary & Negative check: orphan 'Và' before Given/When/Then records error cleanly
    bad_parser = gherkin_suite.GherkinParser()
    bad_parser.parse(
        "# language: vi\nTính năng: Lỗi\n  Kịch bản: Thiếu bước gốc\n    Và nhấn \"Lưu\"\n",  # synapse-ignore: VIETNAMESE
        filename="bad_vi.feature",
    )
    assert len(bad_parser.errors) == 1

    # Verify M14 deliverables exist and link canonical reversible_sandbox path
    assert os.path.isfile(os.path.join(REPO_ROOT, "docs", "adr", "ADR-0021-hub-rules-skills-harmonization.md"))
    api_rules = Path(REPO_ROOT, "testing", "api-contracts", "api_testing_rules.md").read_text(encoding="utf-8")
    assert "tools/heal/reversible_sandbox.py" in api_rules


def test_polish_analyze_gate_toggles_setup_config_and_jtl_timestamp(tmp_path, monkeypatch, capsys):
    from tools.core import analyze_project, setup_project
    from tools.perf import jtl_analyzer

    # 1. ensure_synapse_config sets gate_10_performance_sla=False for non-perf profiles and keeps True for perf
    pw_dir = tmp_path / "pw_proj"
    pw_dir.mkdir()
    assert setup_project.ensure_synapse_config(str(pw_dir), profile="playwright") is True
    pw_cfg = json.loads((pw_dir / "synapse.config.json").read_text(encoding="utf-8"))
    assert pw_cfg["quality_gates"]["gates"]["gate_10_performance_sla"] is False

    perf_dir = tmp_path / "perf_proj"
    perf_dir.mkdir()
    assert setup_project.ensure_synapse_config(str(perf_dir), profile="perf-and-load") is True
    perf_cfg = json.loads((perf_dir / "synapse.config.json").read_text(encoding="utf-8"))
    assert perf_cfg["quality_gates"]["gates"].get("gate_10_performance_sla", True) is True

    # 2. analyze_project honors skipped gates in TARGET mode and fails closed in HUB mode (Invariant 11)
    proj = tmp_path / "hub_sim"
    (proj / "tests").mkdir(parents=True)
    monkeypatch.setattr(analyze_project.check_env.DiagnosticRunner, "run_all", lambda self: 0)
    monkeypatch.setattr(
        analyze_project.repo_map,
        "build_repo_map",
        lambda *a, **kw: {"classes_count": 0, "methods_count": 0, "source_lines": 0, "output_file": "repo_map.txt"},
    )
    monkeypatch.setattr(analyze_project.infer_linter, "run_infer_linter", lambda *a, **kw: 0)
    monkeypatch.setattr(analyze_project.trace_data_flow, "run_data_flow_tracer", lambda *a, **kw: 0)
    vmod = analyze_project.verify_all
    monkeypatch.setattr(vmod, "verify_engine_preflight", lambda *a, **kw: True)
    called_gates = []
    for gname in (
        "gate_1_bom_check", "gate_2_path_portability", "gate_3_clean_pom",
        "gate_4_ai_docs_lint", "gate_5_cleanup_blacklist", "gate_6_credential_security",
        "gate_7_infer_linter", "gate_8_micro_mutator", "gate_9_skill_collision",
        "gate_10_performance_sla",
    ):
        monkeypatch.setattr(vmod, gname, lambda *a, _g=gname, **kw: (called_gates.append(_g) or True))

    # Empty config executes gates normally instead of skipping non-False entries
    monkeypatch.setattr(vmod, "detect_repo_mode", lambda *a, **kw: "TARGET")
    assert analyze_project.run_full_analysis(str(proj)) == 0
    assert "gate_1_bom_check" in called_gates
    assert "gate_10_performance_sla" in called_gates

    # Disabled Gate 10 in TARGET skips Gate 10 with [GATE 10] banner; in HUB fails closed (Invariant 11)
    (proj / "synapse.config.json").write_text(
        json.dumps({"quality_gates": {"gates": {"gate_10_performance_sla": False}}}),
        encoding="utf-8",
    )
    called_gates.clear()
    capsys.readouterr()
    assert analyze_project.run_full_analysis(str(proj)) == 0
    out_target = capsys.readouterr().out
    assert "[GATE 10] Disabled via synapse.config.json (SKIPPED)" in out_target
    assert "gate_1_bom_check" in called_gates
    assert "gate_10_performance_sla" not in called_gates

    monkeypatch.setattr(vmod, "detect_repo_mode", lambda *a, **kw: "HUB")
    assert analyze_project.run_full_analysis(str(proj)) == 1
    out_hub = capsys.readouterr().out
    assert "[GATE 10] Disabled via synapse.config.json (FAIL:" in out_hub

    # 3. jtl_analyzer.parse_jtl_timestamp handles epoch ms, ISO Z, formatted dates, and raises on garbage
    assert jtl_analyzer.parse_jtl_timestamp("1700000000") == 1700000000000
    assert jtl_analyzer.parse_jtl_timestamp("2026-11-25T10:00:00Z") > 0
    assert jtl_analyzer.parse_jtl_timestamp("2026/11/25 10:00:00") > 0
    with pytest.raises(ValueError, match="Unrecognized JTL timestamp format"):
        jtl_analyzer.parse_jtl_timestamp("not-a-timestamp")
