#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-Scenario Unit Tests for tools/runtime/action_bundler.py."""

import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.runtime.action_bundler import ActionBundler


class TestActionBundler:
    def test_positive_read_slice_ast_slice_and_run_cmd(self, tmp_path):
        sample = tmp_path / "sample.py"
        sample.write_text("line1\ndef hello(x: int) -> int:\n    return x + 1\n", encoding="utf-8")

        batch = ActionBundler.execute_batch(
            [
                {"id": "r1", "action": "read_slice", "path": "sample.py", "lines": [2, 3]},
                {"id": "a1", "action": "ast_slice", "path": "sample.py"},
                {"id": "c1", "action": "run_cmd", "cmd": [sys.executable, "-c", "print('ok')"]},
            ],
            repo_root=str(tmp_path),
        )
        assert batch["batch_size"] == 3
        assert batch["completed"] == 3
        assert batch["round_trips_saved"] == 2
        assert batch["results"]["r1"]["status"] == "SUCCESS"
        assert "def hello" in batch["results"]["r1"]["content"]
        assert batch["results"]["a1"]["status"] == "SUCCESS"
        assert "hello" in batch["results"]["a1"]["skeleton"]
        assert batch["results"]["c1"]["status"] == "SUCCESS"
        assert batch["results"]["c1"]["stdout"] == "ok"

    def test_negative_missing_file_missing_cmd_and_unknown_action(self, tmp_path):
        missing = ActionBundler.execute_single_action(
            {"id": "m", "action": "read_slice", "path": "nope.txt"}, repo_root=str(tmp_path)
        )
        assert missing["status"] == "ERROR"

        no_cmd = ActionBundler.execute_single_action({"id": "nc", "action": "run_cmd"}, repo_root=str(tmp_path))
        assert no_cmd["status"] == "ERROR"

        unknown = ActionBundler.execute_single_action({"id": "u", "action": "drop_db"}, repo_root=str(tmp_path))
        assert unknown["status"] == "ERROR"
        assert "Unsupported" in unknown["error"]

        bad_cmd = ActionBundler.execute_single_action(
            {"id": "fail", "action": "run_cmd", "cmd": [sys.executable, "-c", "import sys; sys.exit(2)"]},
            repo_root=str(tmp_path),
        )
        assert bad_cmd["status"] == "FAILED"
        assert bad_cmd["exit_code"] == 2

        long_out = ActionBundler.execute_single_action(
            {
                "id": "trunc",
                "action": "run_cmd",
                "cmd": [sys.executable, "-c", "import sys; print('A'*2000); print('E'*800, file=sys.stderr)"],
            },
            repo_root=str(tmp_path),
        )
        assert len(long_out["stdout"]) == 1500
        assert len(long_out["stderr"]) == 500

        if os.name == "nt":
            builtin_shell = ActionBundler.execute_single_action(
                {"id": "shell_guard", "action": "run_cmd", "cmd": "echo builtin_only"},
                repo_root=str(tmp_path),
            )
            assert builtin_shell["status"] == "EXCEPTION"

    def test_boundary_empty_batch(self, tmp_path):
        batch = ActionBundler.execute_batch([], repo_root=str(tmp_path))
        assert batch["batch_size"] == 0
        assert batch["completed"] == 0
        assert batch["round_trips_saved"] == 0
        assert batch["results"] == {}

    def test_cli_batch_and_demo_execution(self, tmp_path, monkeypatch, capsys):
        from tools.runtime.action_bundler import main as bundler_main

        batch_file = tmp_path / "ops.json"
        batch_file.write_text(
            json.dumps([{"id": "agents_vi", "action": "read_slice", "path": "AGENTS.md", "lines": [1, 5]}]),
            encoding="utf-8",
        )
        monkeypatch.setattr(sys, "argv", ["action_bundler.py", "--batch", str(batch_file)])
        rc_batch = bundler_main()
        assert rc_batch == 0
        out_batch = capsys.readouterr().out
        assert "Thế Vị" in out_batch
        payload = json.loads(out_batch)
        assert payload["results"]["agents_vi"]["status"] == "SUCCESS"

        monkeypatch.setattr(sys, "argv", ["action_bundler.py", "--demo"])
        rc_demo = bundler_main()
        assert rc_demo == 0
        out_demo = capsys.readouterr().out
        assert "Round-Trips Saved" in out_demo
        assert "(Error:" in out_demo
        assert "[SUCCESS] Operation 'read_agents_anchor'" in out_demo

        monkeypatch.setattr(sys, "argv", ["action_bundler.py"])
        rc_none = bundler_main()
        assert rc_none == 0
        capsys.readouterr()
