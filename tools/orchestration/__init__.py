# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — ORCHESTRATION Package (tools.orchestration)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.orchestration import autogen_qa_broker
from tools.orchestration import browsergym_eval
from tools.orchestration import typed_prompt_signatures
from tools.orchestration import goldfish_review
from tools.orchestration import matrix_sharder
from tools.orchestration import qa_event_stream
from tools.orchestration import runaway_stopper
from tools.orchestration import senior_code_review
from tools.orchestration import swe_qa_aci
from tools.orchestration import synapse_doctor
from tools.orchestration import synapse_observer
from tools.orchestration import synapse_qa_bench
from tools.orchestration import tot_exploratory_tester

# Backward compatibility alias
dspy_qa_signatures = typed_prompt_signatures

__all__ = [
    "autogen_qa_broker",
    "browsergym_eval",
    "typed_prompt_signatures",
    "dspy_qa_signatures",
    "goldfish_review",
    "matrix_sharder",
    "qa_event_stream",
    "runaway_stopper",
    "senior_code_review",
    "swe_qa_aci",
    "synapse_doctor",
    "synapse_observer",
    "synapse_qa_bench",
    "tot_exploratory_tester"
]
