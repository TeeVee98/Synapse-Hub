# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — HEAL Package (tools.heal)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.heal import agentless_patcher
from tools.heal import assertion_optimizer
from tools.heal import auto_heal
from tools.heal import auto_heal_reflexion
from tools.heal import ci_healing_hook
from tools.heal import heal_pr_automator
from tools.heal import heuristic_locator_matcher
from tools.heal import live_visual_healer
from tools.heal import lookup_xpath
from tools.heal import reversible_sandbox
from tools.heal import ast_assertion_optimizer
from tools.heal import visual_som_helper

# Backward compatibility alias
textgrad_mutation_optimizer = ast_assertion_optimizer
from tools.core import cache_resolver  # noqa: F401

__all__ = [
    "agentless_patcher",
    "assertion_optimizer",
    "ast_assertion_optimizer",
    "auto_heal",
    "auto_heal_reflexion",
    "ci_healing_hook",
    "heal_pr_automator",
    "heuristic_locator_matcher",
    "live_visual_healer",
    "lookup_xpath",
    "reversible_sandbox",
    "textgrad_mutation_optimizer",
    "visual_som_helper"
]
