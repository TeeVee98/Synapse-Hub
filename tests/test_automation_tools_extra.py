#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Unit tests covering uncovered Automation CLI tools (API, Heal, Runtime)."""

import json
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.api.api_drift_sentinel import compare_specs
from tools.api.fuzz_payloads import get_field_fuzz_scenarios, get_fuzz_payloads
from tools.api.pairwise_generator import generate_all_pairs, generate_pairwise
from tools.heal.heal_pr_automator import calculate_healing_confidence, generate_pr_draft
from tools.runtime.meta_tool_engine import MetaToolEngine
from tools.runtime.trajectory_compressor import TrajectoryCompressor


class TestApiToolsCoverage:
    def test_api_drift_sentinel_detects_breaking_and_compatible_changes(self):
        old_spec = {
            "paths": {
                "/orders": {
                    "get": {"responses": {"200": {}}},
                    "post": {
                        "parameters": [{"name": "dryRun", "in": "query", "required": False, "type": "boolean"}],
                        "responses": {"201": {}},
                    },
                },
                "/legacy": {"get": {"responses": {"200": {}}}},
            }
        }
        new_spec = {
            "paths": {
                "/orders": {
                    "get": {"responses": {"200": {}}},
                    "post": {
                        "parameters": [
                            {"name": "dryRun", "in": "query", "required": True, "type": "string"},
                            {"name": "tenantId", "in": "header", "required": True, "type": "string"},
                        ],
                        "responses": {},
                    },
                },
                "/v2/orders": {"get": {"responses": {"200": {}}}},
            }
        }
        res = compare_specs(old_spec, new_spec)
        types = {b["type"] for b in res["breaking_changes"]}
        assert {"REMOVED_ENDPOINT", "PARAM_NOW_REQUIRED", "PARAM_TYPE_CHANGED", "NEW_REQUIRED_PARAM"}.issubset(types)
        assert res["is_backward_compatible"] is False
        assert res["contract_health_score"] < 100.0
        assert len(res["warnings"]) >= 1
        assert len(res["additions"]) == 1

        clean = compare_specs(old_spec, old_spec)
        assert clean["is_backward_compatible"] is True
        assert clean["contract_health_score"] == 100.0

    def test_pairwise_generator_covers_100_percent_pairs_and_empty(self):
        params = {
            "browser": ["chromium", "firefox", "webkit"],
            "os": ["linux", "windows"],
            "auth": ["jwt", "oauth"],
        }
        all_pairs = generate_all_pairs(params)
        cases = generate_pairwise(params)
        covered = set()
        for c in cases:
            keys = sorted(c.keys())
            for i in range(len(keys)):
                for j in range(i + 1, len(keys)):
                    covered.add(((keys[i], c[keys[i]]), (keys[j], c[keys[j]])))
        assert covered == all_pairs
        assert len(cases) < 12  # smaller than full Cartesian product
        assert generate_pairwise({}) == []
        assert generate_pairwise({"single": ["a", "b"]}) == [{"single": "a"}, {"single": "b"}]

    def test_fuzz_payloads_categories_and_cli(self):
        sqli = get_fuzz_payloads("sqli")
        assert "sqli_polyglots" in sqli
        assert len(sqli["sqli_polyglots"]) >= 4
        all_p = get_fuzz_payloads("all")
        assert len(all_p) > len(sqli)
        assert get_field_fuzz_scenarios("amount", "integer")
        assert get_field_fuzz_scenarios("username", "string")

        res = subprocess.run(
            [sys.executable, os.path.join(ROOT_DIR, "tools", "api", "fuzz_payloads.py"), "--category", "xss", "--json"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 0
        assert "xss_polyglots" in res.stdout


class TestHealAndRuntimeToolsCoverage:
    def test_heal_pr_automator_confidence_and_draft(self):
        high = calculate_healing_confidence(0.95, 0.92, 0.90)
        assert high["qualified_for_pr"] is True
        assert high["risk_tier"] == "LOW_RISK"

        low = calculate_healing_confidence(0.5, 0.4, 0.3)
        assert low["qualified_for_pr"] is False
        assert low["risk_tier"] == "HIGH_RISK"

        draft = generate_pr_draft(
            page_file="src/pages/LoginPage.ts",
            old_locator="#old-login",
            new_locator="getByTestId('login-btn')",
            confidence_info=high,
            trace_zip="reports/trace.zip",
        )
        assert draft["branch_name"].startswith("heal/loginpage_")
        assert "login-btn" in draft["pr_body"]
        assert "npx playwright show-trace" in draft["pr_body"]

    def test_trajectory_compressor_masks_large_and_preserves_small(self, tmp_path):
        small = TrajectoryCompressor.mask_tool_observation("echo", {}, "ok", log_dir=str(tmp_path))
        assert small["masked"] is False

        big_text = "\n".join(f"line {i}: FAIL check" for i in range(40))
        masked = TrajectoryCompressor.mask_tool_observation("pytest", {"target": "auth"}, big_text, turn_index=3, log_dir=str(tmp_path))
        assert masked["masked"] is True
        assert masked["saved_tokens"] > 0
        assert os.path.isfile(masked["log_file"])
        assert "[Observation Masked:" in masked["content"]

        msgs = [
            {"role": "tool", "tool_name": "read", "content": big_text},
            {"role": "assistant", "content": "working"},
            {"role": "tool", "tool_name": "recent", "content": big_text},
        ]
        compressed, total_saved = TrajectoryCompressor.compress_conversation_messages(
            msgs, keep_recent_turns=1, log_dir=str(tmp_path)
        )
        assert total_saved > 0
        assert "[Observation Masked:" in compressed[0]["content"]
        assert compressed[2]["content"] == big_text

    def test_meta_tool_engine_search_and_execute_direct(self, tmp_path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "probe.py").write_text("import sys\nprint('arg=' + sys.argv[1])\n", encoding="utf-8")
        (tools_dir / "tools_schema.min.json").write_text(
            json.dumps({
                "tools": {
                    "probe": {
                        "cmd": f"{sys.executable} tools/probe.py",
                        "args": {"val": {"type": "string", "req": True}},
                    }
                }
            }),
            encoding="utf-8",
        )
        engine = MetaToolEngine(str(tmp_path))
        hits = engine.search_tools("probe")
        assert any(h["name"] == "probe" for h in hits)
        toon = engine.search_tools("probe", compact_format="toon")
        assert "@schema" in toon

        ok_res = engine.execute_tool("probe", {"val": "hello"})
        assert ok_res["status"] == "SUCCESS"
        assert "arg=hello" in ok_res["stdout"]

        err_res = engine.execute_tool("nonexistent_tool", {})
        assert err_res["status"] == "ERROR"
        assert err_res["exit_code"] == 127
