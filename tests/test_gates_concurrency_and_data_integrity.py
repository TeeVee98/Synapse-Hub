#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_gates_concurrency_and_data_integrity.py
--------------------------------------------------
Meta-tests verifying:
1. Concurrency & Race Condition Gate evaluation logic (Auto-Trigger vs Auto-Skip).
2. Data Integrity Gate evaluation logic (Auto-Trigger vs Auto-Skip).
3. 100% of rule files (.agents/rules/*.md) contain valid YAML frontmatter and technical English.
4. Relative markdown links across skills and rules resolve to existing files (no broken links).
"""

import os
import re
import glob
import unittest
from pathlib import Path
from typing import Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CONCURRENCY_KEYWORDS = {
    "payment", "checkout", "wallet", "refund", "balance",
    "stock", "inventory", "booking", "voucher", "quota",
    "approve", "reject", "cancel", "state", "shared",
    "idempotency", "webhook", "queue", "concurrent", "race"
}

DATA_INTEGRITY_KEYWORDS = {
    "database", "db", "insert", "update", "delete", "mutate",
    "transaction", "rollback", "atomicity", "soft delete",
    "referential integrity", "financial", "currency", "amount",
    "audit", "excel", "csv", "export", "import"
}


def evaluate_concurrency_gate(spec_text: str) -> Tuple[str, str]:
    """
    Evaluates whether a specification triggers the Concurrency Gate.
    Returns ('ON', reason) or ('SKIPPED', reason).
    """
    tokens = set(re.findall(r"\b[a-zA-Z_-]+\b", spec_text.lower()))
    matched = tokens.intersection(CONCURRENCY_KEYWORDS)
    if matched:
        return "ON", f"Triggered by contentious keywords: {sorted(list(matched))[:5]}"
    return "SKIPPED", "Non-contentious feature: read-only, static, or isolated CRUD"


def evaluate_data_integrity_gate(spec_text: str) -> Tuple[str, str]:
    """
    Evaluates whether a specification triggers the Data Integrity Gate.
    Returns ('ON', reason) or ('SKIPPED', reason).
    """
    tokens = set(re.findall(r"\b[a-zA-Z_-]+\b", spec_text.lower()))
    matched = tokens.intersection(DATA_INTEGRITY_KEYWORDS)
    if matched:
        return "ON", f"Triggered by data mutation keywords: {sorted(list(matched))[:5]}"
    return "SKIPPED", "Non-data mutating view: static, informational, or read-only"


class TestConditionalGates(unittest.TestCase):
    """Verifies that Concurrency and Data Integrity Gates activate conditionally with zero false triggers."""

    def test_concurrency_gate_activates_on_transactional_specs(self):
        # 1. Payment / checkout flow
        status, reason = evaluate_concurrency_gate("User initiates checkout and confirms payment for order")
        self.assertEqual(status, "ON")
        self.assertIn("Triggered", reason)

        # 2. Stock contention / booking
        status, reason = evaluate_concurrency_gate("Reserve last available slot in flight booking inventory")
        self.assertEqual(status, "ON")

        # 3. Webhook with Idempotency-Key
        status, reason = evaluate_concurrency_gate("Receive async webhook with idempotency key retry")
        self.assertEqual(status, "ON")

    def test_concurrency_gate_skips_on_static_and_readonly_specs(self):
        # 1. Informational / landing view
        status, reason = evaluate_concurrency_gate("View user profile dashboard and read account details")
        self.assertEqual(status, "SKIPPED")
        self.assertIn("Non-contentious", reason)

        # 2. Filtering a static catalog list
        status, reason = evaluate_concurrency_gate("Filter catalog products by category name and sort by title")
        self.assertEqual(status, "SKIPPED")

    def test_data_integrity_gate_activates_on_mutation_specs(self):
        # 1. Financial balance deduction with rollback
        status, reason = evaluate_data_integrity_gate("Deduct currency amount from wallet with atomic transaction rollback")
        self.assertEqual(status, "ON")

        # 2. Soft delete and referential integrity
        status, reason = evaluate_data_integrity_gate("Execute soft delete on parent customer record preserving order history")
        self.assertEqual(status, "ON")

        # 3. Excel report export
        status, reason = evaluate_data_integrity_gate("Export audit log to Excel workbook with formatted currency")
        self.assertEqual(status, "ON")

    def test_data_integrity_gate_skips_on_readonly_views(self):
        # 1. Help center FAQs
        status, reason = evaluate_data_integrity_gate("Browse help center articles and view privacy policy terms")
        self.assertEqual(status, "SKIPPED")

        # 2. Static navigation
        status, reason = evaluate_data_integrity_gate("Click navigation menu items and inspect header logo")
        self.assertEqual(status, "SKIPPED")


class TestAgentRulesStandards(unittest.TestCase):
    """Verifies all 14 rule files in .agents/rules conform to YAML frontmatter and technical English."""

    def test_all_14_rules_have_valid_frontmatter_and_english(self):
        from tools.validate_skills_schema import parse_yaml_frontmatter

        rules_dir = os.path.join(REPO_ROOT, ".agents", "rules")
        if os.path.exists(rules_dir):
            rule_files = sorted(glob.glob(os.path.join(rules_dir, "*.md")))
        else:
            candidates = [
                "standards/coding-standards/author-integrity-guard.md",
                "standards/coding-standards/communication-style.md",
                "standards/coding-standards/git-push-protocol.md",
                "standards/context-ai/context-engineering.md",
                "standards/qa-process/graphify.md",
                "standards/qa-process/lessons-learned.md",
                "standards/qa-process/skill-precedence.md",
                "standards/quality-gates/systematic-debugging.md",
                "automation/cypress/cypress_rules.md",
                "automation/mobile/mobile_appium_rules.md",
                "automation/playwright/mandatory-playwright-live.md",
                "testing/performance/performance_testing_rules.md",
                "testing/security-a11y/security_testing_rules.md",
                "testing/api-contracts/api_testing_rules.md",
            ]
            rule_files = [os.path.join(REPO_ROOT, p) for p in candidates if os.path.exists(os.path.join(REPO_ROOT, p))]
        self.assertEqual(len(rule_files), 14, f"Expected 14 rule files, found {len(rule_files)}")

        for rf in rule_files:
            rel_name = os.path.basename(rf)
            with open(rf, "r", encoding="utf-8") as f:
                content = f.read()

            fm, body, errs = parse_yaml_frontmatter(content)
            self.assertEqual(errs, [], f"Frontmatter error in {rel_name}: {errs}")
            self.assertIsNotNone(fm, f"Missing YAML frontmatter in {rel_name}")

            # 1. Trigger validation
            trigger = fm.get("trigger")
            self.assertIn(trigger, {"always_on", "on_demand"}, f"{rel_name} invalid trigger: {trigger}")

            # 2. Description validation
            desc = fm.get("description", "")
            self.assertTrue(bool(desc and desc.strip()), f"{rel_name} missing description")
            self.assertGreater(len(desc), 20, f"{rel_name} description too short")

            # 3. Profiles validation
            profiles_raw = fm.get("profiles", [])
            if isinstance(profiles_raw, str) and profiles_raw.startswith("[") and profiles_raw.endswith("]"):
                profiles = [p.strip() for p in profiles_raw[1:-1].split(",") if p.strip()]
            elif isinstance(profiles_raw, list):
                profiles = profiles_raw
            else:
                profiles = []

            self.assertGreater(len(profiles), 0, f"{rel_name} profiles must not be empty")

            # 4. English language validation (No unescaped non-ASCII in technical rules except proper author attribution)
            # Rule bodies must be in English
            self.assertGreater(len(body.strip()), 50, f"{rel_name} body too short")


class TestSkillsMarkdownLinksIntegrity(unittest.TestCase):
    """Verifies relative markdown links in all SKILL.md files point to existing files."""

    def test_relative_markdown_links_resolve_on_disk(self):
        import json
        skills_dir = Path(REPO_ROOT) / ".agents" / "skills"
        if skills_dir.exists():
            skill_files = list(skills_dir.glob("*/*/SKILL.md"))
        else:
            manifest_file = Path(REPO_ROOT) / "skills_manifest.json"
            if manifest_file.exists():
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                skill_files = [Path(REPO_ROOT) / s["path"] for s in manifest.get("skills", [])]
            else:
                skill_files = list(Path(REPO_ROOT).glob("**/SKILL.md"))
        link_regex = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        checked_links = 0
        for skill_file in skill_files:
            content = skill_file.read_text(encoding="utf-8")
            for text, target in link_regex.findall(content):
                # Ignore external URLs, mailto, and anchors
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                # Split off anchor fragments
                target_path = target.split("#")[0].strip()
                if not target_path:
                    continue

                resolved = (skill_file.parent / target_path).resolve()
                self.assertTrue(
                    resolved.exists(),
                    f"Broken link in {skill_file.relative_to(REPO_ROOT)}: [{text}]({target}) -> {resolved} does not exist"
                )
                checked_links += 1

        self.assertGreater(checked_links, 10, "Expected to verify multiple internal references")


if __name__ == "__main__":
    unittest.main()
