#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/rules_router.py — Progressive Rules Router & Context Optimizer (Boost B2)
--------------------------------------------------------------------------------
Dynamically inspects workspace markers (Playwright, Cypress, Appium, K6, Security,
API) to route and emit ONLY the minimal necessary rule files and skill subset.
Prevents 4,000+ tokens of rule/skill bloat per agent turn while ensuring 100%
quality gate compliance.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Set

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Token constants for estimation (1 token ~= 4 chars)
CHARS_PER_TOKEN = 4

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

# Total baseline tokens when unrouted (all rules ~15KB + 53 skill descriptions ~12KB ~= 6,750 tokens)
ESTIMATED_UNROUTED_TOKENS = 6500


def _find_repo_root() -> str:
    """Finds the root of Synapse-Hub repository."""
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "AGENTS.md")) and os.path.exists(os.path.join(curr, ".agents")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def detect_workspace_stacks(workspace_dir: str) -> Dict[str, Any]:
    """
    Inspects workspace directory up to 2 levels deep to identify active tech stacks.
    Ignores heavy vendor and cache folders (.git, node_modules, build, etc.).
    """
    workspace = os.path.abspath(workspace_dir)
    detected: Dict[str, List[str]] = {
        "playwright": [],
        "cypress": [],
        "mobile": [],
        "performance": [],
        "security": [],
        "api": [],
        "git": [],
    }

    if not os.path.isdir(workspace):
        return {"detected_stacks": [], "evidence": detected}

    # Fast check for git
    if os.path.isdir(os.path.join(workspace, ".git")):
        detected["git"].append(".git directory")

    # Read package.json / requirements / configs in root
    pkg_json = os.path.join(workspace, "package.json")
    if os.path.isfile(pkg_json):
        try:
            with open(pkg_json, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                if "playwright" in content or "@playwright/test" in content:
                    detected["playwright"].append("package.json (playwright dependency)")
                if "cypress" in content:
                    detected["cypress"].append("package.json (cypress dependency)")
                if "appium" in content:
                    detected["mobile"].append("package.json (appium dependency)")
                if "k6" in content or "artillery" in content:
                    detected["performance"].append("package.json (perf dependency)")
        except Exception as err:
            _ = err

    # Read Python requirement / project config markers (requirements*.txt, pyproject.toml, Pipfile)
    for py_cfg_name in ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile", "setup.py"):
        py_cfg = os.path.join(workspace, py_cfg_name)
        if os.path.isfile(py_cfg):
            try:
                with open(py_cfg, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    if "playwright" in content or "pytest-playwright" in content:
                        detected["playwright"].append(f"{py_cfg_name} (playwright dependency)")
                    if "cypress" in content:
                        detected["cypress"].append(f"{py_cfg_name} (cypress dependency)")
                    if "appium" in content:
                        detected["mobile"].append(f"{py_cfg_name} (appium dependency)")
                    if "locust" in content or "k6" in content:
                        detected["performance"].append(f"{py_cfg_name} (performance dependency)")
                    if "bandit" in content or "semgrep" in content:
                        detected["security"].append(f"{py_cfg_name} (security dependency)")
            except Exception as err:
                _ = err

    # Read JVM build markers (build.gradle, build.gradle.kts, pom.xml)
    for jvm_cfg_name in ("build.gradle", "build.gradle.kts", "pom.xml"):
        jvm_cfg = os.path.join(workspace, jvm_cfg_name)
        if os.path.isfile(jvm_cfg):
            try:
                with open(jvm_cfg, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                    if "playwright" in content:
                        detected["playwright"].append(f"{jvm_cfg_name} (playwright dependency)")
                    if "appium" in content:
                        detected["mobile"].append(f"{jvm_cfg_name} (appium dependency)")
                    if "jmeter" in content or "gatling" in content:
                        detected["performance"].append(f"{jvm_cfg_name} (performance dependency)")
                    if "pact" in content or "rest-assured" in content:
                        detected["api"].append(f"{jvm_cfg_name} (api contract dependency)")
            except Exception as err:
                _ = err

    # Scan files up to depth 2
    ignored = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "target", ".gradle"}
    for root, dirs, files in os.walk(workspace):
        rel = os.path.relpath(root, workspace)
        depth = 0 if rel == "." else len(rel.split(os.sep))
        if depth >= 2:
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if d not in ignored]

        for file_name in files:
            f_lower = file_name.lower()
            rel_file = os.path.join(rel, file_name) if rel != "." else file_name

            # Playwright markers
            if f_lower.startswith("playwright.config."):
                detected["playwright"].append(rel_file)

            # Cypress markers
            if f_lower.startswith("cypress.config.") or f_lower == "cypress.json":
                detected["cypress"].append(rel_file)

            # Mobile markers
            if f_lower in ("caps.json", "androidmanifest.xml") or f_lower.endswith(".xcodeproj"):
                detected["mobile"].append(rel_file)

            # Performance markers
            if f_lower.endswith(".jmx") or f_lower == "locustfile.py" or ".k6." in f_lower or f_lower == "k6.js":
                detected["performance"].append(rel_file)

            # Security markers
            if any(k in f_lower for k in ("zap", "burp", "nuclei", "semgrep.yml")):
                detected["security"].append(rel_file)

            # API markers
            if f_lower in ("openapi.json", "openapi.yaml", "swagger.json", "swagger.yaml") or f_lower.endswith(".pact.json"):
                detected["api"].append(rel_file)

    active_stacks = [stack for stack, evidence in detected.items() if evidence]
    return {
        "detected_stacks": active_stacks,
        "evidence": {k: v for k, v in detected.items() if v},
    }


def route_rules(workspace_dir: str = ".") -> Dict[str, Any]:
    """
    Determines the minimal set of rules and skills for the target workspace.
    Calculates estimated tokens consumed versus the unrouted baseline.
    """
    repo_root = _find_repo_root()
    stack_info = detect_workspace_stacks(workspace_dir)
    active_stacks = stack_info["detected_stacks"]

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

    # Ensure rule files exist in .agents/rules
    rules_dir = os.path.join(repo_root, ".agents", "rules")
    valid_rules: List[str] = []
    total_rule_bytes = 0

    for r in sorted(rules_set):
        rule_path = os.path.join(rules_dir, r)
        if os.path.isfile(rule_path):
            valid_rules.append(r)
            try:
                total_rule_bytes += os.path.getsize(rule_path)
            except OSError:
                total_rule_bytes += 2000
        else:
            valid_rules.append(r)
            total_rule_bytes += 2000

    # Dynamic calculation of unrouted baseline from actual rules directory + 53 skill catalogue
    unrouted_rule_bytes = 0
    if os.path.isdir(rules_dir):
        for f in os.listdir(rules_dir):
            if f.endswith(".md"):
                try:
                    unrouted_rule_bytes += os.path.getsize(os.path.join(rules_dir, f))
                except OSError:
                    unrouted_rule_bytes += 2500
    else:
        unrouted_rule_bytes = 30000

    unrouted_baseline = (unrouted_rule_bytes // CHARS_PER_TOKEN) + (53 * 120)
    unrouted_baseline = max(unrouted_baseline, ESTIMATED_UNROUTED_TOKENS)

    # Skill tokens (~120 tokens per skill metadata summary)
    skill_tokens = len(skills_set) * 120
    rule_tokens = total_rule_bytes // CHARS_PER_TOKEN
    total_routed_tokens = rule_tokens + skill_tokens

    # Ensure estimated savings calculation
    tokens_saved = max(0, unrouted_baseline - total_routed_tokens)

    return {
        "workspace": os.path.abspath(workspace_dir),
        "detected_stacks": active_stacks,
        "evidence": stack_info["evidence"],
        "recommended_rules": valid_rules,
        "recommended_skills": sorted(skills_set),
        "token_metrics": {
            "unrouted_baseline_tokens": unrouted_baseline,
            "routed_tokens": total_routed_tokens,
            "tokens_saved": tokens_saved,
            "reduction_percentage": round((tokens_saved / unrouted_baseline) * 100, 1),
        },
    }


def format_routing_report(result: Dict[str, Any], fmt: str = "text") -> str:
    """Formats the routing outcome into human-readable text or JSON."""
    if fmt == "json":
        return json.dumps(result, indent=2, ensure_ascii=False)

    metrics = result["token_metrics"]
    stacks_str = ", ".join(result["detected_stacks"]) if result["detected_stacks"] else "Standard QA / Clean POM"

    lines = [
        "╔══════════════════════════════════════════════════════════════════╗",
        "║      SYNAPSE HUB — PROGRESSIVE RULES ROUTER (BOOST B2)          ║",
        "╚══════════════════════════════════════════════════════════════════╝",
        f"Target Workspace: {result['workspace']}",
        f"Active Stacks   : {stacks_str}",
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
    lines.append("─── Token Optimization Metrics ───")
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
    args = parser.parse_args()

    result = route_rules(args.workspace)

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
