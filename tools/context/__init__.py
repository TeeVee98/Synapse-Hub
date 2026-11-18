# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — CONTEXT Package (tools.context)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.context import ast_cache
from tools.context import benchmark_swarm_context
from tools.context import context_slicer
from tools.context import lookup_tc
from tools.context import token_telemetry
from tools.context import trace_data_flow
from tools.core import count_tokens
from tools.core import distill_log
from tools.core import repo_map
from tools.core import rule_harvester

__all__ = [
    "ast_cache",
    "benchmark_swarm_context",
    "context_slicer",
    "lookup_tc",
    "token_telemetry",
    "trace_data_flow",
    "count_tokens",
    "distill_log",
    "repo_map",
    "rule_harvester",
]
