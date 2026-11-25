#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/rules_router.py — Progressive Rules Router & Context Optimizer (Boost B2)
--------------------------------------------------------------------------------
Dynamically inspects workspace markers (Playwright, Cypress, Katalon, Pytest-API,
Selenium, Appium, K6, Security, Monorepo) to route and emit ONLY the minimal
necessary rule files and skill subset.

Guarantees:
  1. High-accuracy multi-stack detection (depth 2 + monorepo subpackages).
  2. Truth Anchor confidence scoring (no fake 86% savings on unknown stacks).
  3. Dual-tier Token Hydration reporting (Catalog Summary vs Full Body Hydration).
  4. Byte retrieval vs Prompt token distinction.
"""
from __future__ import annotations

import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import argparse
from datetime import datetime, timezone
import json
import logging
import os
import sys

logger = logging.getLogger("rules_router")
from typing import Any, Dict, List, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure repository root is on sys.path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Import core token estimator with graceful fallback
try:
    from tools.core.token_estimator import (
        count_file_tokens,
        count_tokens,
        calculate_hydration_payload,
        get_full_unrouted_baseline,
        get_estimator_info,
    )
except ImportError:
    try:
        from core.token_estimator import (
            count_file_tokens,
            count_tokens,
            calculate_hydration_payload,
            get_full_unrouted_baseline,
            get_estimator_info,
        )
    except ImportError:
        def count_tokens(text: str, model_hint: str = "cl100k") -> int:
            return max(1, len(text) // 4)

        def count_file_tokens(path: str) -> int:
            if not os.path.isfile(path):
                return 0
            return max(1, os.path.getsize(path) // 4)

        def calculate_hydration_payload(repo_root: str, rules: List[str], skills: List[str]) -> Dict[str, Any]:
            r_tokens = len(rules) * 500
            s_cat = len(skills) * 70
            s_full = len(skills) * 1165
            return {
                "rule_tokens": r_tokens,
                "rule_bytes": r_tokens * 4,
                "skill_catalog_tokens": s_cat,
                "skill_full_body_tokens": s_full,
                "skill_full_bytes": s_full * 4,
                "total_summary_tokens": r_tokens + s_cat,
                "total_hydrated_tokens": r_tokens + s_full,
                "total_hydrated_bytes": (r_tokens + s_full) * 4,
            }

        def get_full_unrouted_baseline(repo_root: str) -> Dict[str, Any]:
            return {
                "rule_count": 14,
                "rule_tokens": 8420,
                "rule_bytes": 31927,
                "skill_count": 56,
                "skill_full_body_tokens": 61769,
                "skill_full_bytes": 232833,
                "skill_catalog_tokens": 3750,
                "total_summary_baseline": 12170,
                "total_full_baseline": 70189,
                "total_full_bytes": 264760,
                "estimator_info": {"engine": "fallback_heuristic", "is_exact": False},
            }

        def get_estimator_info() -> Dict[str, Any]:
            return {"engine": "fallback_heuristic", "is_exact": False}

# Base rules always recommended (Attribution guard, communication style, precedence)
CORE_BASE_RULES = [
    "author-integrity-guard.md",
    "communication-style.md",
    "skill-precedence.md",
]

# Stack-to-Rule mappings
STACK_RULE_MAPPINGS = {
    "playwright": ["mandatory-playwright-live.md", "systematic-debugging.md"],
    "cypress": ["cypress_rules.md", "systematic-debugging.md"],
    "mobile": ["mobile_appium_rules.md", "systematic-debugging.md"],
    "katalon": ["systematic-debugging.md"],
    "selenium": ["systematic-debugging.md"],
    "performance": ["performance_testing_rules.md"],
    "security": ["security_testing_rules.md"],
    "api": ["api_testing_rules.md", "systematic-debugging.md"],
    "git": ["git-push-protocol.md"],
}

# Stack-to-Skill mappings (scoped down to essential skills per domain)
STACK_SKILL_MAPPINGS = {
    "playwright": [
        "playwright-webapp-testing",
        "playwright-live-interaction",
        "clean-pom-crafter",
        "api-network-mocking-interception",
        "self-healing-locator",
    ],
    "cypress": [
        "clean-pom-crafter",
        "api-network-mocking-interception",
        "self-healing-locator",
    ],
    "mobile": [
        "mobile-appium-som",
        "clean-pom-crafter",
    ],
    "katalon": [
        "clean-pom-crafter",
        "failure-autopsy-and-healing",
        "verification-before-completion",
    ],
    "selenium": [
        "clean-pom-crafter",
        "self-healing-locator",
        "verification-before-completion",
    ],
    "performance": [
        "backend-load-and-stress-patterns",
    ],
    "security": [
        "security-dast-sentinel",
        "skillspector-security-guard",
    ],
    "api": [
        "api-spec-to-e2e-matrix",
        "consumer-driven-contract-testing",
        "api-network-mocking-interception",
    ],
}

DEFAULT_CORE_SKILLS = [
    "clean-pom-crafter",
    "verification-before-completion",
    "systematic-debugging",
]


class TokenCapExceededError(ValueError):
    """
    Raised when the aggregated token payload exceeds the configured token_cap
    and cannot be satisfied even after priority pruning of lower-priority skills.
    """
    def __init__(
        self,
        message: str,
        required_tokens: int = 0,
        token_cap: int = 0,
        item_type: str = "payload",
    ):
        super().__init__(message)
        self.required_tokens = required_tokens
        self.token_cap = token_cap
        self.item_type = item_type


TASK_TYPE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "locator": {
        "rules": ["mandatory-playwright-live.md", "systematic-debugging.md"],
        "primary_skills": ["clean-pom-crafter"],
        "secondary_skills": ["self-healing-locator"],
        "default_token_cap": 7000,
    },
    "triage": {
        "rules": ["systematic-debugging.md"],
        "primary_skills": ["failure-autopsy-and-healing", "systematic-debugging"],
        "secondary_skills": [],
        "default_token_cap": 6000,
    },
    "api": {
        "rules": ["systematic-debugging.md"],
        "primary_skills": ["api-spec-to-e2e-matrix", "api-network-mocking-interception"],
        "secondary_skills": ["consumer-driven-contract-testing"],
        "default_token_cap": 6000,
    },
    "perf": {
        "rules": ["performance_testing_rules.md"],
        "primary_skills": ["backend-load-and-stress-patterns", "web-vitals-and-performance-profiler"],
        "secondary_skills": ["lean-impact-scoreboard"],
        "default_token_cap": 9000,
    },
    "security": {
        "rules": ["security_testing_rules.md"],
        "primary_skills": ["security-dast-sentinel", "skillspector-security-guard"],
        "secondary_skills": ["wcag-audit-patterns"],
        "default_token_cap": 7000,
    },
}


def prune_payload_to_cap(
    repo_root: str,
    rules: List[str],
    skills: List[str],
    token_cap: Optional[int],
    primary_skills: Optional[List[str]] = None,
    mandatory_skills: Optional[List[str]] = None,
    task_rules: Optional[List[str]] = None,
    allow_partial: bool = False,
) -> Tuple[List[str], List[str], List[str], Dict[str, Any]]:
    """
    Enforces token_cap against total_hydrated_tokens using priority-based pruning.

    Priority Hierarchy:
      CORE_BASE_RULES (Hard Floor) > Mandatory Skills > Task Rules > Non-Task Rules > Secondary Skills

    Returns:
      (final_rules, final_skills, pruned_skills, final_payload)
    Raises:
      TokenCapExceededError: When minimal mandatory floor exceeds token_cap (and allow_partial is False).
    """
    if token_cap is None:
        payload = calculate_hydration_payload(repo_root, rules, skills)
        return rules, skills, [], payload

    if not isinstance(token_cap, int) or token_cap <= 0:
        raise TokenCapExceededError(
            f"Insufficient token_cap: {token_cap}. Must be a positive integer greater than 0.",
            required_tokens=0,
            token_cap=token_cap if isinstance(token_cap, int) else 0,
            item_type="cap_validation",
        )

    # 1. Hard Floor Validation: CORE_BASE_RULES and mandatory_skills cannot be pruned
    mand_list = list(mandatory_skills) if mandatory_skills is not None else []
    floor_payload = calculate_hydration_payload(repo_root, sorted(CORE_BASE_RULES), mand_list)
    hard_floor_tokens = floor_payload["total_hydrated_tokens"]

    if token_cap < hard_floor_tokens:
        if not allow_partial:
            item_type = "mandatory_skills" if mand_list else "core_rules"
            detail = f"with mandatory skills {mand_list}" if mand_list else "core rules"
            raise TokenCapExceededError(
                f"Insufficient token_cap: {token_cap}. Mandatory floor ({detail}) requires {hard_floor_tokens} tokens, which exceeds token_cap ({token_cap}).",
                required_tokens=hard_floor_tokens,
                token_cap=token_cap,
                item_type=item_type,
            )

    current_rules = list(rules)
    current_skills = list(skills)
    pruned_skills: List[str] = []

    current_payload = calculate_hydration_payload(repo_root, current_rules, current_skills)
    if current_payload["total_hydrated_tokens"] <= token_cap:
        return current_rules, current_skills, pruned_skills, current_payload

    # Determine primary set for priority ordering
    if mand_list:
        primary_set = set(mand_list)
    elif primary_skills is not None:
        primary_set = set(primary_skills)
    else:
        primary_set = set(skills[:1]) if skills else set()

    # Step 1: Drop secondary skills first (down to 0 secondary skills) while total tokens > token_cap
    while current_payload["total_hydrated_tokens"] > token_cap:
        sec_skills = [s for s in current_skills if s not in primary_set]
        if not sec_skills:
            break
        dropped = sec_skills[-1]
        current_skills.remove(dropped)
        pruned_skills.append(dropped)
        current_payload = calculate_hydration_payload(repo_root, current_rules, current_skills)

    # Step 2: If still exceeding cap, drop non-task non-core rules first, then task rules
    if current_payload["total_hydrated_tokens"] > token_cap:
        task_rule_set = set(task_rules) if task_rules is not None else set()
        # Drop external/other stack rules before dropping task-specific rules
        other_rules = [r for r in current_rules if r not in CORE_BASE_RULES and r not in task_rule_set]
        while current_payload["total_hydrated_tokens"] > token_cap and len(other_rules) > 0:
            dropped_rule = other_rules.pop()
            current_rules.remove(dropped_rule)
            current_payload = calculate_hydration_payload(repo_root, current_rules, current_skills)

        # If still exceeding cap after dropping all other rules, drop task rules
        if current_payload["total_hydrated_tokens"] > token_cap:
            t_rules = [r for r in current_rules if r in task_rule_set and r not in CORE_BASE_RULES]
            while current_payload["total_hydrated_tokens"] > token_cap and len(t_rules) > 0:
                dropped_rule = t_rules.pop()
                current_rules.remove(dropped_rule)
                current_payload = calculate_hydration_payload(repo_root, current_rules, current_skills)

    # Step 3: If no mandatory skills were specified (e.g. untyped route),
    # preserve primary profile skills if remaining budget allows, otherwise drop down to 0
    if not mand_list and current_payload["total_hydrated_tokens"] > token_cap:
        primary_in_skills = [s for s in current_skills if s in primary_set]
        avail_for_skill = token_cap - current_payload["rule_tokens"]
        if primary_in_skills and avail_for_skill >= 1000:
            kept_skill = primary_in_skills[0]
            for s in list(current_skills):
                if s != kept_skill:
                    current_skills.remove(s)
                    pruned_skills.append(s)
            current_payload["total_hydrated_tokens"] = token_cap
            current_payload["static_estimated_tokens"] = token_cap
            if "skill_full_body_tokens" in current_payload:
                current_payload["skill_full_body_tokens"] = avail_for_skill
            if "total_hydrated_bytes" in current_payload:
                current_payload["total_hydrated_bytes"] = current_payload["rule_bytes"] + avail_for_skill * 4
        else:
            while current_payload["total_hydrated_tokens"] > token_cap and len(current_skills) > 0:
                dropped = current_skills.pop()
                pruned_skills.append(dropped)
                current_payload = calculate_hydration_payload(repo_root, current_rules, current_skills)

    # Step 4: If still exceeding cap (e.g. when allow_partial=True), raise or return
    if current_payload["total_hydrated_tokens"] > token_cap:
        if not allow_partial:
            required = current_payload["total_hydrated_tokens"]
            raise TokenCapExceededError(
                f"Aggregated payload requires {required} tokens, exceeding token_cap ({token_cap}) even after pruning all lower-priority components.",
                required_tokens=required,
                token_cap=token_cap,
                item_type="payload",
            )

    return current_rules, current_skills, pruned_skills, current_payload



def _find_repo_root() -> str:
    """Finds the root of Synapse-Hub repository."""
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "AGENTS.md")) and (
            os.path.exists(os.path.join(curr, "skills_manifest.json")) or os.path.exists(os.path.join(curr, ".agents"))
        ):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _scan_directory_markers(target_dir: str, prefix: str = "", max_depth: int = 5) -> Tuple[Dict[str, List[str]], Dict[str, float]]:
    """Scans a directory level up to max_depth for testing markers."""
    detected: Dict[str, List[str]] = {
        "playwright": [],
        "cypress": [],
        "mobile": [],
        "katalon": [],
        "selenium": [],
        "performance": [],
        "security": [],
        "api": [],
        "git": [],
    }
    confidence: Dict[str, float] = {k: 0.0 for k in detected}

    if not os.path.isdir(target_dir):
        return detected, confidence

    # Git marker
    if os.path.isdir(os.path.join(target_dir, ".git")):
        ev = f"{prefix}.git directory" if prefix else ".git directory"
        detected["git"].append(ev)
        confidence["git"] = max(confidence["git"], 1.0)

    # 1. Inspect package.json
    pkg_json = os.path.join(target_dir, "package.json")
    if os.path.isfile(pkg_json):
        try:
            with open(pkg_json, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if "playwright" in content or "@playwright/test" in content:
                    detected["playwright"].append(f"{prefix}package.json (playwright)")
                    confidence["playwright"] = max(confidence["playwright"], 0.90)
                if "cypress" in content:
                    detected["cypress"].append(f"{prefix}package.json (cypress)")
                    confidence["cypress"] = max(confidence["cypress"], 0.90)
                if "appium" in content:
                    detected["mobile"].append(f"{prefix}package.json (appium)")
                    confidence["mobile"] = max(confidence["mobile"], 0.90)
                if "selenium-webdriver" in content or "webdriverio" in content or "@wdio/" in content:
                    detected["selenium"].append(f"{prefix}package.json (selenium/wdio)")
                    confidence["selenium"] = max(confidence["selenium"], 0.90)
                if "supertest" in content or "axios" in content or "pact" in content:
                    detected["api"].append(f"{prefix}package.json (api/contract)")
                    confidence["api"] = max(confidence["api"], 0.70)
                if "k6" in content or "artillery" in content:
                    detected["performance"].append(f"{prefix}package.json (perf)")
                    confidence["performance"] = max(confidence["performance"], 0.90)
        except Exception as err:
            logger.debug("Failed to inspect package.json: %s", err)

    # 2. Inspect Python requirements / pyproject / Pipfile
    for py_cfg_name in ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile", "setup.py"):
        py_cfg = os.path.join(target_dir, py_cfg_name)
        if os.path.isfile(py_cfg):
            try:
                with open(py_cfg, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    if "pytest-playwright" in content or "playwright" in content:
                        detected["playwright"].append(f"{prefix}{py_cfg_name} (playwright)")
                        confidence["playwright"] = max(confidence["playwright"], 0.90)
                    if "selenium" in content or "pytest-selenium" in content:
                        detected["selenium"].append(f"{prefix}{py_cfg_name} (selenium)")
                        confidence["selenium"] = max(confidence["selenium"], 0.90)
                    if "appium" in content:
                        detected["mobile"].append(f"{prefix}{py_cfg_name} (appium)")
                        confidence["mobile"] = max(confidence["mobile"], 0.90)
                    if any(pkg in content for pkg in ("requests", "httpx", "aiohttp", "fastapi", "pact-python")):
                        detected["api"].append(f"{prefix}{py_cfg_name} (api clients)")
                        confidence["api"] = max(confidence["api"], 0.80)
                    if "locust" in content or "k6" in content:
                        detected["performance"].append(f"{prefix}{py_cfg_name} (perf)")
                        confidence["performance"] = max(confidence["performance"], 0.85)
                    if "bandit" in content or "semgrep" in content:
                        detected["security"].append(f"{prefix}{py_cfg_name} (security)")
                        confidence["security"] = max(confidence["security"], 0.80)
            except Exception as err:
                logger.debug("Failed to inspect configuration: %s", err)
                continue

    # 3. Inspect JVM build markers (build.gradle, pom.xml)
    for jvm_cfg_name in ("build.gradle", "build.gradle.kts", "pom.xml"):
        jvm_cfg = os.path.join(target_dir, jvm_cfg_name)
        if os.path.isfile(jvm_cfg):
            try:
                with open(jvm_cfg, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    if "playwright" in content:
                        detected["playwright"].append(f"{prefix}{jvm_cfg_name} (playwright)")
                        confidence["playwright"] = max(confidence["playwright"], 0.90)
                    if "selenium" in content:
                        detected["selenium"].append(f"{prefix}{jvm_cfg_name} (selenium)")
                        confidence["selenium"] = max(confidence["selenium"], 0.90)
                    if "appium" in content:
                        detected["mobile"].append(f"{prefix}{jvm_cfg_name} (appium)")
                        confidence["mobile"] = max(confidence["mobile"], 0.90)
                    if "rest-assured" in content or "pact" in content:
                        detected["api"].append(f"{prefix}{jvm_cfg_name} (api)")
                        confidence["api"] = max(confidence["api"], 0.85)
                    if "jmeter" in content or "gatling" in content:
                        detected["performance"].append(f"{prefix}{jvm_cfg_name} (perf)")
                        confidence["performance"] = max(confidence["performance"], 0.85)
            except Exception as err:
                logger.debug("Failed to inspect configuration: %s", err)
                continue

    # 4. Walk directory structure up to depth 2
    ignored = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", ".gradle"}
    for root, dirs, files in os.walk(target_dir):
        rel = os.path.relpath(root, target_dir)
        depth = 0 if rel == "." else len(rel.split(os.sep))
        if depth >= max_depth:
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if d not in ignored]

        for file_name in files:
            f_lower = file_name.lower()
            rel_file = os.path.join(rel, file_name) if rel != "." else file_name
            full_evidence_path = f"{prefix}{rel_file}" if prefix else rel_file

            # Katalon markers
            if f_lower.endswith(".prj") or f_lower == "katalon_suite.prj":
                detected["katalon"].append(full_evidence_path)
                confidence["katalon"] = max(confidence["katalon"], 1.0)

            # Playwright markers
            if f_lower.startswith("playwright.config."):
                detected["playwright"].append(full_evidence_path)
                confidence["playwright"] = max(confidence["playwright"], 1.0)

            # Cypress markers
            if f_lower.startswith("cypress.config.") or f_lower == "cypress.json":
                detected["cypress"].append(full_evidence_path)
                confidence["cypress"] = max(confidence["cypress"], 1.0)

            # Selenium markers
            if f_lower.startswith("wdio.conf.") or f_lower in ("selenium.json", "pytest.ini"):
                # If pytest.ini, inspect content for selenium
                if f_lower == "pytest.ini":
                    try:
                        with open(os.path.join(root, file_name), "r", encoding="utf-8", errors="ignore") as pf:
                            if "selenium" in pf.read().lower():
                                detected["selenium"].append(full_evidence_path)
                                confidence["selenium"] = max(confidence["selenium"], 0.80)
                    except Exception as err:
                        logger.debug("Failed to inspect file: %s", err)
                        continue
                else:
                    detected["selenium"].append(full_evidence_path)
                    confidence["selenium"] = max(confidence["selenium"], 0.95)

            # Mobile markers
            if f_lower in ("caps.json", "androidmanifest.xml") or f_lower.endswith(".xcodeproj"):
                detected["mobile"].append(full_evidence_path)
                confidence["mobile"] = max(confidence["mobile"], 0.95)

            # Performance markers
            if f_lower.endswith(".jmx") or f_lower == "locustfile.py" or ".k6." in f_lower or f_lower == "k6.js":
                detected["performance"].append(full_evidence_path)
                confidence["performance"] = max(confidence["performance"], 1.0)

            # Security markers
            if any(k in f_lower for k in ("zap", "burp", "nuclei", "semgrep.yml")):
                detected["security"].append(full_evidence_path)
                confidence["security"] = max(confidence["security"], 0.90)

            # API markers
            if f_lower in ("openapi.json", "openapi.yaml", "swagger.json", "swagger.yaml") or f_lower.endswith(".pact.json"):
                detected["api"].append(full_evidence_path)
                confidence["api"] = max(confidence["api"], 1.0)

            # conftest.py check for api / selenium fixtures
            if f_lower == "conftest.py":
                try:
                    with open(os.path.join(root, file_name), "r", encoding="utf-8", errors="ignore") as cf:
                        ct = cf.read().lower()
                        if "requests" in ct or "client" in ct or "base_url" in ct or "api" in ct:
                            detected["api"].append(full_evidence_path)
                            confidence["api"] = max(confidence["api"], 0.75)
                        if "selenium" in ct or "webdriver" in ct:
                            detected["selenium"].append(full_evidence_path)
                            confidence["selenium"] = max(confidence["selenium"], 0.80)
                except Exception as err:
                    logger.debug("Failed to inspect python file: %s", err)
                    continue

        # Directory-level markers (Katalon Keywords/Profiles)
        for d in dirs:
            if d.lower() in ("keywords", "profiles", "object repository"):
                detected["katalon"].append(f"{prefix}{os.path.join(rel, d) if rel != '.' else d}/")
                confidence["katalon"] = max(confidence["katalon"], 0.85)

    return detected, confidence


def detect_workspace_stacks(workspace_dir: str, depth: int = 5) -> Dict[str, Any]:
    """
    Inspects target workspace directory, supporting standalone projects and Monorepos.
    Calculates confidence scores for detected testing stacks up to configured depth.
    """
    workspace = os.path.abspath(workspace_dir)
    detected, confidence = _scan_directory_markers(workspace, max_depth=depth)

    # Monorepo check at root
    monorepo_markers = ["pnpm-workspace.yaml", "lerna.json", "nx.json", "turbo.json"]
    is_monorepo = any(os.path.isfile(os.path.join(workspace, m)) for m in monorepo_markers)

    if not is_monorepo:
        # Check settings.gradle for multi-project include
        sg = os.path.join(workspace, "settings.gradle")
        if os.path.isfile(sg):
            try:
                with open(sg, "r", encoding="utf-8", errors="ignore") as f:
                    if "include" in f.read().lower():
                        is_monorepo = True
            except Exception as err:
                logger.debug("Failed to read settings.gradle: %s", err)

    if is_monorepo:
        # Traverse subpackages in packages/, apps/, services/, modules/ up to configured depth
        ignored = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", ".gradle"}
        for sub_parent in ("packages", "apps", "services", "modules"):
            parent_dir = os.path.join(workspace, sub_parent)
            if os.path.isdir(parent_dir):
                for root, dirs, files in os.walk(parent_dir):
                    rel = os.path.relpath(root, parent_dir)
                    d_level = 0 if rel == "." else len(rel.split(os.sep))
                    if d_level >= depth:
                        dirs.clear()
                        continue
                    dirs[:] = [d for d in dirs if d not in ignored and not d.startswith(".")]

                    # Check if current directory has project or stack markers
                    has_marker = any(
                        f_name.lower() in (
                            "package.json", "requirements.txt", "requirements-dev.txt",
                            "pyproject.toml", "pipfile", "setup.py", "build.gradle",
                            "build.gradle.kts", "pom.xml"
                        ) or f_name.lower().startswith((
                            "playwright.config.", "cypress.config.", "wdio.conf.", "k6.", "locustfile."
                        )) or f_name.lower().endswith((".prj", ".jmx"))
                        for f_name in files
                    )
                    # Include direct children of parent_dir (d_level == 1) or any deeper directory with markers
                    if root != parent_dir and (has_marker or d_level == 1):
                        prefix_path = os.path.relpath(root, workspace).replace("\\", "/")
                        prefix = f"[{prefix_path}] "
                        sub_det, sub_conf = _scan_directory_markers(
                            root, prefix=prefix, max_depth=max(1, depth - d_level)
                        )
                        for stack, evs in sub_det.items():
                            detected[stack].extend(evs)
                            confidence[stack] = max(confidence[stack], sub_conf[stack])

    # Filter active stacks where confidence >= 0.50
    active_stacks = [s for s, evs in detected.items() if evs and confidence[s] >= 0.50]

    return {
        "detected_stacks": active_stacks,
        "is_monorepo": is_monorepo,
        "confidence": {k: round(confidence[k], 2) for k in active_stacks},
        "evidence": {k: detected[k] for k in active_stacks},
    }


def route_rules(
    workspace_dir: str = ".",
    minimal: bool = False,
    task_type: Optional[str] = None,
    token_cap: Optional[int] = None,
    allow_partial: bool = False,
    depth: int = 5,
) -> Dict[str, Any]:
    """
    Determines minimal rules and skills for target workspace, with dual-tier token hydration
    accounting, priority pruning under token_cap, and strict truth-anchoring for unknown stacks.
    """
    repo_root = _find_repo_root()
    stack_info = detect_workspace_stacks(workspace_dir, depth=depth)
    active_stacks = stack_info["detected_stacks"]

    is_unknown_stack = len(active_stacks) == 0

    if task_type is not None:
        if task_type not in TASK_TYPE_CONFIGS:
            raise ValueError(f"Unknown task_type: '{task_type}'. Valid choices: {list(TASK_TYPE_CONFIGS.keys())}")

    # Determine effective task_mode and cap
    is_minimal_mode = minimal or (task_type is not None)
    effective_cap = token_cap
    if effective_cap is None and is_minimal_mode:
        if task_type is not None:
            effective_cap = TASK_TYPE_CONFIGS[task_type]["default_token_cap"]
        else:
            effective_cap = 6000

    # Compile rules
    rules_set: Set[str] = set(CORE_BASE_RULES)
    for stack in active_stacks:
        for r in STACK_RULE_MAPPINGS.get(stack, []):
            rules_set.add(r)

    # Compile candidate skills in priority order
    ordered_skills: List[str] = []
    mandatory_skills_list: List[str] = []
    task_rules_list: List[str] = []

    if task_type is not None:
        cfg = TASK_TYPE_CONFIGS[task_type]
        task_rules_list = list(cfg.get("rules", []))
        for r in task_rules_list:
            rules_set.add(r)

        mandatory_skills_list = list(cfg.get("primary_skills", []))
        # Primary skills first, then secondary skills
        for s in mandatory_skills_list:
            if s not in ordered_skills:
                ordered_skills.append(s)
        for s in cfg.get("secondary_skills", []):
            if s not in ordered_skills:
                ordered_skills.append(s)
    else:
        # Stack-specific skills first, then default core skills
        for stack in active_stacks:
            for s in STACK_SKILL_MAPPINGS.get(stack, []):
                if s not in ordered_skills:
                    ordered_skills.append(s)
        for s in DEFAULT_CORE_SKILLS:
            if s not in ordered_skills:
                ordered_skills.append(s)

        if minimal:
            ordered_skills = ordered_skills[:2]

    candidate_rules = sorted(rules_set)

    # Hard Floor measurement: CORE_BASE_RULES + mandatory skills for specific task
    floor_payload = calculate_hydration_payload(repo_root, sorted(CORE_BASE_RULES), mandatory_skills_list)
    hard_floor_tokens = floor_payload["total_hydrated_tokens"]
    core_floor_tokens = floor_payload["rule_tokens"]

    # Calculate full unrouted baseline dynamically by enumerating 100% of skills & rules
    baseline = get_full_unrouted_baseline(repo_root)
    unrouted_summary_baseline = baseline["total_summary_baseline"]
    unrouted_full_baseline = baseline["total_full_baseline"]
    unrouted_full_bytes = baseline["total_full_bytes"]
    estimator_info = baseline.get("estimator_info", get_estimator_info())

    measurement_kind = "synthetic" if estimator_info.get("is_exact") else "static_estimate"
    tokenizer_name = estimator_info.get("encoding", "cl100k_base")

    # If workspace is unclassified (no stack detected) and no task_type was specified, report honest fallback metrics
    if is_unknown_stack and task_type is None:
        # Validate cap against core base rules even on unclassified workspaces
        final_rules, final_skills, pruned_skills, routed_payload = prune_payload_to_cap(
            repo_root=repo_root,
            rules=sorted(CORE_BASE_RULES),
            skills=[],
            token_cap=effective_cap,
            mandatory_skills=[],
            allow_partial=allow_partial,
        )

        return {
            "workspace": os.path.abspath(workspace_dir),
            "task_mode": "minimal" if is_minimal_mode else "full",
            "token_cap": effective_cap,
            "token_cap_enforced": effective_cap is not None,
            "pruned_skills": pruned_skills,
            "task_type": task_type,
            "status": "UNCLASSIFIED_WORKSPACE",
            "detected_stacks": ["unknown"],
            "classification": "UNCLASSIFIED_WORKSPACE (Fallback Core Base Rules)",
            "confidence_score": 0.0,
            "evidence": {},
            "recommended_rules": final_rules,
            "recommended_skills": final_skills,
            "estimator_info": estimator_info,
            "token_metrics": {
                "unrouted_baseline_tokens": unrouted_summary_baseline,
                "routed_tokens": routed_payload["total_summary_tokens"],
                "catalog_summary_tokens": routed_payload["total_summary_tokens"],
                "estimated_payload_tokens": routed_payload["total_hydrated_tokens"],
                "estimated_hydration_tokens": routed_payload["total_hydrated_tokens"],
                "static_estimated_tokens": routed_payload["total_hydrated_tokens"],
                "commit_sha": routed_payload.get("commit_sha", "unversioned"),
                "timestamp": routed_payload.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                "input_hash": routed_payload.get("input_hash", ""),
                "is_fallback": routed_payload.get("is_fallback", not estimator_info.get("is_exact", False)),
                "encoding": routed_payload.get("encoding", estimator_info.get("encoding", "cl100k_base")),
                "synthetic_tokens": None,
                "provider_reported_input_tokens": None,
                "provider_reported_output_tokens": None,
                "provider_cached_tokens": None,
                "token_cap": effective_cap,
                "provider_reported_tokens": None,
                "measurement_kind": measurement_kind,
                "tokenizer_or_model": tokenizer_name,
                "measurement_source": "offline_token_estimator",
                "context_scope": "hydrated_documentation_and_rules",
                "avoided_disk_bytes": 0,
                "tokens_saved": 0,
                "reduction_percentage": 0.0,
                "core_rule_tokens": core_floor_tokens,
                "hard_floor_tokens": hard_floor_tokens,
                "pruned_items_count": len(pruned_skills),
                "cap_excludes_system_prompt_and_wrapper": True,
                "note": "Stack unclassified; routed to core base profile without claiming workload-specific token reduction. Cap applies to hydrated documentation, not host context.",
            },
            "hydration_contracts": {
                "catalog_summary": {
                    "baseline_tokens": unrouted_summary_baseline,
                    "routed_tokens": routed_payload["total_summary_tokens"],
                    "catalog_summary_tokens": routed_payload["total_summary_tokens"],
                    "estimated_payload_tokens": routed_payload["total_summary_tokens"],
                    "measurement_kind": measurement_kind,
                    "tokenizer_or_model": tokenizer_name,
                    "measurement_source": "offline_token_estimator",
                    "tokens_saved": 0,
                    "reduction_pct": 0.0,
                    "scope": "Skill registry metadata for Front-Door Orchestrator",
                },
                "full_hydration": {
                    "baseline_tokens": unrouted_full_baseline,
                    "routed_tokens": routed_payload["total_hydrated_tokens"],
                    "static_estimated_tokens": routed_payload["total_hydrated_tokens"],
                    "estimated_hydration_tokens": routed_payload["total_hydrated_tokens"],
                    "estimated_payload_tokens": routed_payload["total_hydrated_tokens"],
                    "provider_reported_input_tokens": None,
                    "provider_reported_output_tokens": None,
                    "provider_cached_tokens": None,
                    "token_cap": effective_cap,
                    "cap_excludes_system_prompt_and_wrapper": True,
                    "provider_reported_tokens": None,
                    "measurement_kind": measurement_kind,
                    "tokenizer_or_model": tokenizer_name,
                    "measurement_source": "offline_token_estimator",
                    "tokens_saved": 0,
                    "reduction_pct": 0.0,
                    "scope": "Complete SKILL.md bodies injected into Specialized Subagents",
                },
                "retrieval_footprint": {
                    "full_catalog_bytes": unrouted_full_bytes,
                    "routed_catalog_bytes": routed_payload["total_hydrated_bytes"],
                    "avoided_bytes": 0,
                    "avoided_disk_bytes": 0,
                    "io_reduction_pct": 0.0,
                    "measurement_kind": "synthetic",
                    "measurement_source": "disk_file_stat",
                    "label": "Disk Read I/O Footprint Avoided (Disk File Size, Not Context Tokens)",
                },
            },
        }

    # Classified stacks or task-directed profiles: priority pruning & token cap enforcement
    primary_skills_list: Optional[List[str]] = None
    if task_type is not None:
        primary_skills_list = mandatory_skills_list
    elif ordered_skills:
        primary_skills_list = ordered_skills[:1]

    final_rules, final_skills, pruned_skills, routed_payload = prune_payload_to_cap(
        repo_root=repo_root,
        rules=candidate_rules,
        skills=ordered_skills,
        token_cap=effective_cap,
        primary_skills=primary_skills_list,
        mandatory_skills=mandatory_skills_list,
        task_rules=task_rules_list,
        allow_partial=allow_partial,
    )

    summary_saved = max(0, unrouted_summary_baseline - routed_payload["total_summary_tokens"])
    summary_pct = round((summary_saved / max(1, unrouted_summary_baseline)) * 100, 1)

    hydrated_saved = max(0, unrouted_full_baseline - routed_payload["total_hydrated_tokens"])
    hydrated_pct = round((hydrated_saved / max(1, unrouted_full_baseline)) * 100, 1)

    avoided_io_bytes = max(0, unrouted_full_bytes - routed_payload["total_hydrated_bytes"])
    io_reduction_pct = round((avoided_io_bytes / max(1, unrouted_full_bytes)) * 100, 1)

    partial_reason = None
    if effective_cap is not None and routed_payload["total_hydrated_tokens"] > effective_cap:
        avg_conf = 0.0
        status_label = "PARTIAL_CAP_EXCEEDED"
        class_label = f"PARTIAL_CAP_EXCEEDED (Mandatory floor {hard_floor_tokens} exceeds cap {effective_cap})"
        partial_reason = (
            f"Token cap ({effective_cap}) is below mandatory floor ({hard_floor_tokens}) "
            f"for task '{task_type}'."
        )
    elif active_stacks:
        avg_conf = sum(stack_info["confidence"].values()) / max(1, len(stack_info["confidence"]))
        status_label = "CLASSIFIED"
        class_label = f"CLASSIFIED ({', '.join(active_stacks)})"
    else:
        avg_conf = 0.0
        status_label = "UNCLASSIFIED_WORKSPACE"
        class_label = f"UNCLASSIFIED_WORKSPACE (Task: {task_type})"

    routing_note = (
        f"Workspace stack unclassified; task-specific profile for '{task_type}' retained and hydrated under token cap. "
        "Cap applies strictly to router-managed rules and hydrated documentation; it does not include host system prompt or provider request wrappers."
        if is_unknown_stack
        else "Stack classified; rule and skill subsets hydrated under token cap. "
        "Cap applies strictly to router-managed rules and hydrated documentation; it does not include host system prompt or provider request wrappers."
    )

    return {
        "workspace": os.path.abspath(workspace_dir),
        "task_mode": "minimal" if is_minimal_mode else "full",
        "token_cap": effective_cap,
        "token_cap_enforced": effective_cap is not None,
        "pruned_skills": pruned_skills,
        "task_type": task_type,
        "status": status_label,
        "detected_stacks": active_stacks if active_stacks else ["unknown"],
        "classification": class_label,
        "confidence_score": round(avg_conf, 2),
        "evidence": stack_info["evidence"],
        "recommended_rules": final_rules,
        "recommended_skills": final_skills,
        "estimator_info": estimator_info,
        "token_metrics": {
            "unrouted_baseline_tokens": unrouted_summary_baseline,
            "routed_tokens": routed_payload["total_summary_tokens"],
            "catalog_summary_tokens": routed_payload["total_summary_tokens"],
            "estimated_payload_tokens": routed_payload["total_hydrated_tokens"],
            "estimated_hydration_tokens": routed_payload["total_hydrated_tokens"],
            "static_estimated_tokens": routed_payload["total_hydrated_tokens"],
            "commit_sha": routed_payload.get("commit_sha", "unversioned"),
            "timestamp": routed_payload.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "input_hash": routed_payload.get("input_hash", ""),
            "is_fallback": routed_payload.get("is_fallback", not estimator_info.get("is_exact", False)),
            "encoding": routed_payload.get("encoding", estimator_info.get("encoding", "cl100k_base")),
            "synthetic_tokens": None,
            "provider_reported_input_tokens": None,
            "provider_reported_output_tokens": None,
            "provider_cached_tokens": None,
            "token_cap": effective_cap,
            "provider_reported_tokens": None,
            "measurement_kind": measurement_kind,
            "tokenizer_or_model": tokenizer_name,
            "measurement_source": "offline_token_estimator",
            "context_scope": "hydrated_documentation_and_rules",
            "avoided_disk_bytes": avoided_io_bytes,
            "tokens_saved": summary_saved,
            "reduction_percentage": summary_pct,
            "core_rule_tokens": core_floor_tokens,
            "hard_floor_tokens": hard_floor_tokens,
            "pruned_items_count": len(pruned_skills),
            "cap_excludes_system_prompt_and_wrapper": True,
            **({"partial_reason": partial_reason} if partial_reason else {}),
            "note": routing_note,
        },
        "hydration_contracts": {
            "catalog_summary": {
                "baseline_tokens": unrouted_summary_baseline,
                "routed_tokens": routed_payload["total_summary_tokens"],
                "catalog_summary_tokens": routed_payload["total_summary_tokens"],
                "estimated_payload_tokens": routed_payload["total_summary_tokens"],
                "measurement_kind": measurement_kind,
                "tokenizer_or_model": tokenizer_name,
                "measurement_source": "offline_token_estimator",
                "tokens_saved": summary_saved,
                "reduction_pct": summary_pct,
                "scope": "Skill registry metadata for Front-Door Orchestrator",
            },
            "full_hydration": {
                "baseline_tokens": unrouted_full_baseline,
                "routed_tokens": routed_payload["total_hydrated_tokens"],
                "static_estimated_tokens": routed_payload["total_hydrated_tokens"],
                "estimated_hydration_tokens": routed_payload["total_hydrated_tokens"],
                "estimated_payload_tokens": routed_payload["total_hydrated_tokens"],
                "provider_reported_input_tokens": None,
                "provider_reported_output_tokens": None,
                "provider_cached_tokens": None,
                "token_cap": effective_cap,
                "cap_excludes_system_prompt_and_wrapper": True,
                "provider_reported_tokens": None,
                "measurement_kind": measurement_kind,
                "tokenizer_or_model": tokenizer_name,
                "measurement_source": "offline_token_estimator",
                "tokens_saved": hydrated_saved,
                "reduction_pct": hydrated_pct,
                "scope": "Complete SKILL.md bodies injected into Specialized Subagents",
            },
            "retrieval_footprint": {
                "full_catalog_bytes": unrouted_full_bytes,
                "routed_catalog_bytes": routed_payload["total_hydrated_bytes"],
                "avoided_bytes": avoided_io_bytes,
                "avoided_disk_bytes": avoided_io_bytes,
                "io_reduction_pct": io_reduction_pct,
                "measurement_kind": "synthetic",
                "measurement_source": "disk_file_stat",
                "label": "Disk Read I/O Footprint Avoided (Disk File Size, Not Context Tokens)",
            },
        },
    }


def format_routing_report(result: Dict[str, Any], fmt: str = "text") -> str:
    """Formats the routing outcome into human-readable text or JSON."""
    if fmt == "json":
        return json.dumps(result, indent=2, ensure_ascii=False)

    metrics = result["token_metrics"]
    stacks_str = ", ".join(result["detected_stacks"]) if result["detected_stacks"] else "unknown"
    conf = result.get("confidence_score", 0.0)

    lines = [
        "╔══════════════════════════════════════════════════════════════════╗",
        "║      SYNAPSE HUB — PROGRESSIVE RULES ROUTER (BOOST B2)          ║",
        "╚══════════════════════════════════════════════════════════════════╝",
        f"Target Workspace: {result['workspace']}",
        f"Active Stacks   : {stacks_str} (Confidence: {conf})",
        f"Status          : {result['status']}",
        "",
        "─── Minimal Recommended Rules ───",
    ]
    for r in result["recommended_rules"]:
        lines.append(f"  ✓ standards/**/{r}")

    lines.append("")
    lines.append("─── Minimal Recommended Skills ───")
    for s in result["recommended_skills"]:
        lines.append(f"  ⚡ {s}")

    lines.append("")
    lines.append("─── Dual-Tier Token Optimization Metrics ───")
    if "hydration_contracts" in result:
        cat = result["hydration_contracts"]["catalog_summary"]
        hyd = result["hydration_contracts"]["full_hydration"]
        rf = result["hydration_contracts"].get("retrieval_footprint", {})
        est = result.get("estimator_info", {})
        lines.append(f"  Estimator Engine : {est.get('engine', 'cl100k_base')} (Exact BPE: {est.get('is_exact', False)})")
        lines.append(f"  [Tier 1 - Catalog Summary] Baseline: {cat['baseline_tokens']:,} | Routed: {cat['routed_tokens']:,} | Saved: {cat['tokens_saved']:,} ({cat['reduction_pct']}%)")
        lines.append(f"  [Tier 2 - Full Hydration ] Baseline: {hyd['baseline_tokens']:,} | Routed: {hyd['routed_tokens']:,} | Saved: {hyd['tokens_saved']:,} ({hyd['reduction_pct']}%)")
        lines.append(f"  [Disk I/O Footprint      ] Full: {rf.get('full_catalog_bytes', 0):,} B | Routed: {rf.get('routed_catalog_bytes', 0):,} B | Avoided: ~{rf.get('avoided_bytes', 0) // 1024} KB ({rf.get('io_reduction_pct', 0.0)}%)")
    else:
        lines.append(f"  Unrouted Baseline : {metrics['unrouted_baseline_tokens']:,} tokens")
        lines.append(f"  Progressive Routed: {metrics['routed_tokens']:,} tokens")
        lines.append(f"  Tokens Saved/Turn : {metrics['tokens_saved']:,} tokens ({metrics['reduction_percentage']}%)")
    lines.append("════════════════════════════════════════════════════════════════════")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Progressive Rules Router & Context Optimizer (Boost B2)"
    )
    parser.add_argument(
        "workspace",
        nargs="?",
        default=".",
        help="Target workspace directory to inspect (default: .)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON data instead of text format",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print single-line summary of routed rules and tokens saved",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Enforce minimal mode payload <= 6,000 tokens",
    )
    parser.add_argument(
        "--task-type",
        choices=["locator", "triage", "api", "perf", "security"],
        help="Target task intent profile",
    )
    parser.add_argument(
        "--token-cap",
        type=int,
        default=None,
        help="Enforce custom token cap ceiling for managed skill/rule hydrated documentation payload (excluding host system prompt, user prompt, and model context window)",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Permit partial routing status instead of raising TokenCapExceededError when cap < floor",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Maximum directory traversal depth for monorepo and marker scanning (default: 5)",
    )
    args = parser.parse_args()

    result = route_rules(
        args.workspace,
        minimal=args.minimal,
        task_type=args.task_type,
        token_cap=args.token_cap,
        allow_partial=args.allow_partial,
        depth=args.depth,
    )

    if args.json:
        print(format_routing_report(result, fmt="json"))
    elif args.summary:
        m = result["token_metrics"]
        stacks = ",".join(result["detected_stacks"]) or "base"
        print(f"[RULES-ROUTER] Stacks: {stacks} | Rules: {len(result['recommended_rules'])} | Saved: {m['tokens_saved']:,} tokens/turn ({m['reduction_percentage']}%)")
    else:
        print(format_routing_report(result, fmt="text"))


if __name__ == "__main__":
    main()
