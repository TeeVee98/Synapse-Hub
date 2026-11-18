# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — API Package (tools.api)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.api import _openapi_parser
from tools.api import api_drift_sentinel
from tools.api import api_fuzzer
from tools.api import contract_validator
from tools.api import e2e_flow_prober
from tools.api import fuzz_payloads
from tools.api import generate_api_matrix
from tools.api import network_mock_shield
from tools.api import pairwise_generator
from tools.api import spec_drift_sentinel
from tools.api import vcr_cassette_guard

__all__ = [
    "_openapi_parser",
    "api_drift_sentinel",
    "api_fuzzer",
    "contract_validator",
    "e2e_flow_prober",
    "fuzz_payloads",
    "generate_api_matrix",
    "network_mock_shield",
    "pairwise_generator",
    "spec_drift_sentinel",
    "vcr_cassette_guard"
]
