# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — REPORT Package (tools.report)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.report import bug_reporter
from tools.report import coverage_reporter
from tools.report import generate_allure_report
from tools.report import generate_sbom
from tools.report import generate_test_reports
from tools.report import generate_tool_catalog
from tools.report import output_formatter
from tools.report import pinpoint_failure
from tools.report import telemetry_correlator
from tools.report import trend_analytics

__all__ = [
    "bug_reporter",
    "coverage_reporter",
    "generate_allure_report",
    "generate_sbom",
    "generate_test_reports",
    "generate_tool_catalog",
    "output_formatter",
    "pinpoint_failure",
    "telemetry_correlator",
    "trend_analytics"
]
