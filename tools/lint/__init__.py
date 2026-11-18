# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — LINT Package (tools.lint)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.lint import agent_canary
from tools.lint import ai_eval_sentinel
from tools.lint import flaky_detector
from tools.lint import git_pre_commit_guard
from tools.lint import humanize_linter
from tools.lint import infer_linter
from tools.lint import lint_ai_docs
from tools.lint import micro_mutator
from tools.lint import mipro_assertion_tuner
from tools.lint import pre_bash_guard
from tools.lint import pre_push_guard
from tools.lint import skill_collision_guard
from tools.lint import update_sentinel
from tools.lint import validate_groovy_scripts
from tools.lint import validate_skills_schema

__all__ = [
    "agent_canary",
    "ai_eval_sentinel",
    "flaky_detector",
    "git_pre_commit_guard",
    "humanize_linter",
    "infer_linter",
    "lint_ai_docs",
    "micro_mutator",
    "mipro_assertion_tuner",
    "pre_bash_guard",
    "pre_push_guard",
    "skill_collision_guard",
    "update_sentinel",
    "validate_groovy_scripts",
    "validate_skills_schema"
]
