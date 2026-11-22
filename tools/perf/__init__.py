# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — PERF Package (tools.perf)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.perf import chaos_resilience_probe
from tools.perf import heap_leak_analyzer
from tools.perf import jtl_analyzer
from tools.perf import k6_analyzer
from tools.perf import mobile_resilience_sentinel
from tools.perf import newman_analyzer
from tools.perf import observability_tester
from tools.perf import slow_test_profiler
from tools.contrib import generate_jmx_plan  # noqa: F401
from tools.lint import flaky_detector  # noqa: F401
from tools.orchestration import matrix_sharder  # noqa: F401

__all__ = [
    "chaos_resilience_probe",
    "heap_leak_analyzer",
    "jtl_analyzer",
    "k6_analyzer",
    "mobile_resilience_sentinel",
    "newman_analyzer",
    "observability_tester",
    "slow_test_profiler"
]
