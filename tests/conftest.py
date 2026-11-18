#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/conftest.py
-----------------
Pytest test harness configuration for Synapse Hub test suites.
Guarantees deterministic hermetic test execution with English fallback.
Bootstraps all 13 modular domain packages in tools/ into sys.path.
"""

import os
import sys

# Enforce deterministic English output during test execution across all environments
os.environ.setdefault("SYNAPSE_LANG", "en")

# Canonical sys.path bootstrapping for modular domain architecture
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS_DIR = os.path.join(_REPO_ROOT, "tools")
_DOMAINS = [
    "core", "lint", "heal", "context", "security", "api", "perf",
    "design", "report", "transpiler", "orchestration", "mcp", "contrib"
]
for _d in _DOMAINS:
    _dp = os.path.join(_TOOLS_DIR, _d)
    if _dp not in sys.path:
        sys.path.insert(0, _dp)

if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
