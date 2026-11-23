# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for DockerSandboxRunner (tests/test_docker_sandbox_runner.py).

Verifies Docker command construction, fallback behavior, resource limits,
and execution status handling.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

from unittest.mock import MagicMock, patch
import pytest

from tools.runtime.docker_sandbox_runner import DockerSandboxRunner, SandboxConfig


@pytest.fixture
def default_runner():
    return DockerSandboxRunner()


def test_sandbox_config_defaults(default_runner):
    cfg = default_runner.config
    assert cfg.image == "python:3.12-slim"
    assert cfg.memory_limit == "2g"
    assert cfg.cpu_limit == 2.0
    assert cfg.timeout_sec == 120.0
    assert cfg.network_enabled is True


def test_build_docker_command_structure(default_runner):
    cmd = ["pytest", "tests/"]
    ws = "/tmp/workspace"
    docker_cmd = default_runner.build_docker_command(cmd, ws, container_name="test_cnt")

    assert docker_cmd[0] == "docker"
    assert docker_cmd[1] == "run"
    assert "--rm" in docker_cmd
    assert "--name" in docker_cmd
    assert "test_cnt" in docker_cmd
    assert "-m" in docker_cmd and "2g" in docker_cmd
    assert "--cpus=2.0" in docker_cmd
    assert "-w" in docker_cmd and "/workspace" in docker_cmd
    assert "python:3.12-slim" in docker_cmd
    assert docker_cmd[-2:] == ["pytest", "tests/"]


def test_network_disabled_flag():
    cfg = SandboxConfig(network_enabled=False)
    runner = DockerSandboxRunner(config=cfg)
    docker_cmd = runner.build_docker_command(["python", "main.py"], "/ws")
    assert "--network" in docker_cmd
    assert "none" in docker_cmd


def test_fallback_when_docker_unavailable(default_runner):
    with patch.object(default_runner, "is_docker_available", return_value=False):
        res = default_runner.run_sandboxed(["pytest", "tests/"])
        assert res["status"] == "FALLBACK_LOCAL"
        assert res["sandboxed"] is False
        assert "Falling back to local execution" in res["message"]


def test_docker_run_success_handling(default_runner):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "ALL TESTS PASSED"
    mock_proc.stderr = ""

    with patch.object(default_runner, "is_docker_available", return_value=True), \
         patch("subprocess.run", return_value=mock_proc):
        res = default_runner.run_sandboxed(["pytest", "tests/"])
        assert res["status"] == "PASSED"
        assert res["exit_code"] == 0
        assert res["sandboxed"] is True
        assert res["stdout"] == "ALL TESTS PASSED"
