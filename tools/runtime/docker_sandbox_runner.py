# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Docker Sandbox Runner (tools/runtime/docker_sandbox_runner.py).

Inspired by AgentScope 2.0 workspace container backends:
Provides sandboxed execution inside Docker containers with strict resource
limits (CPU, Memory, timeout) and automatic fallback to Local Subprocess
execution when Docker daemon is unavailable.

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


VALID_SYNAPSE_MODES = ("hub", "client")


def normalize_docker_mount_path(workspace_dir: str) -> str:
    """Normalizes a host workspace directory to forward-slash mount format."""
    if not isinstance(workspace_dir, str) or not workspace_dir.strip():
        raise ValueError("workspace_dir must be a non-empty path")
    return os.path.abspath(workspace_dir.strip()).replace("\\", "/")


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration constraints for Docker container sandbox."""

    image: str = "python:3.12-slim"
    memory_limit: str = "2g"
    cpu_limit: float = 2.0
    timeout_sec: float = 120.0
    network_enabled: bool = True
    synapse_mode: Optional[str] = None


class DockerSandboxRunner:
    """Manages container lifecycle, volume mounting, and isolated execution."""

    def __init__(self, config: Optional[SandboxConfig] = None) -> None:
        self.config = config or SandboxConfig()

    def _resolve_synapse_mode(self, mode: Optional[str] = None) -> str:
        """Resolves and validates SYNAPSE_MODE from explicit override, config, or env."""
        raw = mode if mode is not None else (
            self.config.synapse_mode if self.config.synapse_mode is not None else os.environ.get("SYNAPSE_MODE", "hub")
        )
        normalized = str(raw).strip().lower()
        if normalized not in VALID_SYNAPSE_MODES:
            raise ValueError(f"Invalid SYNAPSE_MODE '{raw}': expected 'hub' or 'client'.")
        return normalized

    def is_docker_available(self) -> bool:
        """Probes whether the Docker CLI and daemon are operational."""
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return False
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5.0,
                check=False,
            )
            return res.returncode == 0
        except (subprocess.SubprocessError, OSError) as err:
            sys.stderr.write(f"[WARN] Docker availability check failed: {err}\n")
            return False

    def build_docker_command(
        self,
        command_args: List[str],
        workspace_dir: str,
        container_name: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> List[str]:
        """Constructs an isolated 'docker run' CLI command string list."""
        c_name = container_name or f"synapse_sandbox_{uuid.uuid4().hex[:8]}"
        norm_workspace = normalize_docker_mount_path(workspace_dir)
        effective_mode = self._resolve_synapse_mode(mode)

        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            c_name,
            "-m",
            self.config.memory_limit,
            f"--cpus={self.config.cpu_limit}",
            "-v",
            f"{norm_workspace}:/workspace",
            "-w",
            "/workspace",
            "-e",
            f"SYNAPSE_MODE={effective_mode}",
            "-e",
            "CI=true",
            "-e",
            "PYTHONUNBUFFERED=1",
        ]

        if not self.config.network_enabled:
            docker_cmd.extend(["--network", "none"])

        docker_cmd.append(self.config.image)
        docker_cmd.extend(command_args)
        return docker_cmd

    def run_sandboxed(
        self,
        command: List[str],
        workspace_dir: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes the command in a container if available, else returns fallback flag."""
        ws_dir = workspace_dir or os.getcwd()
        if not self.is_docker_available():
            return {
                "status": "FALLBACK_LOCAL",
                "message": "Docker daemon unavailable or not installed. Falling back to local execution.",
                "command": command,
                "exit_code": None,
                "sandboxed": False,
            }

        docker_cmd = self.build_docker_command(command, ws_dir, mode=mode)
        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.config.timeout_sec,
                check=False,
            )
            return {
                "status": "PASSED" if proc.returncode == 0 else "FAILED",
                "command": " ".join(docker_cmd),
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "sandboxed": True,
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "TIMEOUT",
                "command": " ".join(docker_cmd),
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Docker container timed out after {self.config.timeout_sec}s.",
                "sandboxed": True,
            }
        except OSError as os_err:
            return {
                "status": "ERROR",
                "command": " ".join(docker_cmd),
                "exit_code": 1,
                "stdout": "",
                "stderr": str(os_err),
                "sandboxed": True,
            }
