#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Shared CLI Runtime Utilities for Synapse-Hub Tools
--------------------------------------------------
Eliminates duplicated boilerplate across CLI tools:
  - Robust UTF-8 console output setup (Windows cp1252 / cmd.exe compatibility)
  - Canonical repository root resolution
  - Standardized JSON formatting and error exits
"""

import os
import sys
import json
from typing import Any, Optional


def setup_utf8_output():
    """Configures sys.stdout and sys.stderr with UTF-8 encoding safely."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


# Automatically configure UTF-8 output when this module is imported
setup_utf8_output()


def get_repo_root(start_file: Optional[str] = None) -> str:
    """Returns the canonical absolute repository root path.
    Prioritizes SYNAPSE_PROJECT_ROOT env var, then walks up from start_file or CWD."""
    env_root = os.environ.get("SYNAPSE_PROJECT_ROOT")
    if env_root and os.path.isdir(env_root):
        return os.path.abspath(env_root)

    origin = os.path.abspath(start_file or __file__)
    current = os.path.dirname(origin) if os.path.isfile(origin) else origin

    # Walk up to locate marker files (package.json, pyproject.toml, .agents)
    for _ in range(8):
        if any(os.path.exists(os.path.join(current, marker)) for marker in ("package.json", "pyproject.toml", "AGENTS.md")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    return os.path.abspath(os.getcwd())


def print_json(data: Any, indent: int = 2, file=None):
    """Prints serializable data as UTF-8 formatted JSON."""
    out = json.dumps(data, indent=indent, ensure_ascii=False, default=str)
    print(out, file=file or sys.stdout)


def exit_with_error(message: str, code: int = 1):
    """Prints a formatted error message to stderr and exits."""
    sys.stderr.write(f"[ERROR] {message}\n")
    sys.exit(code)
