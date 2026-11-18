# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — SECURITY Package (tools.security)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.security import asvs_auditor
from tools.security import cvss_calculator
from tools.security import pentest_scope_guard
from tools.security import regulatory_compliance
from tools.security import safety_firewall
from tools.security import security_coverage_ledger
from tools.security import security_scanner
from tools.contrib import wcag_audit

__all__ = [
    "asvs_auditor",
    "cvss_calculator",
    "pentest_scope_guard",
    "regulatory_compliance",
    "safety_firewall",
    "security_coverage_ledger",
    "security_scanner",
    "wcag_audit",
]
