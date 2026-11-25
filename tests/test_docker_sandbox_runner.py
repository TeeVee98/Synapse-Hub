# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Unit tests for DockerSandboxRunner (tests/test_docker_sandbox_runner.py).

Verifies Docker command construction, dynamic SYNAPSE_MODE propagation,
Windows mount path normalization, fallback behavior, resource limits,
execution status handling, and Compose V2 template compliance.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

import os
import subprocess
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
    assert cfg.synapse_mode is None


def test_build_docker_command_structure(default_runner, monkeypatch):
    monkeypatch.delenv("SYNAPSE_MODE", raising=False)
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
    assert "SYNAPSE_MODE=hub" in docker_cmd
    assert "python:3.12-slim" in docker_cmd
    assert docker_cmd[-2:] == ["pytest", "tests/"]


def test_dynamic_synapse_mode_from_env_and_override(monkeypatch):
    monkeypatch.setenv("SYNAPSE_MODE", "CLIENT")
    runner = DockerSandboxRunner()
    docker_cmd = runner.build_docker_command(["pytest"], "/tmp/ws")
    assert "SYNAPSE_MODE=client" in docker_cmd
    assert "SYNAPSE_MODE=hub" not in docker_cmd

    override_cmd = runner.build_docker_command(["pytest"], "/tmp/ws", mode="hub")
    assert "SYNAPSE_MODE=hub" in override_cmd


def test_invalid_mode_and_empty_workspace_raise(default_runner):
    with pytest.raises(ValueError, match="Invalid SYNAPSE_MODE"):
        default_runner.build_docker_command(["pytest"], "/tmp/ws", mode="staging")

    with pytest.raises(ValueError, match="workspace_dir"):
        default_runner.build_docker_command(["pytest"], "   ")


def test_windows_mount_path_normalization():
    docker_cmd = DockerSandboxRunner().build_docker_command(["pytest"], r"D:\Synapse Hub")
    vol_idx = docker_cmd.index("-v") + 1
    assert "\\" not in docker_cmd[vol_idx]
    assert docker_cmd[vol_idx].endswith(":/workspace")

    # Also verifies forward-slash mount path remains intact without trailing slash corruption
    docker_cmd_posix = DockerSandboxRunner().build_docker_command(["pytest"], "/tmp/workspace/")
    vol_idx_posix = docker_cmd_posix.index("-v") + 1
    assert "\\" not in docker_cmd_posix[vol_idx_posix]
    assert not docker_cmd_posix[vol_idx_posix].startswith("//")
    assert docker_cmd_posix[vol_idx_posix].endswith(":/workspace")


def test_network_disabled_flag():
    cfg = SandboxConfig(network_enabled=False, synapse_mode="client")
    runner = DockerSandboxRunner(config=cfg)
    docker_cmd = runner.build_docker_command(["python", "main.py"], "/ws")
    assert "--network" in docker_cmd
    assert "none" in docker_cmd
    assert "SYNAPSE_MODE=client" in docker_cmd


def test_fallback_when_docker_unavailable(default_runner):
    with patch.object(default_runner, "is_docker_available", return_value=False):
        res = default_runner.run_sandboxed(["pytest", "tests/"])
        assert res["status"] == "FALLBACK_LOCAL"
        assert res["sandboxed"] is False
        assert "Falling back to local execution" in res["message"]


def test_docker_run_success_and_error_handling(default_runner):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "ALL TESTS PASSED"
    mock_proc.stderr = ""

    with patch.object(default_runner, "is_docker_available", return_value=True), \
         patch("subprocess.run", return_value=mock_proc):
        res = default_runner.run_sandboxed(["pytest", "tests/"], mode="client")
        assert res["status"] == "PASSED"
        assert res["exit_code"] == 0
        assert res["sandboxed"] is True
        assert res["stdout"] == "ALL TESTS PASSED"
        assert "SYNAPSE_MODE=client" in res["command"]

    with patch.object(default_runner, "is_docker_available", return_value=True), \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=1)):
        res_to = default_runner.run_sandboxed(["pytest"])
        assert res_to["status"] == "TIMEOUT"
        assert res_to["exit_code"] == 124


def test_jmeter_distributed_compose_v2_compliant():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    compose_path = os.path.join(repo_root, "tools", "templates", "jmeter-distributed", "docker-compose.yml")
    with open(compose_path, "r", encoding="utf-8") as f:
        raw = f.read()

    assert not raw.lstrip().startswith("version:")
    assert "services:" in raw
    assert "jmeter-master:" in raw
    assert "JVM_ARGS=-Xms1g -Xmx2g" in raw
