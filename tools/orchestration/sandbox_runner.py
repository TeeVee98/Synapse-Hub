#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/orchestration/sandbox_runner.py — Pluggable Ephemeral Test & Mutation Sandbox
---------------------------------------------------------------------------------
Provides physical filesystem and environment isolation for Green and Mutation
verification phases:
  - WorktreeSandbox (stdlib default): Ephemeral git worktree (with dirty overlay)
    or copytree workspace, scrubbed HOME/TMPDIR/secret env vars, and atomic
    artifact promotion ONLY after exit_code == 0.
  - DockerSandbox (opt-in): Hardened container execution (--rm --network none)
    mounted strictly onto an ephemeral staged copy, failing closed if Docker
    is unavailable.
  - HostSandbox (explicit opt-out): Direct execution in repo_root (--sandbox host).
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import secrets
import shlex
import shutil
import site
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

_SAFE_ENV_KEYS = {
    "PATH",
    "PYTHONPATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "SYSTEMROOT",
    "COMSPEC",
    "PATHEXT",
    "WINDIR",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
}

_SENSITIVE_ENV_TOKENS = (
    "KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "CREDENTIAL",
    "AUTH",
    "AWS_",
    "GCP_",
    "AZURE_",
    "OPENAI_",
    "ANTHROPIC_",
    "GEMINI_",
    "GITHUB_",
)

_IGNORED_OVERLAY_PREFIXES = (
    ".git/",
    ".pytest_cache/",
    "__pycache__/",
    "node_modules/",
    "scratch/sandboxes/",
)


class SandboxBackend(Protocol):
    name: str

    def prepare(self, repo_root: str, target_files: List[str]) -> str: ...
    def execute(self, cmd: str, sandbox_dir: str, timeout: float = 60.0) -> Tuple[int, str]: ...
    def promote_artifacts(self, sandbox_dir: str, artifact_paths: List[str], dest_root: str) -> List[str]: ...
    def cleanup(self, sandbox_dir: str) -> None: ...


@dataclass(frozen=True)
class SandboxExecutionResult:
    backend: str
    exit_code: int
    output: str
    promoted_artifacts: List[str]
    isolated_root: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "exit_code": self.exit_code,
            "output": self.output,
            "promoted_artifacts": list(self.promoted_artifacts),
            "isolated_root": self.isolated_root,
        }


def _is_within_root(target_path: str, root_dir: str) -> bool:
    """Returns True iff resolved target_path stays strictly within resolved root_dir."""
    root_real = os.path.realpath(root_dir)
    target_real = os.path.realpath(target_path)
    try:
        return os.path.commonpath([root_real, target_real]) == root_real
    except ValueError:
        return False


def _tokenize_command(cmd: str) -> List[str]:
    """Portably tokenizes a command string without shell=True."""
    if not isinstance(cmd, str) or not cmd.strip():
        return []
    return shlex.split(cmd, posix=(os.name != "nt"))


def rewrite_command_paths(cmd: str, source_root: str, sandbox_dir: str) -> str:
    """Rewrites absolute path references from source_root to sandbox_dir in a command string."""
    if not cmd or not source_root or not sandbox_dir:
        return cmd
    src_abs = os.path.abspath(source_root)
    src_real = os.path.realpath(source_root)
    sbx_abs = os.path.abspath(sandbox_dir)
    rewritten = cmd.replace(src_abs, sbx_abs)
    if src_real != src_abs:
        rewritten = rewritten.replace(src_real, sbx_abs)
    return rewritten


def scrub_sandbox_env(
    sandbox_dir: str,
    base_env: Optional[Dict[str, str]] = None,
    extra_env: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Constructs a scrubbed subprocess environment isolated to sandbox_dir."""
    source_env = dict(os.environ if base_env is None else base_env)
    clean_env: Dict[str, str] = {}
    for k, v in source_env.items():
        k_up = k.upper()
        if any(tok in k_up for tok in _SENSITIVE_ENV_TOKENS):
            continue
        if k in _SAFE_ENV_KEYS or k_up in _SAFE_ENV_KEYS:
            clean_env[k] = v

    sbx_base = os.path.dirname(os.path.abspath(sandbox_dir)) if os.path.basename(os.path.abspath(sandbox_dir)) == "workspace" else os.path.abspath(sandbox_dir)
    sbx_home = os.path.join(sbx_base, ".sandbox_home")
    sbx_tmp = os.path.join(sbx_base, ".sandbox_tmp")
    os.makedirs(sbx_home, exist_ok=True)
    os.makedirs(sbx_tmp, exist_ok=True)

    clean_env["HOME"] = sbx_home
    clean_env["USERPROFILE"] = sbx_home
    clean_env["TMPDIR"] = sbx_tmp
    clean_env["TEMP"] = sbx_tmp
    clean_env["TMP"] = sbx_tmp
    clean_env["SYNAPSE_SANDBOX"] = "1"
    clean_env["PYTHONDONTWRITEBYTECODE"] = "1"

    # Preserve read-only access to user-installed test runners (e.g. pytest in user site-packages)
    # after redirecting HOME into the ephemeral sandbox.
    pp_entries: List[str] = []
    if extra_env and extra_env.get("PYTHONPATH"):
        pp_entries.extend(p for p in extra_env["PYTHONPATH"].split(os.pathsep) if p)
    if clean_env.get("PYTHONPATH"):
        pp_entries.extend(p for p in clean_env["PYTHONPATH"].split(os.pathsep) if p)
    try:
        user_site = site.getusersitepackages()
        if isinstance(user_site, str) and os.path.isdir(user_site):
            pp_entries.append(user_site)
    except Exception as exc:
        sys.stderr.write(f"[WorktreeSandbox] Warning: could not resolve user site-packages: {exc}\n")

    if extra_env:
        for k, v in extra_env.items():
            if k != "PYTHONPATH":
                clean_env[k] = v

    if pp_entries:
        deduped = list(dict.fromkeys(pp_entries))
        clean_env["PYTHONPATH"] = os.pathsep.join(deduped)

    return clean_env


def _is_git_repo(repo_root: str) -> bool:
    """Returns True iff repo_root itself is the top-level directory of a valid git worktree with HEAD."""
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if top.returncode != 0 or not top.stdout.strip():
            return False
        if os.path.realpath(top.stdout.strip()) != os.path.realpath(repo_root):
            return False
        res = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return res.returncode == 0 and bool(res.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


class WorktreeSandbox:
    """Stdlib-first ephemeral workspace isolation via git worktree + dirty overlay (or copytree fallback)."""

    name: str = "worktree"

    def __init__(self, extra_env: Optional[Dict[str, str]] = None) -> None:
        self.extra_env: Dict[str, str] = dict(extra_env or {})
        self._sandbox_meta: Dict[str, Dict[str, Any]] = {}

    def _overlay_dirty_files(self, repo_root: str, workspace_dir: str, target_files: List[str]) -> None:
        """Copies uncommitted modified/untracked files from repo_root into the detached worktree."""
        paths_to_sync: Set[str] = set()
        deleted_paths: Set[str] = set()

        try:
            st = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=all"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if st.returncode == 0:
                for raw_line in st.stdout.splitlines():
                    if len(raw_line) < 4:
                        continue
                    code = raw_line[:2]
                    rel_part = raw_line[3:].strip()
                    if " -> " in rel_part:
                        old_p, new_p = rel_part.split(" -> ", 1)
                        deleted_paths.add(old_p.strip().strip('"'))
                        rel_part = new_p.strip()
                    rel_norm = rel_part.strip('"').replace("\\", "/")
                    if not rel_norm or any(rel_norm.startswith(p) for p in _IGNORED_OVERLAY_PREFIXES):
                        continue
                    if "D" in code:
                        deleted_paths.add(rel_norm)
                    else:
                        paths_to_sync.add(rel_norm)
        except (OSError, subprocess.SubprocessError) as exc:
            sys.stderr.write(f"[WorktreeSandbox] Warning: git status overlay probe failed: {exc}\n")

        for tf in target_files:
            if not tf:
                continue
            rel_tf = os.path.relpath(tf, repo_root) if os.path.isabs(tf) else tf
            rel_norm = rel_tf.replace("\\", "/")
            if not rel_norm.startswith(".."):
                paths_to_sync.add(rel_norm)

        for rel_d in deleted_paths:
            dst = os.path.join(workspace_dir, rel_d)
            if _is_within_root(dst, workspace_dir) and os.path.isfile(dst):
                os.remove(dst)

        for rel_p in paths_to_sync:
            src = os.path.join(repo_root, rel_p)
            dst = os.path.join(workspace_dir, rel_p)
            if not _is_within_root(src, repo_root) or not _is_within_root(dst, workspace_dir):
                continue
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)

    def prepare(self, repo_root: str, target_files: List[str]) -> str:
        abs_root = os.path.abspath(repo_root)
        sbx_parent = tempfile.mkdtemp(prefix=f"synapse_sbx_{os.getpid()}_{secrets.token_hex(3)}_")
        workspace_dir = os.path.join(sbx_parent, "workspace")
        used_worktree = False

        if _is_git_repo(abs_root):
            try:
                wt_res = subprocess.run(
                    ["git", "worktree", "add", "--detach", workspace_dir, "HEAD"],
                    cwd=abs_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                if wt_res.returncode == 0 and os.path.isdir(workspace_dir):
                    used_worktree = True
                    self._overlay_dirty_files(abs_root, workspace_dir, list(target_files or []))
            except (OSError, subprocess.SubprocessError):
                used_worktree = False

        if not used_worktree:
            shutil.copytree(
                abs_root,
                workspace_dir,
                ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "node_modules", "*.pyc"),
                dirs_exist_ok=True,
            )

        self._sandbox_meta[os.path.abspath(workspace_dir)] = {
            "repo_root": abs_root,
            "sbx_parent": sbx_parent,
            "used_worktree": used_worktree,
        }
        return workspace_dir

    def execute(self, cmd: str, sandbox_dir: str, timeout: float = 60.0) -> Tuple[int, str]:
        meta = self._sandbox_meta.get(os.path.abspath(sandbox_dir), {})
        orig_root = meta.get("repo_root", "")
        effective_cmd = rewrite_command_paths(cmd, orig_root, sandbox_dir) if orig_root else cmd
        argv = _tokenize_command(effective_cmd)
        if not argv:
            return 1, "EXECUTION_ERROR: Empty command provided to WorktreeSandbox."

        env = scrub_sandbox_env(sandbox_dir, extra_env=self.extra_env)
        try:
            proc = subprocess.run(
                argv,
                cwd=sandbox_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            return proc.returncode, proc.stdout or ""
        except subprocess.TimeoutExpired:
            return 124, f"TIMEOUT_ERROR: Sandbox command timed out after {timeout}s."
        except FileNotFoundError as exc:
            return 127, f"COMMAND_NOT_FOUND: {exc}"
        except OSError as exc:
            return 1, f"EXECUTION_ERROR: {exc}"

    def promote_artifacts(self, sandbox_dir: str, artifact_paths: List[str], dest_root: str) -> List[str]:
        promoted: List[str] = []
        abs_sbx = os.path.abspath(sandbox_dir)
        abs_dest = os.path.abspath(dest_root)

        for rel_art in artifact_paths or []:
            if not isinstance(rel_art, str) or not rel_art.strip() or os.path.isabs(rel_art):
                continue
            src = os.path.join(abs_sbx, rel_art)
            dst = os.path.join(abs_dest, rel_art)
            if not _is_within_root(src, abs_sbx) or not _is_within_root(dst, abs_dest):
                continue
            if not os.path.isfile(src):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            tmp_dst = f"{dst}.promote.{os.getpid()}.{secrets.token_hex(4)}"
            shutil.copy2(src, tmp_dst)
            os.replace(tmp_dst, dst)
            promoted.append(rel_art.replace("\\", "/"))

        return promoted

    def cleanup(self, sandbox_dir: str) -> None:
        abs_sbx = os.path.abspath(sandbox_dir)
        meta = self._sandbox_meta.pop(abs_sbx, None)
        if meta and meta.get("used_worktree"):
            try:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", abs_sbx],
                    cwd=meta["repo_root"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                sys.stderr.write(f"[WorktreeSandbox] Warning: git worktree remove failed: {exc}\n")
                shutil.rmtree(abs_sbx, ignore_errors=True)
        parent_dir = meta["sbx_parent"] if meta else abs_sbx
        if parent_dir and os.path.exists(parent_dir):
            shutil.rmtree(parent_dir, ignore_errors=True)


class DockerSandbox:
    """Opt-in container sandbox (--sandbox docker) mounting an ephemeral copy with --network none."""

    name: str = "docker"

    def __init__(
        self,
        image: str = "python:3.11-slim",
        docker_binary: str = "docker",
        network_none: bool = True,
    ) -> None:
        self.image = image
        self.docker_binary = docker_binary
        self.network_none = network_none
        self._staging = WorktreeSandbox()

    def build_docker_command(self, cmd: str, sandbox_dir: str) -> List[str]:
        abs_sbx = os.path.abspath(sandbox_dir)
        rewritten = rewrite_command_paths(cmd, abs_sbx, "/workspace")
        meta = self._staging._sandbox_meta.get(abs_sbx, {})
        orig_root = meta.get("repo_root", "")
        if orig_root:
            rewritten = rewrite_command_paths(rewritten, orig_root, "/workspace")
        inner_argv = _tokenize_command(rewritten)

        docker_argv: List[str] = [
            self.docker_binary,
            "run",
            "--rm",
        ]
        if self.network_none:
            docker_argv.extend(["--network", "none"])
        docker_argv.extend([
            "--workdir", "/workspace",
            "-v", f"{abs_sbx}:/workspace",
            "-e", "SYNAPSE_SANDBOX=1",
            "-e", "HOME=/tmp",
            "-e", "TMPDIR=/tmp",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            self.image,
        ])
        docker_argv.extend(inner_argv)
        return docker_argv

    def prepare(self, repo_root: str, target_files: List[str]) -> str:
        return self._staging.prepare(repo_root, target_files)

    def execute(self, cmd: str, sandbox_dir: str, timeout: float = 60.0) -> Tuple[int, str]:
        if not shutil.which(self.docker_binary):
            return 127, f"DOCKER_UNAVAILABLE: Container runtime '{self.docker_binary}' not found on PATH."
        docker_argv = self.build_docker_command(cmd, sandbox_dir)
        try:
            proc = subprocess.run(
                docker_argv,
                cwd=sandbox_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            return proc.returncode, proc.stdout or ""
        except subprocess.TimeoutExpired:
            return 124, f"TIMEOUT_ERROR: Docker sandbox timed out after {timeout}s."
        except OSError as exc:
            return 1, f"DOCKER_EXECUTION_ERROR: {exc}"

    def promote_artifacts(self, sandbox_dir: str, artifact_paths: List[str], dest_root: str) -> List[str]:
        return self._staging.promote_artifacts(sandbox_dir, artifact_paths, dest_root)

    def cleanup(self, sandbox_dir: str) -> None:
        self._staging.cleanup(sandbox_dir)


class HostSandbox:
    """Explicit opt-out backend (--sandbox host) running directly in repo_root."""

    name: str = "host"

    def prepare(self, repo_root: str, target_files: List[str]) -> str:
        return os.path.abspath(repo_root)

    def execute(self, cmd: str, sandbox_dir: str, timeout: float = 60.0) -> Tuple[int, str]:
        argv = _tokenize_command(cmd)
        if not argv:
            return 1, "EXECUTION_ERROR: Empty command provided to HostSandbox."
        try:
            proc = subprocess.run(
                argv,
                cwd=sandbox_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            return proc.returncode, proc.stdout or ""
        except subprocess.TimeoutExpired:
            return 124, f"TIMEOUT_ERROR: Host command timed out after {timeout}s."
        except FileNotFoundError as exc:
            return 127, f"COMMAND_NOT_FOUND: {exc}"
        except OSError as exc:
            return 1, f"EXECUTION_ERROR: {exc}"

    def promote_artifacts(self, sandbox_dir: str, artifact_paths: List[str], dest_root: str) -> List[str]:
        return [p.replace("\\", "/") for p in (artifact_paths or []) if os.path.isfile(os.path.join(dest_root, p))]

    def cleanup(self, sandbox_dir: str) -> None:
        return None


def create_sandbox_backend(mode: str = "worktree", **kwargs: Any) -> SandboxBackend:
    """Factory creating a pluggable SandboxBackend for 'worktree', 'docker', or 'host'."""
    norm = (mode or "worktree").strip().lower()
    if norm == "worktree":
        return WorktreeSandbox(extra_env=kwargs.get("extra_env"))
    if norm == "docker":
        return DockerSandbox(
            image=kwargs.get("image", "python:3.11-slim"),
            docker_binary=kwargs.get("docker_binary", "docker"),
            network_none=kwargs.get("network_none", True),
        )
    if norm == "host":
        return HostSandbox()
    raise ValueError(f"Unsupported sandbox backend mode: {mode!r}. Expected 'worktree', 'docker', or 'host'.")


def run_in_sandbox(
    backend: SandboxBackend,
    repo_root: str,
    cmd: str,
    target_files: Optional[List[str]] = None,
    artifact_paths: Optional[List[str]] = None,
    timeout: float = 60.0,
) -> SandboxExecutionResult:
    """Executes cmd inside an ephemeral sandbox, promoting artifacts ONLY if exit_code == 0."""
    sandbox_dir = backend.prepare(repo_root, list(target_files or []))
    promoted: List[str] = []
    try:
        exit_code, output = backend.execute(cmd, sandbox_dir, timeout=timeout)
        if exit_code == 0 and artifact_paths:
            promoted = backend.promote_artifacts(sandbox_dir, list(artifact_paths), repo_root)
    finally:
        backend.cleanup(sandbox_dir)

    return SandboxExecutionResult(
        backend=backend.name,
        exit_code=exit_code,
        output=output,
        promoted_artifacts=promoted,
        isolated_root=sandbox_dir,
    )
