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


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration constraints for Docker container sandbox."""

    image: str = "python:3.12-slim"
    memory_limit: str = "2g"
    cpu_limit: float = 2.0
    timeout_sec: float = 120.0
    network_enabled: bool = True


class DockerSandboxRunner:
    """Manages container lifecycle, volume mounting, and isolated execution."""

    def __init__(self, config: Optional[SandboxConfig] = None) -> None:
        self.config = config or SandboxConfig()

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
    ) -> List[str]:
        """Constructs an isolated 'docker run' CLI command string list."""
        c_name = container_name or f"synapse_sandbox_{uuid.uuid4().hex[:8]}"
        norm_workspace = os.path.abspath(workspace_dir)

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
            "SYNAPSE_MODE=hub",
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

        docker_cmd = self.build_docker_command(command, ws_dir)
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
