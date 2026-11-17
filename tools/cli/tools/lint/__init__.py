# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — Static Quality & Policy Sentinels (tools.lint)
-----------------------------------------------------------
Domain package grouping all static code defect, encoding, license,
and AI documentation drift verification tools.
"""

from tools import (
    author_integrity,
    check_version_sync,
    git_pre_commit_guard,
    infer_linter,
    lint_ai_docs,
    skill_collision_guard,
    skillspector,
    spec_drift_sentinel,
    validate_groovy_scripts,
)

__all__ = [
    "author_integrity",
    "check_version_sync",
    "git_pre_commit_guard",
    "infer_linter",
    "lint_ai_docs",
    "skill_collision_guard",
    "skillspector",
    "spec_drift_sentinel",
    "validate_groovy_scripts",
]
