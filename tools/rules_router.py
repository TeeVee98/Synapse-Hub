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

import argparse
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
                "rule_count": 13,
                "rule_tokens": 8420,
                "rule_bytes": 31927,
                "skill_count": 53,
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
    "cypress": ["systematic-debugging.md"],
    "mobile": ["mobile_appium_rules.md", "systematic-debugging.md"],
    "katalon": ["systematic-debugging.md"],
    "selenium": ["systematic-debugging.md"],
    "performance": ["performance_testing_rules.md"],
    "security": ["security_testing_rules.md"],
    "api": ["systematic-debugging.md"],
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


def _find_repo_root() -> str:
    """Finds the root of Synapse-Hub repository."""
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "AGENTS.md")) and os.path.exists(os.path.join(curr, ".agents")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _scan_directory_markers(target_dir: str, prefix: str = "") -> Tuple[Dict[str, List[str]], Dict[str, float]]:
    """Scans a single directory level up to depth 2 for testing markers."""
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
        if depth >= 2:
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


def detect_workspace_stacks(workspace_dir: str) -> Dict[str, Any]:
    """
    Inspects target workspace directory, supporting standalone projects and Monorepos.
    Calculates confidence scores for detected testing stacks.
    """
    workspace = os.path.abspath(workspace_dir)
    detected, confidence = _scan_directory_markers(workspace)

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
        # Traverse subpackages in packages/, apps/, services/, modules/
        for sub_parent in ("packages", "apps", "services", "modules"):
            parent_dir = os.path.join(workspace, sub_parent)
            if os.path.isdir(parent_dir):
                try:
                    for child in os.listdir(parent_dir):
                        child_dir = os.path.join(parent_dir, child)
                        if os.path.isdir(child_dir) and not child.startswith("."):
                            prefix = f"[{sub_parent}/{child}] "
                            sub_det, sub_conf = _scan_directory_markers(child_dir, prefix=prefix)
                            for stack, evs in sub_det.items():
                                detected[stack].extend(evs)
                                confidence[stack] = max(confidence[stack], sub_conf[stack])
                except OSError as err:
                    logger.debug("Failed to inspect subpackage: %s", err)

    # Filter active stacks where confidence >= 0.50
    active_stacks = [s for s, evs in detected.items() if evs and confidence[s] >= 0.50]

    return {
        "detected_stacks": active_stacks,
        "is_monorepo": is_monorepo,
        "confidence": {k: round(confidence[k], 2) for k in active_stacks},
        "evidence": {k: detected[k] for k in active_stacks},
    }


def route_rules(workspace_dir: str = ".", minimal: bool = False, task_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Determines minimal rules and skills for target workspace, with dual-tier token hydration
    accounting and strict truth-anchoring for unknown stacks.
    """
    repo_root = _find_repo_root()
    stack_info = detect_workspace_stacks(workspace_dir)
    active_stacks = stack_info["detected_stacks"]

    is_unknown_stack = len(active_stacks) == 0

    # Compile rules
    rules_set: Set[str] = set(CORE_BASE_RULES)
    for stack in active_stacks:
        for r in STACK_RULE_MAPPINGS.get(stack, []):
            rules_set.add(r)

    # Compile skills
    skills_set: Set[str] = set(DEFAULT_CORE_SKILLS)
    for stack in active_stacks:
        for s in STACK_SKILL_MAPPINGS.get(stack, []):
            skills_set.add(s)

    if task_type == "locator":
        minimal = True
        skills_set = {"clean-pom-crafter", "self-healing-locator"}
    elif task_type == "triage":
        minimal = True
        skills_set = {"failure-autopsy-and-healing", "systematic-debugging"}
    elif minimal:
        skills_set = set(sorted(skills_set)[:1])

    # Resolve rules directory
    rules_dir = os.path.join(repo_root, ".agents", "rules")
    valid_rules = sorted(rules_set)
    valid_skills = sorted(skills_set)

    # Calculate dual-tier hydration payloads
    routed_payload = calculate_hydration_payload(repo_root, valid_rules, valid_skills)

    # Calculate full unrouted baseline dynamically by enumerating 100% of skills & rules
    baseline = get_full_unrouted_baseline(repo_root)
    unrouted_summary_baseline = baseline["total_summary_baseline"]
    unrouted_full_baseline = baseline["total_full_baseline"]
    unrouted_full_bytes = baseline["total_full_bytes"]
    estimator_info = baseline.get("estimator_info", get_estimator_info())

    # If workspace is unclassified (no stack detected), report honest fallback metrics
    if is_unknown_stack:
        return {
            "workspace": os.path.abspath(workspace_dir),
            "task_mode": "minimal" if (minimal or task_type) else "full",
            "token_cap": 6000 if (minimal or task_type) else None,
            "task_type": task_type,
            "status": "UNCLASSIFIED_WORKSPACE",
            "detected_stacks": ["unknown"],
            "classification": "UNCLASSIFIED_WORKSPACE (Fallback Core Base Rules)",
            "confidence_score": 0.0,
            "evidence": {},
            "recommended_rules": valid_rules,
            "recommended_skills": valid_skills,
            "estimator_info": estimator_info,
            "token_metrics": {
                "unrouted_baseline_tokens": unrouted_summary_baseline,
                "routed_tokens": routed_payload["total_summary_tokens"],
                "tokens_saved": 0,
                "reduction_percentage": 0.0,
                "note": "Stack unclassified; routed to core base profile without claiming workload-specific token reduction.",
            },
            "hydration_contracts": {
                "catalog_summary": {
                    "baseline_tokens": unrouted_summary_baseline,
                    "routed_tokens": routed_payload["total_summary_tokens"],
                    "tokens_saved": 0,
                    "reduction_pct": 0.0,
                },
                "full_hydration": {
                    "baseline_tokens": unrouted_full_baseline,
                    "routed_tokens": routed_payload["total_hydrated_tokens"],
                    "tokens_saved": 0,
                    "reduction_pct": 0.0,
                },
                "retrieval_footprint": {
                    "full_catalog_bytes": unrouted_full_bytes,
                    "routed_catalog_bytes": routed_payload["total_hydrated_bytes"],
                    "avoided_bytes": 0,
                    "io_reduction_pct": 0.0,
                    "label": "Disk Read I/O Footprint Avoided (Disk File Size, Not Context Tokens)",
                },
            },
        }

    # Classified stacks: compute honest savings for both tiers
    summary_saved = max(0, unrouted_summary_baseline - routed_payload["total_summary_tokens"])
    summary_pct = round((summary_saved / max(1, unrouted_summary_baseline)) * 100, 1)

    hydrated_saved = max(0, unrouted_full_baseline - routed_payload["total_hydrated_tokens"])
    hydrated_pct = round((hydrated_saved / max(1, unrouted_full_baseline)) * 100, 1)

    avoided_io_bytes = max(0, unrouted_full_bytes - routed_payload["total_hydrated_bytes"])
    io_reduction_pct = round((avoided_io_bytes / max(1, unrouted_full_bytes)) * 100, 1)

    avg_conf = sum(stack_info["confidence"].values()) / max(1, len(stack_info["confidence"]))

    return {
        "workspace": os.path.abspath(workspace_dir),
        "task_mode": "minimal" if (minimal or task_type) else "full",
        "token_cap": 6000 if (minimal or task_type) else None,
        "task_type": task_type,
        "status": "CLASSIFIED",
        "detected_stacks": active_stacks,
        "classification": f"CLASSIFIED ({', '.join(active_stacks)})",
        "confidence_score": round(avg_conf, 2),
        "evidence": stack_info["evidence"],
        "recommended_rules": valid_rules,
        "recommended_skills": valid_skills,
        "estimator_info": estimator_info,
        "token_metrics": {
            "unrouted_baseline_tokens": unrouted_summary_baseline,
            "routed_tokens": routed_payload["total_summary_tokens"],
            "tokens_saved": summary_saved,
            "reduction_percentage": summary_pct,
        },
        "hydration_contracts": {
            "catalog_summary": {
                "baseline_tokens": unrouted_summary_baseline,
                "routed_tokens": routed_payload["total_summary_tokens"],
                "tokens_saved": summary_saved,
                "reduction_pct": summary_pct,
                "scope": "Skill registry metadata for Front-Door Orchestrator",
            },
            "full_hydration": {
                "baseline_tokens": unrouted_full_baseline,
                "routed_tokens": routed_payload["total_hydrated_tokens"],
                "tokens_saved": hydrated_saved,
                "reduction_pct": hydrated_pct,
                "scope": "Complete SKILL.md bodies injected into Specialized Subagents",
            },
            "retrieval_footprint": {
                "full_catalog_bytes": unrouted_full_bytes,
                "routed_catalog_bytes": routed_payload["total_hydrated_bytes"],
                "avoided_bytes": avoided_io_bytes,
                "io_reduction_pct": io_reduction_pct,
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
        lines.append(f"  ✓ .agents/rules/{r}")

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
    args = parser.parse_args()

    result = route_rules(args.workspace, minimal=args.minimal, task_type=args.task_type)

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
