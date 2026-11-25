# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-Scenario Red-First Verification Suite for P0-P2 AI/RAG/Agent Fixes."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT_DIR / "tools"
for _p in (str(ROOT_DIR), str(TOOLS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.ai.cove_verifier import ChainOfVerificationEngine
from tools.lint.ai_eval_sentinel import (
    audit_agent_transcript,
    compute_context_metrics,
    compute_faithfulness,
    evaluate_rag_triplet,
)
from tools.orchestration.browsergym_eval import BrowserGymEvaluator, main as browsergym_main
from tools.orchestration.synapse_qa_bench import SynapseQABench
from tools.reasoning.prover_verifier_games import ProverArgument, VerifierAgent
from tools.reasoning.semantic_entropy import SemanticEntropyEngine


# ==============================================================================
# P0: BrowserGym PageClass Certification & AI Eval Sentinel
# ==============================================================================

def test_p0_browsergym_ignores_comments_and_copyright_urls(tmp_path: Path):
    """Positive & Boundary: comments mentioning Thread.sleep and https:// URLs must not fail."""
    page_file = tmp_path / "CleanBasePage.ts"
    page_file.write_text(
        "\n".join([
            "// SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>",
            "export class CleanBasePage {",
            "  /**",
            "   * Smart wait without static Thread.sleep or time.sleep(5).",
            "   * Avoids //div[1] brittle paths.",
            "   */",
            "  async waitReady() {",
            "    await this.page.getByRole('button', { name: 'Save' }).waitFor({ state: 'visible' });",
            "  }",
            "}",
        ]),
        encoding="utf-8",
    )
    gym = BrowserGymEvaluator(repo_root=str(tmp_path))
    res = gym.evaluate_pageclass(str(page_file))
    assert res["status"] == "PASS"
    assert res["certification"] == "APPROVED"
    assert res["raw_xpath_hits"] == 0
    assert res["static_sleep_hits"] == 0
    assert res["clean_pom_score"] == 1.0


def test_p0_browsergym_detects_python_aom_and_real_xpath_sleep(tmp_path: Path):
    """Positive & Negative: Python snake_case AOM counted; real sleep & XPath still rejected."""
    py_page = tmp_path / "PyLoginPage.py"
    py_page.write_text(
        "\n".join([
            "# https://github.com/TeeVee98/Synapse-Hub",
            "class PyLoginPage:",
            "    def __init__(self, page):",
            "        self.email = page.get_by_label('Email')",
            "        self.btn = page.get_by_role('button', { 'name': 'Sign In' })",
            "        self.banner = page.get_by_test_id('welcome')",
        ]),
        encoding="utf-8",
    )
    gym = BrowserGymEvaluator(repo_root=str(tmp_path))
    res_good = gym.evaluate_pageclass(str(py_page))
    assert res_good["status"] == "PASS"
    assert res_good["aom_selector_hits"] >= 3
    assert res_good["raw_xpath_hits"] == 0

    bad_page = tmp_path / "BadRealPage.ts"
    bad_page.write_text(
        "\n".join([
            "export class BadRealPage {",
            "  async bad() {",
            "    await this.page.locator('//div[@id=\"app\"]/button').click();",
            "    time.sleep(2);",
            "  }",
            "}",
        ]),
        encoding="utf-8",
    )
    res_bad = gym.evaluate_pageclass(str(bad_page))
    assert res_bad["status"] == "FAIL"
    assert res_bad["certification"] == "REJECTED"
    assert res_bad["raw_xpath_hits"] >= 1
    assert res_bad["static_sleep_hits"] >= 1


def test_p0_ai_eval_sentinel_catches_unit_attached_numbers_and_returns_context_metrics():
    """Negative, Positive & Boundary: 1500ms != 200ms caught; empty/whitespace boundaries & context metrics."""
    # Empty answer boundary
    empty_faith = compute_faithfulness("", "Some context.")
    assert empty_faith["score"] == 1.0
    assert empty_faith["is_faithful"] is True
    assert empty_faith["total_claims"] == 0

    context = "Headless Latency Ceiling: Average action step latency must remain below 200ms."
    hallucinated = "Average headless action step latency can reach 1500ms."
    res_hall = compute_faithfulness(hallucinated, context)
    assert res_hall["is_faithful"] is False
    assert res_hall["score"] == 0.0
    assert len(res_hall["hallucinated_claims"]) == 1

    triplet = evaluate_rag_triplet(
        query="What is the headless step latency ceiling?",
        context=context,
        answer="Average headless action step latency must remain below 200ms.",
    )
    assert "context_precision" in triplet
    assert "context_recall" in triplet
    assert 0.0 < triplet["context_precision"] <= 1.0
    assert triplet["context_recall"] >= 0.8

    # Boundary tests for compute_context_metrics
    assert compute_context_metrics("", "   ", "") == (0.0, 0.0)
    assert compute_context_metrics("", "Single chunk without punctuation", "") == (0.0, 1.0)
    assert compute_context_metrics("ab", "ab", "ab") == (1.0, 1.0)
    assert compute_context_metrics("latency", "", "latency") == (0.0, 0.0)
    assert compute_context_metrics("latency", "latency 200ms", "latency") == (1.0, 1.0)


def test_p0_ai_eval_sentinel_transcript_supports_tool_calls_and_vietnamese(tmp_path: Path):
    """Positive, Negative & Boundary: Antigravity transcript events, orphan planner responses, and empty content."""
    good_log = tmp_path / "good_transcript.jsonl"
    events_good = [
        {"step_index": 0, "type": "PLANNER_RESPONSE", "content": "Orphan response before user input"},
        {"step_index": 1, "type": "USER_INPUT", "content": "Chạy kiểm tra hệ thống"},
        {
            "step_index": 2,
            "type": "PLANNER_RESPONSE",
            "content": "",
            "tool_calls": [
                {"name": "read_file", "args": {"Path": "/repo/custom_vault.py"}},
                {"name": "read_file", "args": {"Path": "/repo/SKILL.md"}},
            ],
        },
        {"step_index": 3, "type": "GENERIC", "content": "Showing lines 1-61 of 61\n\"web-agent-gym-benchmarking\""},
        {
            "step_index": 4,
            "type": "PLANNER_RESPONSE",
            "content": "Đã đọc `custom_vault.py` và `SKILL.md` với 61 dòng.",
        },
    ]
    good_log.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events_good), encoding="utf-8")
    res_good = audit_agent_transcript(str(good_log))
    assert res_good["total_conversation_turns"] == 1
    assert res_good["overall_faithfulness_rate"] >= 80.0
    assert res_good["is_trustworthy"] is True

    bad_log = tmp_path / "bad_transcript.jsonl"
    events_bad = [
        {"step_index": 0, "type": "USER_INPUT", "content": "Run benchmark"},
        {"step_index": 1, "type": "GENERIC", "content": "avg_latency_ms: 128.5, passed_tasks: 3"},
        {
            "step_index": 2,
            "type": "PLANNER_RESPONSE",
            "content": "Hệ thống đạt 9999ms và có 42 lỗi nghiêm trọng trong database_oracle_v9.",
        },
    ]
    bad_log.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events_bad), encoding="utf-8")
    res_bad = audit_agent_transcript(str(bad_log))
    assert res_bad["is_trustworthy"] is False
    assert res_bad["overall_faithfulness_rate"] < 80.0


# ==============================================================================
# P1: CoVe Verifier & Synapse QA Bench AST Validation
# ==============================================================================

def test_p1_cove_rejects_docstring_only_test_and_static_data_collision(tmp_path: Path):
    """Negative & Positive: docstring/call-only test fails TRUTH_ANCHOR; static ID fails DATA_COLLISION."""
    fake_test = tmp_path / "test_fake.py"
    fake_test.write_text(
        "\n".join([
            "def test_no_assertions():",
            '    """Looks real but asserts nothing."""',
            "    create_customer(email='fixed@corp.com', code='CUST_001')",
        ]),
        encoding="utf-8",
    )
    engine = ChainOfVerificationEngine()
    rep_fake = engine.verify(str(fake_test))
    assert rep_fake["status"] == "DISCREPANCY_DETECTED"
    failed_cats = {d["category"] for d in rep_fake["discrepancies"]}
    assert "TRUTH_ANCHOR" in failed_cats
    assert "DATA_COLLISION" in failed_cats

    expect_test = tmp_path / "test_expect.py"
    expect_test.write_text(
        "\n".join([
            "def test_playwright_expect(page):",
            "    code = unique_code('CUST_')",
            "    create_customer(code=code)",
            "    expect(page.get_by_text(code)).to_be_visible()",
        ]),
        encoding="utf-8",
    )
    rep_ok = engine.verify(str(expect_test))
    assert rep_ok["status"] == "PASS"


def test_p1_synapse_qa_bench_real_resolver_and_ast_flag_validation():
    """Positive & Negative: default resolver works cleanly and phantom CLI flags fail AST check."""
    bench = SynapseQABench()
    res_ok = bench.run_benchmark()
    assert res_ok["passed"] is True
    assert res_ok["overall_score"] >= 85.0
    assert res_ok["arg_validity_accuracy"] == 100.0

    # Negative case: phantom flag '--nonexistent-flag-xyz' and bogus intent
    bad_cases = [
        {
            "id": "TC-BAD-01",
            "intent": "Run all 10 Definition-of-Done Quality Gates before merging git commit",
            "expected_tool": "verify_all.py",
            "valid_args": ["--nonexistent-flag-xyz", "123"],
            "irrelevant_tools": ["jtl_analyzer.py"],
        },
        {
            "id": "TC-BAD-02",
            "intent": "Transpile test cases bidirectionally between Java, TypeScript, and Groovy",
            "expected_tool": "omni_transpiler.py",
            "valid_args": ["--from", "ts", "--to", "groovy"],
            "irrelevant_tools": ["flaky_detector.py"],
        },
    ]
    bad_bench = SynapseQABench(cases=bad_cases)
    res_bad = bad_bench.run_benchmark()
    assert res_bad["arg_validity_accuracy"] == 0.0
    assert all(d["args_valid"] is False for d in res_bad["details"])


# ==============================================================================
# P2: Gate Flags, Epistemic Noise, & Live Browser Mode
# ==============================================================================

def test_p2_prover_verifier_gate_enforces_user_proposal():
    """CLI: --gate combined with --proposal must evaluate the proposal and fail on REFUTED."""
    cmd = [
        sys.executable,
        str(TOOLS_DIR / "reasoning" / "prover_verifier_games.py"),
        "--proposal",
        "Add time.sleep(5) and except Exception: pass to hide test failures",
        "--rounds",
        "2",
        "--judge-mode",
        "strict",
        "--gate",
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["status"] == "REFUTED"
    assert payload["winner"] == "verifier"


def test_p2_prover_verifier_ignores_prose_in_context_contradiction():
    """Boundary: prose words like Foundational/TypeScript/AGENTS/Rule must not trigger missing symbols."""
    verifier = VerifierAgent()
    dummy_arg = ProverArgument(claim="Evidence: AGENTS.md Rule 1.3", citations=["AGENTS.md Rule 1.3"], confidence=0.9)
    counter = verifier.generate_attack(
        round_num=1,
        proposal_text="Foundational TypeScript suites following AGENTS Rule guidelines with mutex lock retry empty check.",
        context_text="class BasePage: pass  # short context > 10 chars",
        prover_argument=dummy_arg,
    )
    assert not any("context contradiction" in c.lower() for c in counter.counter_examples)


def test_p2_semantic_entropy_gate_and_epistemic_target_cleanup():
    """CLI & Boundary: --gate with --prompt enforces threshold and filters interrogatives."""
    eng = SemanticEntropyEngine()
    plan = eng._generate_epistemic_search_plan("What is the return type of BasePage.clickSafe?")
    assert "What" not in plan[1]["target"]
    assert "BasePage" in plan[1]["target"]

    cmd_high = [
        sys.executable,
        str(TOOLS_DIR / "reasoning" / "semantic_entropy.py"),
        "--prompt",
        "What is the return type of BasePage.clickSafe?",
        "--samples",
        "4",
        "--threshold",
        "0.50",
        "--epistemic-search",
        "--gate",
        "--json",
    ]
    proc_high = subprocess.run(cmd_high, capture_output=True, text=True)
    assert proc_high.returncode == 1
    parsed_high = json.loads(proc_high.stdout)
    assert parsed_high["epistemic_search_required"] is True
    step2_target = parsed_high["epistemic_search_plan"][1]["target"]
    assert "What" not in step2_target
    assert "BasePage" in step2_target

    cmd_low = [
        sys.executable,
        str(TOOLS_DIR / "reasoning" / "semantic_entropy.py"),
        "--prompt",
        "What is the consensus default timeout in BasePage?",
        "--samples",
        "4",
        "--threshold",
        "0.50",
        "--gate",
        "--json",
    ]
    proc_low = subprocess.run(cmd_low, capture_output=True, text=True)
    assert proc_low.returncode == 0
    parsed_low = json.loads(proc_low.stdout)
    assert parsed_low["normalized_entropy"] == 0.0


def test_p2_browsergym_live_browser_flag_fails_closed_without_fake_pass(monkeypatch, capsys):
    """CLI & Negative: --live-browser fails closed with exact zero telemetry; simulated default passes."""
    gym = BrowserGymEvaluator()
    sim_res = gym.run_suite(tasks=["ecommerce_order"])
    assert sim_res["execution_mode"] == "simulated"
    assert sim_res["headless"] is True
    assert sim_res["status"] == "PASS"

    # Simulated CLI default (without --live-browser) via in-process main() so mutants are caught
    monkeypatch.setattr(sys, "argv", ["browsergym_eval.py", "run-suite", "--tasks", "ecommerce_order", "--headless"])
    with pytest.raises(SystemExit) as exc_sim:
        browsergym_main()
    assert exc_sim.value.code == 0
    sim_cli = json.loads(capsys.readouterr().out)
    assert sim_cli["execution_mode"] == "simulated"
    assert sim_cli["status"] == "PASS"

    # Empty tasks boundary
    empty_res = gym.run_suite(tasks=["   "])
    assert empty_res["total_tasks"] == 0
    assert empty_res["avg_latency_ms"] == 0.0

    # Live browser mode via direct API + CLI main()
    live_res = gym.run_suite(tasks=["crm_lead_create"], live_browser=True)
    assert live_res["execution_mode"] == "live_browser"
    assert live_res["headless"] is True

    monkeypatch.setattr(
        sys,
        "argv",
        ["browsergym_eval.py", "run-suite", "--tasks", "crm_lead_create", "--headless", "--live-browser"],
    )
    with pytest.raises(SystemExit) as exc_live:
        browsergym_main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["execution_mode"] == "live_browser"
    if payload["status"] == "FAIL":
        assert exc_live.value.code == 1
        assert payload["certification"] == "REJECTED"
        assert payload["total_tasks"] == 0
        assert payload["passed_tasks"] == 0
        assert payload["action_success_rate"] == 0.0
        assert payload["avg_latency_ms"] == 0.0
        assert payload["database_assertion_pass_rate"] == 0.0
        assert payload["elapsed_seconds"] >= 0.0
        assert payload["tasks"] == []
        assert "error" in payload
