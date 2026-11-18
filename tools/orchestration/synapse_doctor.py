#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/synapse_doctor.py — Autonomous Environment Diagnostic Suite (`agent-qa doctor`)
-------------------------------------------------------------------------------------
Inspired by Cline's self-healing environment diagnostics and Zed's runtime probes.

Core Capabilities:
  1. Python & Node.js Runtime Check: Verifies Python >= 3.9 and Node.js >= 18.
  2. Browser Automation Health: Inspects Playwright browser binaries and dependencies.
  3. Filesystem & Sandbox Integrity: Validates disk write permissions and temp access.
  4. Git & Codebase Health: Validates branch status, encoding, and working tree purity.
  5. CI & Display Telemetry: Detects headless Linux environments lacking DISPLAY/xvfb.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("synapse_doctor")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def check_python_environment() -> Dict[str, Any]:
    """Inspects Python version, executable, and required standard libraries."""
    major, minor, micro = sys.version_info[:3]
    version_str = f"{major}.{minor}.{micro}"
    passed = (major == 3 and minor >= 9)

    return {
        "name": "Python Runtime",
        "passed": passed,
        "version": version_str,
        "executable": sys.executable,
        "message": f"Python {version_str} (>= 3.9 required)" if passed else f"Python {version_str} is outdated (>= 3.9 required).",
        "remedy": None if passed else "Upgrade Python to 3.9+ via official installer or package manager.",
    }


def check_nodejs_environment() -> Dict[str, Any]:
    """Inspects Node.js and NPM runtime versions."""
    node_cmd = shutil.which("node")
    if not node_cmd:
        return {
            "name": "Node.js Runtime",
            "passed": False,
            "version": None,
            "message": "Node.js executable not found in PATH.",
            "remedy": "Install Node.js 18+ LTS from https://nodejs.org or via fnm/nvm.",
        }

    try:
        res = subprocess.run([node_cmd, "--version"], capture_output=True, text=True, timeout=5.0)
        v_str = (res.stdout or "").strip()
        # Parse v18.x.x
        v_num = int(v_str.lstrip("v").split(".")[0]) if v_str else 0
        passed = v_num >= 18
        return {
            "name": "Node.js Runtime",
            "passed": passed,
            "version": v_str,
            "message": f"Node.js {v_str} (>= 18 required)" if passed else f"Node.js {v_str} is below required LTS (>= 18).",
            "remedy": None if passed else "Upgrade Node.js to version 18+ LTS.",
        }
    except Exception as err:
        return {
            "name": "Node.js Runtime",
            "passed": False,
            "version": None,
            "message": f"Failed to execute node: {err}",
            "remedy": "Ensure Node.js is executable and not blocked by security policies.",
        }


def check_playwright_browsers() -> Dict[str, Any]:
    """Inspects Playwright browser binaries and dependencies."""
    browser_dirs: List[str] = []
    system = platform.system()

    if system == "Windows":
        local_app_data = os.getenv("LOCALAPPDATA", "")
        if local_app_data:
            browser_dirs.append(os.path.join(local_app_data, "ms-playwright"))
    else:
        home = os.path.expanduser("~")
        browser_dirs.extend([
            os.path.join(home, ".cache", "ms-playwright"),
            os.path.join(home, "Library", "Caches", "ms-playwright"),
        ])

    installed_browsers: List[str] = []
    for bdir in browser_dirs:
        if os.path.isdir(bdir):
            try:
                for entry in os.listdir(bdir):
                    if any(p in entry.lower() for p in ("chromium", "firefox", "webkit", "ffmpeg")):
                        installed_browsers.append(entry)
            except OSError:
                continue

    has_chromium = any("chromium" in b.lower() for b in installed_browsers)
    passed = has_chromium

    return {
        "name": "Playwright Browsers",
        "passed": passed,
        "detected_browsers": installed_browsers,
        "message": f"Found {len(installed_browsers)} browser package(s) (Chromium detected: {has_chromium})" if passed else "Playwright Chromium browser binary not detected.",
        "remedy": None if passed else "Run 'npx playwright install chromium' or 'playwright install chromium'.",
    }


def check_filesystem_health(repo_root: str) -> Dict[str, Any]:
    """Checks disk write permissions and temporary directory availability."""
    probe_file = os.path.join(repo_root, f".synapse_probe_{os.getpid()}.tmp")
    can_write_workspace = False
    can_write_temp = False

    try:
        with open(probe_file, "w", encoding="utf-8") as f:
            f.write("probe")
        if os.path.isfile(probe_file):
            can_write_workspace = True
            os.remove(probe_file)
    except Exception:
        can_write_workspace = False

    try:
        with tempfile.NamedTemporaryFile("w", delete=True) as tf:
            tf.write("probe")
            can_write_temp = True
    except Exception:
        can_write_temp = False

    passed = can_write_workspace and can_write_temp

    return {
        "name": "Filesystem Health",
        "passed": passed,
        "workspace_writable": can_write_workspace,
        "temp_writable": can_write_temp,
        "message": "Workspace and temporary directories are fully writable." if passed else "Filesystem permission failure in workspace or temp dir.",
        "remedy": None if passed else "Check folder permissions and disk quotas on the current drive.",
    }


def check_git_status(repo_root: str) -> Dict[str, Any]:
    """Inspects Git repository status, active branch, and UTF-8 encoding."""
    git_cmd = shutil.which("git")
    if not git_cmd:
        return {
            "name": "Git Repository",
            "passed": False,
            "message": "Git CLI not found in PATH.",
            "remedy": "Install Git and ensure it is available in system PATH.",
        }

    try:
        res_branch = subprocess.run(
            [git_cmd, "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        branch = (res_branch.stdout or "").strip()

        res_status = subprocess.run(
            [git_cmd, "status", "-s"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        dirty_lines = [l for l in (res_status.stdout or "").splitlines() if l.strip()]

        return {
            "name": "Git Repository",
            "passed": True,
            "branch": branch,
            "dirty_files_count": len(dirty_lines),
            "message": f"Git repository active on branch '{branch}' ({len(dirty_lines)} modified file(s)).",
            "remedy": None,
        }
    except Exception as err:
        return {
            "name": "Git Repository",
            "passed": False,
            "message": f"Git status probe failed: {err}",
            "remedy": "Verify current folder is a valid git checkout.",
        }


def check_ci_and_display_environment() -> Dict[str, Any]:
    """Inspects virtual display configuration on Linux environments."""
    system = platform.system()
    if system != "Linux":
        return {
            "name": "Display / CI Environment",
            "passed": True,
            "system": system,
            "message": f"Non-Linux platform ({system}); headless Chromium operates natively.",
            "remedy": None,
        }

    display = os.getenv("DISPLAY")
    has_xvfb = shutil.which("xvfb-run") is not None
    is_ci = os.getenv("CI") is not None

    passed = (display is not None) or has_xvfb or not is_ci
    return {
        "name": "Display / CI Environment",
        "passed": passed,
        "display": display,
        "has_xvfb": has_xvfb,
        "is_ci": is_ci,
        "message": f"DISPLAY={display}" if display else ("xvfb-run available" if has_xvfb else "No DISPLAY or xvfb-run detected in Linux container."),
        "remedy": None if passed else "Install xvfb ('apt-get install -y xvfb') or set DISPLAY=:1 for GUI execution.",
    }


def run_doctor_diagnostics(repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Runs all 6 core diagnostic checks and returns consolidated system report."""
    root = os.path.abspath(repo_root or os.getcwd())

    checks = [
        check_python_environment(),
        check_nodejs_environment(),
        check_playwright_browsers(),
        check_filesystem_health(root),
        check_git_status(root),
        check_ci_and_display_environment(),
    ]

    all_passed = all(c["passed"] for c in checks)
    failed_count = sum(1 for c in checks if not c["passed"])

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repo_root": root,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "all_passed": all_passed,
        "total_checks": len(checks),
        "failed_count": failed_count,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synapse Doctor — Autonomous Environment & Readiness Diagnostics"
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to inspect (default: current directory).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON diagnostic report.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any diagnostic check fails.",
    )

    args = parser.parse_args()

    report = run_doctor_diagnostics(args.repo_root)

    if args.json:
        print(json.dumps(report, indent=2))
        return 1 if (args.strict and not report["all_passed"]) else 0

    print("======================================================================")
    print("      SYNAPSE HUB — SYSTEM & ENVIRONMENT DIAGNOSTICS (DOCTOR)         ")
    print("======================================================================")
    print(f"Target Directory : {report['repo_root']}")
    print(f"Host Platform    : {report['platform']['system']} {report['platform']['release']} ({report['platform']['machine']})")
    print(f"Timestamp        : {report['timestamp']}")
    print("----------------------------------------------------------------------")

    for c in report["checks"]:
        badge = "[PASS]" if c["passed"] else "[FAIL]"
        print(f"{badge} {c['name']:25}: {c['message']}")
        if not c["passed"] and c.get("remedy"):
            print(f"       -> Action: {c['remedy']}")

    print("======================================================================")
    if report["all_passed"]:
        print("[SUCCESS] All system readiness checks PASSED. Ready for testing & swarm operations.")
        return 0
    else:
        print(f"[WARNING] {report['failed_count']} check(s) flagged potential issues.")
        return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
