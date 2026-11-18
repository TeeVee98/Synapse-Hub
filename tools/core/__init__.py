# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub — CORE Package (tools.core)
"""

import os
import sys

_DOMAIN_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.dirname(_DOMAIN_DIR)
_REPO_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.core import analyze_project
from tools.core import author_integrity
from tools.core import bump_version
from tools.core import cache_resolver
from tools.core import check_env
from tools.core import check_version_sync
from tools.core import cli
from tools.core import config_decoupler
from tools.core import count_tokens
from tools.core import db_sandbox
from tools.core import debt_harvester
from tools.core import distill_log
from tools.core import distill_skill
from tools.core import fsm_enforcer
from tools.core import fsm_middleware
from tools.core import git_worktree_manager
from tools.core import hub_publisher
from tools.core import init_config
from tools.core import package_release
from tools.core import project_state
from tools.core import repo_map
from tools.core import rule_harvester
from tools.core import rules_router
from tools.core import session_vault
from tools.core import setup_project
from tools.core import skill_canonical_digest
from tools.core import skill_profiles
from tools.core import skill_vault
from tools.core import skillspector
from tools.core import sync_agent_rules
from tools.core import sync_skills_manifest
from tools.core import task_memory_manager
from tools.core import test_impact
from tools.core import test_memory_os
from tools.core import validate_host_interop
from tools.core import verify_all
from tools.core import watch_mode
from tools.core import cli_runtime
from tools.core import process_supervisor
from tools.core import file_lock
from tools.core import telemetry
from tools.core import circuit_breaker
from tools.core import memory_bus
from tools.core import adapters
from tools.core import i18n


__all__ = [
    "analyze_project",
    "author_integrity",
    "bump_version",
    "cache_resolver",
    "check_env",
    "check_version_sync",
    "cli",
    "config_decoupler",
    "count_tokens",
    "db_sandbox",
    "debt_harvester",
    "distill_log",
    "distill_skill",
    "fsm_enforcer",
    "fsm_middleware",
    "git_worktree_manager",
    "hub_publisher",
    "init_config",
    "package_release",
    "project_state",
    "repo_map",
    "rule_harvester",
    "rules_router",
    "session_vault",
    "setup_project",
    "skill_canonical_digest",
    "skill_profiles",
    "skill_vault",
    "skillspector",
    "sync_agent_rules",
    "sync_skills_manifest",
    "task_memory_manager",
    "test_impact",
    "test_memory_os",
    "validate_host_interop",
    "verify_all",
    "watch_mode",
    "cli_runtime",
    "process_supervisor",
    "file_lock",
    "telemetry",
    "circuit_breaker",
    "memory_bus",
    "adapters",
    "i18n"
]
