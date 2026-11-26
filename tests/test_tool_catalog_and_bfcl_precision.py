#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""4-Scenario Pytest Suite: Tool Catalog AST Enrichment, MetaToolEngine & BFCL Precision (M4-M5).

Covers:
  1. Positive: Zero false destructive tags on *skill*.py, real AST argparse flags, sanitized docstrings,
               MetaToolEngine >= 166 tools + .agent/skills + bilingual search, SynapseQABench 100% score & TC-BENCH-07.
  2. Negative: Wrong selected_tool fails args_valid honestly, bare numeric query '11' does not hijack domain prefix,
               out-of-domain queries abstain ('').
  3. Boundary: Empty/unicode queries and malformed Python files during AST risk/flag inference never crash.
  4. CLI / Resilience: `synapse_qa_bench.py --json` exits 0 with 100.0% overall score; `meta_tool_engine.py search` exits 0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# ==============================================================================
# 1. M4 — TOOL CATALOG & META-TOOL ENGINE (POSITIVE, NEGATIVE, BOUNDARY, CLI)
# ==============================================================================


def test_positive_catalog_zero_false_destructive_and_ast_enrichment():
    """Positive (TC-04): Zero *skill*.py false destructive tags, AST argparse flags extracted, banner docstrings sanitized."""
    from tools.report.generate_tool_catalog import (
        CatalogRiskAuditDTO,
        build_catalog,
        infer_tool_risk_and_cli_metadata,
    )

    catalog = build_catalog()
    tools_list = catalog["tools"]
    assert len(tools_list) >= 160

    # Zero *skill*.py tools may ever be falsely tagged 'destructive' due to 's-kill' substring
    skill_tools = [t for t in tools_list if "skill" in os.path.basename(t["file"]).lower()]
    assert len(skill_tools) >= 4
    false_destructive = [t["file"] for t in skill_tools if t["risk_level"] == "destructive"]
    assert false_destructive == [], f"False destructive skill tools: {false_destructive}"

    # Separator banner docstring in check_env.py must be sanitized (never '======...')
    check_env_entry = next(t for t in tools_list if t["file"].endswith("check_env.py"))
    assert not check_env_entry["description"].startswith("===")
    assert len(check_env_entry["description"]) >= 10

    # Subdirectory domain category inference replaces generic 'Auxiliary Utilities'
    assert check_env_entry["category"] != "Auxiliary Utilities"

    # Real AST argparse flags extracted for non-registry tools (not placeholder 'CLI options')
    ast_typed = [
        t for t in tools_list
        if any(isinstance(inp, str) and inp.startswith("-") for inp in t.get("inputs", []))
    ]
    assert len(ast_typed) >= 90

    # Direct helper contract check
    meta = infer_tool_risk_and_cli_metadata(
        os.path.join(REPO_ROOT, "tools", "core", "skill_vault.py"),
        "skill_vault.py",
    )
    assert meta["risk_level"] != "destructive"
    assert isinstance(meta["inputs"], list)
    assert isinstance(CatalogRiskAuditDTO(len(tools_list), 0, len(ast_typed), True), CatalogRiskAuditDTO)


def test_positive_meta_tool_engine_166_tools_agent_skills_and_bilingual():
    """Positive (TC-04): MetaToolEngine exposes >= 166 tools, .agent/skills, and bilingual Vietnamese search."""
    from tools.runtime.meta_tool_engine import MetaToolEngine

    engine = MetaToolEngine(REPO_ROOT)
    assert len(engine._tools_catalog) >= 166

    # .agent/skills/* indexed and searchable
    skill_ids = {s.get("id") for s in engine._skills_catalog}
    assert "solo" in skill_ids
    assert "super-plan" in skill_ids

    plan_hits = engine.search_tools("super-plan")
    assert any(h.get("kind") == "skill" and h.get("id") == "super-plan" for h in plan_hits)

    # Catalog-only tool (beyond the 81 tools_schema entries) is now discoverable
    transpiler_hits = engine.search_tools("omni_transpiler")
    assert any(h.get("kind") == "tool" and "omni_transpiler" in str(h.get("name", "")) for h in transpiler_hits)

    # Bilingual Vietnamese search resolves English QA tools/skills
    vi_hits = engine.search_tools("kiểm thử đột biến")
    assert len(vi_hits) > 0
    assert any(
        "mutat" in str(h.get("name", "") or h.get("id", "") or h.get("summary", "")).lower()
        for h in vi_hits
    )


def test_negative_meta_tool_numeric_prefix_no_hijack_and_empty_query():
    """Negative: Bare numeric token '11' does not hijack '11-ai-and-prompting' skills; empty query returns []."""
    from tools.runtime.meta_tool_engine import MetaToolEngine

    engine = MetaToolEngine(REPO_ROOT)
    assert engine.search_tools("") == []

    # Querying '11' must not return all 11-ai-and-prompting skills via numeric domain prefix hijack
    hits_11 = engine.search_tools("11")
    ai_prompting_hits = [
        h for h in hits_11 if h.get("kind") == "skill" and h.get("domain") == "11-ai-and-prompting"
    ]
    assert ai_prompting_hits == [], f"Bare numeric '11' hijacked domain prefix: {ai_prompting_hits}"


def test_boundary_catalog_malformed_python_file_graceful_fallback(tmp_path: Path):
    """Boundary: Malformed Python source during AST risk/flag inspection falls back cleanly without raising."""
    from tools.report.generate_tool_catalog import infer_tool_risk_and_cli_metadata

    bad_file = tmp_path / "broken_skill_helper.py"
    bad_file.write_text("def broken(:\n    pass\n", encoding="utf-8")

    meta = infer_tool_risk_and_cli_metadata(str(bad_file), "broken_skill_helper.py")
    assert meta["risk_level"] == "read_only"
    assert isinstance(meta["inputs"], list)
    assert isinstance(meta["description"], str)


# ==============================================================================
# 2. M5 — SYNAPSE-QA-BENCH (BFCL) PRECISION & HONEST SELECTED-TOOL VALIDATION
# ==============================================================================


def test_positive_bfcl_bench_100_percent_and_transpiler_disambiguation():
    """Positive (TC-04): SynapseQABench achieves 100.0% overall score and selects omni_transpiler.py on TC-BENCH-07."""
    from tools.orchestration.synapse_qa_bench import (
        SynapseQABench,
        ToolBenchEvalDTO,
        score_action_aligned_tool_candidates,
    )

    bench = SynapseQABench()
    report = bench.run_benchmark()

    assert report["overall_score"] == 100.0
    assert report["tool_selection_accuracy"] == 100.0
    assert report["arg_validity_accuracy"] == 100.0
    assert report["irrelevance_detection_rate"] == 100.0
    assert report["passed"] is True

    tc07 = next(d for d in report["details"] if d["id"] == "TC-BENCH-07")
    assert tc07["expected"] == "omni_transpiler.py"
    assert tc07["selected"] == "omni_transpiler.py"
    assert tc07["tool_matched"] is True
    assert tc07["args_valid"] is True

    # Bilingual Vietnamese intent resolves correctly through open-pool scorer
    corpus = bench._build_corpus_docs(bench._open_pool_candidates)
    vi_pick = score_action_aligned_tool_candidates(
        "Chuyển đổi mã kiểm thử giữa Java, TypeScript và Groovy không tốn token",
        bench._open_pool_candidates,
        abstain_threshold=0.20,
        corpus_docs=corpus,
    )
    assert vi_pick == "omni_transpiler.py"
    assert isinstance(ToolBenchEvalDTO(100.0, 100.0, 100.0, 100.0, True), ToolBenchEvalDTO)


def test_negative_bfcl_wrong_selected_tool_fails_args_valid_and_abstains():
    """Negative (TC-03): Selecting a wrong sibling tool MUST fail args_valid; out-of-domain abstains ('')."""
    from tools.orchestration.synapse_qa_bench import SynapseQABench

    single_case = [
        {
            "id": "TC-NEG-WRONG-TOOL",
            "intent": "Transpile test cases bidirectionally between Java, TypeScript, and Groovy",
            "expected_tool": "omni_transpiler.py",
            "valid_args": ["tests/sample_test.ts", "--to", "groovy"],
            "irrelevant_tools": ["flaky_detector.py"],
        }
    ]
    bench = SynapseQABench(cases=single_case)

    # Force resolver to return omni_parser.py (wrong sibling tool without --to flag)
    report = bench.run_benchmark(tool_resolver_fn=lambda _intent: "omni_parser.py")
    detail = report["details"][0]
    assert detail["selected"] == "omni_parser.py"
    assert detail["tool_matched"] is False
    assert detail["args_valid"] is False

    # Force resolver to abstain ('') on a required tool case -> args_valid must also be False
    abstain_report = bench.run_benchmark(tool_resolver_fn=lambda _intent: "")
    assert abstain_report["details"][0]["args_valid"] is False

    # Out-of-domain K8s Helm query abstains cleanly
    default_bench = SynapseQABench()
    k8s_selected = default_bench._default_tool_resolver(
        "Deploy a Kubernetes Helm chart to an AWS EKS cluster with Istio service mesh",
        default_bench._open_pool_candidates,
    )
    assert k8s_selected == ""


def test_boundary_bfcl_empty_and_unicode_intents():
    """Boundary: Empty, whitespace, and emoji-only intents return '' without crashing."""
    from tools.orchestration.synapse_qa_bench import score_action_aligned_tool_candidates

    for sample in ("", "   ", "🔥🎯"):
        assert score_action_aligned_tool_candidates(sample, ["verify_all.py", "omni_transpiler.py"]) == ""


def test_cli_bfcl_bench_and_meta_tool_json_flags():
    """CLI (TC-04): `synapse_qa_bench.py --json` and `meta_tool_engine.py search --json` exit 0 with valid JSON."""
    bench_script = os.path.join(REPO_ROOT, "tools", "orchestration", "synapse_qa_bench.py")
    proc_bench = subprocess.run(
        [sys.executable, bench_script, "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
    )
    assert proc_bench.returncode == 0, proc_bench.stderr
    bench_data = json.loads(proc_bench.stdout)
    assert bench_data["overall_score"] == 100.0
    assert bench_data["passed"] is True

    meta_script = os.path.join(REPO_ROOT, "tools", "runtime", "meta_tool_engine.py")
    proc_meta = subprocess.run(
        [sys.executable, meta_script, "search", "super-plan", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        encoding="utf-8",
    )
    assert proc_meta.returncode == 0, proc_meta.stderr
    meta_data = json.loads(proc_meta.stdout)
    assert isinstance(meta_data, list)
    assert any(item.get("id") == "super-plan" for item in meta_data)
