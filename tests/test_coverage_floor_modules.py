#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit and CLI tests raising coverage across zero- and low-coverage Synapse Hub tooling."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT_DIR / "tools"
for _p in (str(ROOT_DIR), str(TOOLS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.core import git_worktree_manager, sync_skills_manifest
from tools.core.models import QualityGateConfig, SynapseConfig
from tools.core.models.config_model import (
    InferLinterConfig,
    PerformanceConfig,
    PerformanceSLA,
    QualityGatesDict,
    SecurityConfig,
)
from tools.design import smart_visual_masker
from tools.orchestration import runaway_stopper, solo_contracts
from tools.reasoning import telegraphic_enforcer
from tools.report import generate_allure_report, sarif_exporter


# ==============================================================================
# 1. POSITIVE SCENARIO — SARIF, Models, Masker, Telegraphic, Contracts
# ==============================================================================

def test_positive_sarif_models_masker_telegraphic_and_contracts(tmp_path: Path):
    """Positive paths for sarif_exporter, config models, smart_visual_masker, telegraphic_enforcer, and solo_contracts."""
    # SARIF exporter
    sarif_out = tmp_path / "sub" / "out.sarif"
    findings = [
        {"rule_id": "SYNAPSE001", "message": "Zero assertions", "file_path": "tests\\t.py", "line": 12, "level": "error"}
    ]
    returned_path = sarif_exporter.export_sarif(findings, str(sarif_out))
    assert Path(returned_path).is_file()
    data = json.loads(sarif_out.read_text(encoding="utf-8"))
    assert data["version"] == "2.1.0"
    assert data["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "tests/t.py"

    # TypedDict models
    gates: QualityGatesDict = {
        "gate_1_bom_check": True,
        "gate_2_path_portability": True,
        "gate_3_clean_pom": True,
        "gate_4_ai_docs_lint": True,
        "gate_5_cleanup_blacklist": True,
        "gate_6_credential_security": True,
        "gate_7_infer_linter": True,
        "gate_8_micro_mutator": True,
        "gate_9_skill_collision": True,
        "gate_10_performance_sla": True,
    }
    qg: QualityGateConfig = {"mutation_min_score": 80.0, "gates": gates}
    sla: PerformanceSLA = {"p95_ms": 500.0}
    perf: PerformanceConfig = {"sla": sla, "auto_benchmark_fallback": False}
    sec: SecurityConfig = {"allowed_pentest_hosts": ["localhost"], "require_consent": True}
    linter: InferLinterConfig = {"enabled": True, "strict": True}
    cfg: SynapseConfig = {
        "version": "4.10.0",
        "quality_gates": qg,
        "performance": perf,
        "security": sec,
        "infer_linter": linter,
    }
    assert cfg["quality_gates"]["mutation_min_score"] == 80.0

    # SmartVisualMasker
    css = smart_visual_masker.SmartVisualMasker.get_anti_flake_css()
    assert "animation: none !important;" in css
    ts_opts = smart_visual_masker.SmartVisualMasker.generate_playwright_ts_options([".custom-clock"])
    assert "page.locator('.custom-clock')" in ts_opts
    js_script = smart_visual_masker.SmartVisualMasker.generate_browser_mask_script([".avatar"])
    assert "data-visual-masked" in js_script

    # TelegraphicEnforcer
    fluff_text = "Hello there! I'm happy to help. Here is the result: Step 1 -> OK. Hope this helps!"
    is_clean, found = telegraphic_enforcer.TelegraphicEnforcer.audit_text(fluff_text)
    assert is_clean is False
    assert len(found) >= 3
    purified, saved = telegraphic_enforcer.TelegraphicEnforcer.purify_to_telegraphic(fluff_text)
    assert "Step 1 -> OK." in purified
    assert saved > 0

    # Solo contracts 4-scenario coverage & relevance
    test_file = tmp_path / "test_widget.py"
    test_file.write_text(
        "from my_pkg import widget\n\n"
        "def test_positive_widget():\n    '''positive valid happy'''\n    pass\n"
        "def test_case_doc_only():\n    '''negative error case'''\n    pass\n"
        "def test_boundary_widget_empty(): pass\n"
        "def test_cli_widget_json_flag(): pass\n",
        encoding="utf-8",
    )
    target_file = tmp_path / "my_pkg" / "widget.py"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("def render_widget():\n    return 'ok'\n", encoding="utf-8")

    cov = solo_contracts.analyze_four_scenario_coverage([str(test_file)], working_dir=str(tmp_path))
    assert cov["complete"] is True
    assert cov["missing_scenarios"] == []
    assert cov["matched_evidence"]["positive"] == ["test_positive_widget:positive"]
    assert cov["matched_evidence"]["negative"] == ["test_case_doc_only:negative"]

    # Default working_dir=None resolves relative paths against repo root
    cov_repo = solo_contracts.analyze_four_scenario_coverage(["tests/test_coverage_floor_modules.py"])
    assert cov_repo["complete"] is True

    # Non-Python test file & SyntaxError Python fallback & output-only fallback
    spec_ts = tmp_path / "widget.spec.ts"
    spec_ts.write_text("test('positive negative boundary cli', () => {});", encoding="utf-8")
    cov_ts = solo_contracts.analyze_four_scenario_coverage([str(spec_ts)], working_dir=str(tmp_path))
    assert cov_ts["complete"] is True
    assert cov_ts["matched_evidence"]["positive"] == ["widget.spec.ts:positive"]

    syntax_py = tmp_path / "test_broken_syntax.py"
    syntax_py.write_text("def test_positive_broken(:\n", encoding="utf-8")
    cov_syn = solo_contracts.analyze_four_scenario_coverage([str(syntax_py)], output="negative boundary cli", working_dir=str(tmp_path))
    assert cov_syn["coverage"]["positive"] is True
    assert cov_syn["coverage"]["negative"] is False  # output not scanned when test_files is non-empty

    cov_empty = solo_contracts.analyze_four_scenario_coverage([], output="", working_dir=str(tmp_path))
    assert cov_empty["coverage"] == {k: False for k in solo_contracts.REQUIRED_RED_SCENARIOS}

    cov_out = solo_contracts.analyze_four_scenario_coverage([], output="positive negative boundary cli", working_dir=str(tmp_path))
    assert cov_out["complete"] is True
    assert cov_out["matched_evidence"]["positive"] == ["output:positive"]

    # _extract_target_identifiers relative, absolute, and outside-root paths
    toks_rel, syms_rel = solo_contracts._extract_target_identifiers("my_pkg/widget.py", str(tmp_path))
    assert "my_pkg/widget.py" in toks_rel
    assert "my_pkg.widget" in toks_rel
    assert "render_widget" in syms_rel

    toks_out, _ = solo_contracts._extract_target_identifiers("../outside.py", str(tmp_path))
    assert "../outside.py" not in toks_out

    rel_ok, rel_info = solo_contracts.verify_red_target_relevance(
        [str(test_file)], output="", target_files=[str(target_file)], working_dir=str(tmp_path)
    )
    assert rel_ok is True
    assert rel_info["matched"] is True


# ==============================================================================
# 2. NEGATIVE SCENARIO — Error Paths, Missing Files, Runaway & Worktree Failures
# ==============================================================================

def test_negative_worktree_sync_allure_and_contracts(tmp_path: Path):
    """Negative error handling: git failures, missing manifests, non-existent test files, and runaway detection."""
    # sync_skills_manifest missing manifest / empty dir
    ok_missing, diffs_missing = sync_skills_manifest.sync_manifest(tmp_path / "skills", tmp_path / "missing.json")
    assert ok_missing is False
    assert "Manifest not found" in diffs_missing[0]

    empty_manifest = tmp_path / "skills_manifest.json"
    empty_manifest.write_text(json.dumps({"skills": [], "totalSkills": 0}), encoding="utf-8")
    (tmp_path / "skills").mkdir()
    ok_empty, diffs_empty = sync_skills_manifest.sync_manifest(tmp_path / "skills", empty_manifest)
    assert ok_empty is False
    assert "No SKILL.md files found" in diffs_empty[0]

    # WorktreeManager error paths
    mgr = git_worktree_manager.WorktreeManager(base_dir=str(tmp_path / ".synapse" / "worktrees"))
    fail_cp = subprocess.CompletedProcess(["git"], 1, stdout="", stderr="fatal: worktree error")
    with patch.object(git_worktree_manager, "run_git", return_value=fail_cp):
        assert mgr.list_worktrees() == []
        res_create = mgr.create_worktree("agent@1")
        assert res_create["success"] is False
        assert "fatal: worktree error" in res_create["error"]
        res_remove = mgr.remove_worktree(str(tmp_path / "wt1"))
        assert res_remove["success"] is False

    # generate_allure_report when allure CLI missing or fails
    res_dir = tmp_path / "allure-results"
    res_dir.mkdir()
    with patch("shutil.which", return_value=None):
        assert generate_allure_report.generate_allure_report(str(res_dir), str(tmp_path / "out")) == 1
    with patch("shutil.which", return_value="allure"), patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(2, ["allure"])
    ):
        assert generate_allure_report.generate_allure_report(str(res_dir), str(tmp_path / "out")) == 2

    # solo_contracts unmatched target and syntax error test file
    bad_test = tmp_path / "test_bad.py"
    bad_test.write_text("def broken(:\n", encoding="utf-8")
    unrelated_target = tmp_path / "unrelated_module.py"
    unrelated_target.write_text("def unique_symbol_xyz():\n    return 1\n", encoding="utf-8")
    rel_ok, rel_info = solo_contracts.verify_red_target_relevance(
        [str(bad_test)], output="", target_files=[str(unrelated_target)], working_dir=str(tmp_path)
    )
    assert rel_ok is False
    assert len(rel_info["unmatched_targets"]) == 1


# ==============================================================================
# 3. BOUNDARY SCENARIO — Sync Drift, Index Truncation, Worktree & Allure Edge Cases
# ==============================================================================

def test_boundary_sync_manifest_worktree_and_allure(tmp_path: Path):
    """Boundary cases: frontmatter drift sync, 130-char summary clipping, worktree create/remove, and Allure CI skip."""
    skills_dir = tmp_path / "skills"
    s1_dir = skills_dir / "01-web" / "demo-skill"
    s2_dir = skills_dir / "09-ci-and-devops" / "ci-skill"
    s1_dir.mkdir(parents=True)
    s2_dir.mkdir(parents=True)

    (s1_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ncategory: web\nversion: 1.2.0\n"
        "description: \"Updated description for demo skill\"\n"
        "policies:\n  network: none\n---\n# Demo\n",
        encoding="utf-8",
    )
    long_desc = " ".join(["longword"] * 25)
    (s2_dir / "SKILL.md").write_text(
        f"---\nname: ci-skill\ncategory: devops\nversion: 1.0.0\ndescription: \"{long_desc}\"\n---\n# CI\n",
        encoding="utf-8",
    )

    manifest_path = tmp_path / "skills_manifest.json"
    manifest_path.write_text(
        json.dumps({
            "totalSkills": 99,
            "skills": [
                {"id": "demo-skill", "domain": "01-web", "category": "old", "version": "1.0.0", "description": "Old"},
                {"id": "ci-skill", "domain": "09-ci-and-devops", "category": "devops", "version": "1.0.0", "description": long_desc},
            ],
        }),
        encoding="utf-8",
    )

    in_sync, diffs = sync_skills_manifest.sync_manifest(skills_dir, manifest_path, write=True)
    assert in_sync is False
    assert len(diffs) >= 4
    idx_out = tmp_path / "skills_index.json"
    assert idx_out.is_file()
    idx_data = json.loads(idx_out.read_text(encoding="utf-8"))
    assert len(idx_data["skills"]) == 2
    ci_item = [s for s in idx_data["skills"] if s["id"] == "ci-skill"][0]
    assert len(ci_item["summary"]) <= 130
    assert "ci" in ci_item["stack_triggers"]

    # Re-run check now that write=True synced everything
    in_sync_after, diffs_after = sync_skills_manifest.sync_manifest(skills_dir, manifest_path, write=False)
    assert in_sync_after is True
    assert diffs_after == []

    # WorktreeManager happy path with mocked git
    plan_src = tmp_path / "my_plan.md"
    plan_src.write_text("# Plan", encoding="utf-8")
    wt_root = tmp_path / ".synapse" / "worktrees"
    mgr = git_worktree_manager.WorktreeManager(base_dir=str(wt_root))

    def _fake_run_git(args, cwd=None):
        if args[:3] == ["worktree", "list", "--porcelain"]:
            return subprocess.CompletedProcess(
                ["git"],
                0,
                stdout=f"worktree {wt_root / 'agent-1-1'}\nHEAD abc123\nbranch refs/heads/subagent/agent-1\n\n",
                stderr="",
            )
        return subprocess.CompletedProcess(["git"], 0, stdout="pruned", stderr="")

    with patch.object(git_worktree_manager, "run_git", side_effect=_fake_run_git):
        wts = mgr.list_worktrees()
        assert len(wts) == 1
        created = mgr.create_worktree("agent-1", plan_path=str(plan_src), share_dependencies=False)
        assert created["success"] is True
        assert created["copied_plan_path"] == ".synapse/plans/my_plan.md"
        removed = mgr.remove_worktree(str(wt_root / "agent-1-1"))
        assert removed["success"] is True
        assert removed["deleted_branch"] == "subagent/agent-1"
        pruned = mgr.prune_stale()
        assert pruned["success"] is True

    # generate_allure_report open_browser skipped under CI=true
    res_dir = tmp_path / "allure-res"
    res_dir.mkdir()
    with patch("shutil.which", return_value="allure"), patch("subprocess.run") as mock_run, patch.dict(
        "os.environ", {"CI": "true"}, clear=False
    ):
        rc = generate_allure_report.generate_allure_report(str(res_dir), str(tmp_path / "rep"), open_browser=True)
        assert rc == 0
        assert mock_run.call_count == 1


# ==============================================================================
# 4. CLI & RESILIENCE SCENARIO — Main Entrypoints Across Tooling Modules
# ==============================================================================

def test_cli_entrypoints_and_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    """CLI entrypoint coverage for sarif_exporter, sync_skills_manifest, runaway_stopper, git_worktree_manager, allure, masker, telegraphic."""
    # sarif_exporter.main with dict payload
    in_json = tmp_path / "findings.json"
    in_json.write_text(json.dumps({"findings": [{"rule_id": "SYNAPSE002", "message": "Swallowed", "file_path": "a.py", "line": 3}]}), encoding="utf-8")
    out_sarif = tmp_path / "rep.sarif"
    monkeypatch.setattr(sys, "argv", ["sarif_exporter.py", "--input", str(in_json), "--output", str(out_sarif)])
    sarif_exporter.main()
    assert out_sarif.is_file()
    capsys.readouterr()

    # runaway_stopper.main --turns --tokens --json
    monkeypatch.setattr(sys, "argv", ["runaway_stopper.py", "--turns", "2", "--tokens", "500", "--json"])
    runaway_stopper.main()
    out_rs = json.loads(capsys.readouterr().out)
    assert out_rs["is_runaway"] is False

    # runaway_stopper.main --transcript triggering runaway exit 1
    tr_file = tmp_path / "turns.json"
    tr_file.write_text(json.dumps([{"turn_index": i, "tokens_est": 50000} for i in range(5)]), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["runaway_stopper.py", "--transcript", str(tr_file)])
    with pytest.raises(SystemExit) as exc_info:
        runaway_stopper.main()
    assert exc_info.value.code == 1

    # sync_skills_manifest.main --check
    monkeypatch.setattr(
        sys, "argv", ["sync_skills_manifest.py", "--skills-dir", str(ROOT_DIR / "skills"), "--manifest", str(ROOT_DIR / "skills_manifest.json"), "--check"]
    )
    assert sync_skills_manifest.main() == 0
    capsys.readouterr()

    # git_worktree_manager.main list & prune --json
    with patch.object(
        git_worktree_manager,
        "run_git",
        return_value=subprocess.CompletedProcess(["git"], 0, stdout="", stderr=""),
    ):
        monkeypatch.setattr(sys, "argv", ["git_worktree_manager.py", "list", "--json"])
        git_worktree_manager.main()
        assert json.loads(capsys.readouterr().out) == []

        monkeypatch.setattr(sys, "argv", ["git_worktree_manager.py", "prune", "--json"])
        git_worktree_manager.main()
        assert json.loads(capsys.readouterr().out)["success"] is True

    # smart_visual_masker.main --css / --js-script / --playwright-snippet / default
    for flag in (["--css"], ["--js-script"], ["--playwright-snippet"], []):
        monkeypatch.setattr(sys, "argv", ["smart_visual_masker.py"] + flag)
        smart_visual_masker.main()
        assert capsys.readouterr().out.strip() != ""

    # telegraphic_enforcer.main --text clean and dirty
    monkeypatch.setattr(sys, "argv", ["telegraphic_enforcer.py", "--text", "Step 1 -> PASS"])
    assert telegraphic_enforcer.main() == 0
    monkeypatch.setattr(sys, "argv", ["telegraphic_enforcer.py", "--text", "Hello there! Hope this helps!"])
    assert telegraphic_enforcer.main() == 1

    # generate_allure_report.main
    monkeypatch.setattr(sys, "argv", ["generate_allure_report.py", "--results-dir", str(tmp_path / "missing_dir")])
    with pytest.raises(SystemExit) as exc_al:
        generate_allure_report.main()
    assert exc_al.value.code == 0
