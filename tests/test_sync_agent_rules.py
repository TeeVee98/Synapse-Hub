#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Golden Unit Tests for tools/sync_agent_rules.py (AI Bridge Rule Synchronizer)
----------------------------------------------------------------------------
Validates:
  1. Bridge generators for Claude, Cursor, Windsurf, Copilot
  2. Mandatory Author Attribution & MIT License guard preservation
  3. Single source of truth invariants (Clean POM, Zero Hard Sleeps, Truth Anchor)
  4. Non-drift check mode (sync_all --check)
  5. Completeness of TARGET_GENERATORS registry (10 bridge paths)
  6. Template scope cleanliness: zero occurrences of tools/verify_all.py in templates/ai_bridges/*
  7. Conformance to 3-tier policy structure (ALWAYS, RECOMMENDED, SYNAPSE-HUB-ONLY)
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
CORE_DIR = os.path.join(TOOLS_DIR, "core")
for p in (REPO_ROOT, TOOLS_DIR, CORE_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import tools.core.sync_agent_rules as sar
except ImportError:
    import sync_agent_rules as sar

from tools.core.cache_prefix_enforcer import CachePrefixEnforcer
from tools.lint.lint_cache_prefix import run_prefix_lint


class TestSyncAgentRules(unittest.TestCase):

    def test_target_generators_registry(self):
        """Verifies TARGET_GENERATORS contains all 10 canonical bridge paths."""
        self.assertEqual(len(sar.TARGET_GENERATORS), 10)
        paths = [rel_path for rel_path, _ in sar.TARGET_GENERATORS]
        self.assertIn("CLAUDE.md", paths)
        self.assertIn(".cursorrules", paths)
        self.assertIn(".windsurfrules", paths)
        self.assertIn(".cursor/rules/synapse-qa.mdc", paths)
        self.assertIn(".github/copilot-instructions.md", paths)
        self.assertIn(".github/instructions/clean-pom.instructions.md", paths)
        self.assertIn("templates/ai_bridges/CLAUDE.md", paths)
        self.assertIn("templates/ai_bridges/cursor_synapse_qa.mdc", paths)
        self.assertIn("templates/ai_bridges/windsurfrules", paths)
        self.assertIn("templates/ai_bridges/copilot-instructions.md", paths)

    def test_generate_claude_md(self):
        content = sar.generate_claude_md(is_template=False)
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("MIT License", content)
        self.assertIn("Clean Page Object Model (POM)", content)
        self.assertIn("Truth Anchor", content)
        self.assertIn("Dynamic Smart Waits Only", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)
        self.assertIn("SYNAPSE-HUB-ONLY", content)

    def test_generate_cursorrules(self):
        content = sar.generate_cursorrules()
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("Clean POM Flat Architecture", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_generate_windsurfrules(self):
        content = sar.generate_windsurfrules(is_template=False)
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("Clean Page Object Model (POM)", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_generate_cursor_mdc(self):
        content = sar.generate_cursor_mdc(is_template=False)
        self.assertTrue(content.startswith("---"))
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("description:", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_generate_copilot_instructions(self):
        content = sar.generate_copilot_instructions(is_template=False)
        self.assertIn("Thế Vị (@TeeVee98)", content)
        self.assertIn("GitHub Copilot", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_generate_clean_pom_instructions(self):
        content = sar.generate_clean_pom_instructions()
        self.assertTrue(content.startswith("---"))
        self.assertIn("Clean Page Object Model (POM)", content)
        self.assertIn("ALWAYS", content)
        self.assertIn("RECOMMENDED", content)

    def test_template_bridges_cleanliness_contract(self):
        """Contract: templates/ai_bridges/* must NEVER leak Hub tools/, skills_index.json, or Hub-only mandates."""
        template_paths = [
            os.path.join(REPO_ROOT, "templates", "ai_bridges", "CLAUDE.md"),
            os.path.join(REPO_ROOT, "templates", "ai_bridges", "cursor_synapse_qa.mdc"),
            os.path.join(REPO_ROOT, "templates", "ai_bridges", "windsurfrules"),
            os.path.join(REPO_ROOT, "templates", "ai_bridges", "copilot-instructions.md"),
        ]
        forbidden_hub_leaks = [
            "tools/core/",
            "tools/lint/",
            "tools/orchestration/",
            "tools/design/",
            "skills_index.json",
            "SYNAPSE-HUB-ONLY",
            "across all codebase files",
        ]
        for t_path in template_paths:
            self.assertTrue(os.path.isfile(t_path), f"Template bridge file missing: {t_path}")
            with open(t_path, "r", encoding="utf-8") as f:
                content = f.read()
            for leak in forbidden_hub_leaks:
                self.assertNotIn(
                    leak,
                    content,
                    f"Template {t_path} leaked Hub-only token '{leak}' into client project scope!",
                )
            self.assertIn("MIT License", content, f"Template {t_path} missing mandatory MIT license attribution")

    def test_client_bridge_bundle_dto(self):
        """Verifies client templates use CLIENT_INVARIANTS_MD with zero Hub path leaks."""
        bundle = sar.build_client_bridge_bundle(mode="client")
        self.assertEqual(bundle.mode, "client")
        self.assertEqual(bundle.hub_paths_leaked, 0)
        self.assertEqual(bundle.config_file, "synapse.config.json")
        self.assertNotIn("tools/", bundle.content)

    def test_sync_all_check_clean(self):
        exit_code = sar.sync_all(check_only=True)
        self.assertEqual(exit_code, 0)

    def test_stack_specific_rules_protected(self):
        """Verifies PROTECTED_STACK_RULES exist on disk and are strictly excluded from TARGET_GENERATORS."""
        self.assertTrue(hasattr(sar, "PROTECTED_STACK_RULES"), "sar missing PROTECTED_STACK_RULES constant")
        self.assertGreaterEqual(len(sar.PROTECTED_STACK_RULES), 5)
        for rule_path in sar.PROTECTED_STACK_RULES:
            full_path = os.path.join(REPO_ROOT, rule_path)
            self.assertTrue(os.path.isfile(full_path), f"Protected stack rule missing on disk: {rule_path}")

        target_paths = [rel_path for rel_path, _ in sar.TARGET_GENERATORS]
        for rule_path in sar.PROTECTED_STACK_RULES:
            self.assertNotIn(rule_path, target_paths, f"Protected rule {rule_path} found in TARGET_GENERATORS!")

    def test_sync_all_check_validates_agents_md_prefix_and_budget(self):
        """sync_all(check_only=True) must fail when AGENTS.md exceeds MAX_RULE_TOKENS or violates prefix lint."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            for rel_prot in sar.PROTECTED_STACK_RULES:
                prot_path = os.path.join(tmp_dir, rel_prot)
                os.makedirs(os.path.dirname(prot_path), exist_ok=True)
                with open(prot_path, "w", encoding="utf-8") as f:
                    f.write("# protected\n")

            for rel_path, gen_fn in sar.TARGET_GENERATORS:
                out_path = os.path.join(tmp_dir, rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(gen_fn().strip() + "\n")

            agents_path = os.path.join(tmp_dir, "AGENTS.md")
            valid_prefix = (
                "# AGENTS.md\n"
                "### 0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE\n"
                + ("Immutable rule anchor line for prompt cache stability.\n" * 140)
                + "## 1.1 PRE-FLIGHT REASONING CHECKLIST\n---\n"
            )

            # 1. Negative: Exceeds MAX_RULE_TOKENS
            bloated_suffix = "Verbose suffix line.\n" * 1200
            with open(agents_path, "w", encoding="utf-8") as f:
                f.write(valid_prefix + bloated_suffix)
            with patch.object(sar, "REPO_ROOT", tmp_dir):
                self.assertEqual(sar.sync_all(check_only=True), 1)

            # 2. Negative: Violates prefix lint (missing Section 0.2 / below MIN_CACHE_TOKENS)
            with open(agents_path, "w", encoding="utf-8") as f:
                f.write("# AGENTS.md\nShort invalid content.\n")
            with patch.object(sar, "REPO_ROOT", tmp_dir):
                self.assertEqual(sar.sync_all(check_only=True), 1)

            # 3. Positive: Valid prefix and within budget
            with open(agents_path, "w", encoding="utf-8") as f:
                f.write(valid_prefix + "## 2. RECOMMENDED\n- Keep concise.\n")
            with patch.object(sar, "REPO_ROOT", tmp_dir):
                self.assertEqual(sar.sync_all(check_only=True), 0)

    def test_generated_claude_md_passes_prefix_lint(self):
        """Generated CLAUDE.md includes Section 0.2 architecture header and passes run_prefix_lint."""
        content = sar.generate_claude_md(is_template=False)
        self.assertIn("0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE", content)
        with tempfile.TemporaryDirectory() as tmp_dir:
            claude_path = os.path.join(tmp_dir, "CLAUDE.md")
            with open(claude_path, "w", encoding="utf-8") as f:
                f.write(content)
            passed, issues = run_prefix_lint(claude_path)
            self.assertTrue(passed, f"Generated CLAUDE.md failed run_prefix_lint: {issues}")

    def test_agents_md_on_disk_meets_token_budget_and_prefix_floor(self):
        """AGENTS.md on disk satisfies total_est < 3500 and prefix_tokens >= 1024 with 0 volatiles."""
        agents_path = os.path.join(REPO_ROOT, "AGENTS.md")
        with open(agents_path, "r", encoding="utf-8") as f:
            content = f.read()
        partition = CachePrefixEnforcer.partition_prompt(content, auto_isolate_volatile=False)
        total_est = CachePrefixEnforcer.estimate_tokens(content)
        self.assertGreaterEqual(partition["prefix_tokens"], CachePrefixEnforcer.MIN_CACHE_TOKENS)
        self.assertLess(total_est, 3500)
        self.assertEqual(CachePrefixEnforcer.detect_volatile_elements(partition["prefix"]), [])

    def test_sync_minified_schema_positive_and_main_integration(self):
        """sync_minified_schema() generates tools_schema.min.json in tmp_dir and main() invokes it."""
        import tools.report.generate_tool_catalog as gtc
        from tools.runtime.meta_tool_engine import MetaToolEngine

        with tempfile.TemporaryDirectory() as tmp_dir:
            tools_dir = os.path.join(tmp_dir, "tools")
            os.makedirs(tools_dir, exist_ok=True)
            sample_schema = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "version": "1.0.0",
                "description": "Sample verbose schema for minification test",
                "tools": {
                    "sample_linter": {
                        "path": "tools/sample_linter.py",
                        "command": "python3 tools/sample_linter.py",
                        "summary": "A very verbose summary describing every detail of sample_linter.",
                        "description": "Long description that should be pruned during minification.",
                        "examples": ["python3 tools/sample_linter.py --strict"],
                        "args": {
                            "--strict": {
                                "type": "boolean",
                                "default": False,
                                "required": False,
                                "help": "Verbose help text that must be stripped in minified output.",
                            },
                            "--format": {
                                "type": "string",
                                "choices": ["text", "json"],
                                "default": "text",
                                "required": True,
                                "help": "Output format choice.",
                            },
                        },
                    }
                },
            }
            schema_path = os.path.join(tools_dir, "tools_schema.json")
            with open(schema_path, "w", encoding="utf-8") as f:
                json.dump(sample_schema, f, indent=2)

            res = gtc.sync_minified_schema(repo_root=tmp_dir)
            min_path = os.path.join(tools_dir, "tools_schema.min.json")
            self.assertTrue(res.get("synced"), f"Expected synced=True, got {res}")
            self.assertTrue(os.path.isfile(min_path))
            self.assertLess(res["minified_size"], res["original_size"])
            self.assertGreater(res["savings_pct"], 0.0)
            self.assertEqual(res["tools_count"], 1)

            with open(min_path, "r", encoding="utf-8") as f:
                min_data = json.load(f)
            self.assertIn("tools", min_data)
            self.assertIn("sample_linter", min_data["tools"])
            self.assertEqual(min_data["tools"]["sample_linter"]["cmd"], "python3 tools/sample_linter.py")

            engine = MetaToolEngine(tmp_dir)
            self.assertEqual(engine.schema_source, "tools_schema.min.json")
            self.assertIn("sample_linter", engine._tools_catalog)

            # Verify main() refreshes tools_schema.min.json automatically in isolated tmp_dir
            os.remove(min_path)
            with patch.object(gtc, "REPO_ROOT", tmp_dir), patch.object(gtc, "TOOLS_DIR", tools_dir):
                exit_code = gtc.main()
            self.assertEqual(exit_code, 0)
            self.assertTrue(os.path.isfile(min_path))

    def test_sync_minified_schema_missing_and_malformed_boundaries(self):
        """sync_minified_schema() handles missing or malformed tools_schema.json without crashing."""
        import tools.report.generate_tool_catalog as gtc

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Boundary: missing tools/tools_schema.json
            missing_res = gtc.sync_minified_schema(repo_root=tmp_dir)
            self.assertFalse(missing_res.get("synced"))
            self.assertFalse(os.path.exists(os.path.join(tmp_dir, "tools", "tools_schema.min.json")))

            # Negative: malformed JSON in tools/tools_schema.json
            tools_dir = os.path.join(tmp_dir, "tools")
            os.makedirs(tools_dir, exist_ok=True)
            with open(os.path.join(tools_dir, "tools_schema.json"), "w", encoding="utf-8") as f:
                f.write("{corrupt json")
            malformed_res = gtc.sync_minified_schema(repo_root=tmp_dir)
            self.assertFalse(malformed_res.get("synced"))
            self.assertFalse(os.path.exists(os.path.join(tools_dir, "tools_schema.min.json")))

    def test_sync_project_state_records_kv_cache_telemetry_and_boundaries(self):
        """sync_project_state() evaluates KV cache baseline and records kv_cache_min_pct safely."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            agents_path = os.path.join(tmp_dir, "AGENTS.md")
            state_path = os.path.join(tmp_dir, "project_state.json")
            config_path = os.path.join(tmp_dir, "synapse.config.json")

            valid_agents = (
                "# AGENTS.md\n"
                "### 0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE\n"
                + ("Immutable rule anchor line for prompt cache stability.\n" * 140)
                + "## 1.1 PRE-FLIGHT REASONING CHECKLIST\n---\n"
                + "## 2. RECOMMENDED\n- Keep concise.\n"
            )
            with open(agents_path, "w", encoding="utf-8") as f:
                f.write(valid_agents)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "schema_version": "1.1.0",
                        "quality_verification": {"ten_quality_gates": "11/11 PASS"},
                    },
                    f,
                )
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"telemetry": {"min_kv_cache_hit_rate_pct": 88.5}}, f)

            sar.sync_project_state(repo_root=tmp_dir)
            with open(state_path, "r", encoding="utf-8") as f:
                synced_state = json.load(f)

            qv = synced_state["quality_verification"]
            self.assertEqual(qv["ten_quality_gates"], "11/11 PASS")
            self.assertEqual(qv["kv_cache_min_pct"], 88.5)
            self.assertGreaterEqual(qv["kv_cache_baseline_pct"], 88.5)
            self.assertTrue(qv["kv_cache_baseline_passed"])
            self.assertGreaterEqual(qv["rule_prefix_tokens"], CachePrefixEnforcer.MIN_CACHE_TOKENS)

            # Negative: short non-eligible AGENTS.md triggers baseline failure flag without crashing
            with open(agents_path, "w", encoding="utf-8") as f:
                f.write("# AGENTS.md\nShort rule.\n")
            sar.sync_project_state(repo_root=tmp_dir)
            with open(state_path, "r", encoding="utf-8") as f:
                short_state = json.load(f)
            self.assertEqual(short_state["quality_verification"]["kv_cache_baseline_pct"], 0.0)
            self.assertFalse(short_state["quality_verification"]["kv_cache_baseline_passed"])

            # Boundary: missing synapse.config.json falls back to default 85.0%
            os.remove(config_path)
            with open(agents_path, "w", encoding="utf-8") as f:
                f.write(valid_agents)
            sar.sync_project_state(repo_root=tmp_dir)
            with open(state_path, "r", encoding="utf-8") as f:
                default_state = json.load(f)
            self.assertEqual(default_state["quality_verification"]["kv_cache_min_pct"], 85.0)
            self.assertTrue(default_state["quality_verification"]["kv_cache_baseline_passed"])

    def test_assemble_cached_rule_payload_prefix_stability_and_boundaries(self):
        """assemble_cached_rule_payload() keeps prefix_sha256 invariant across dynamic suffixes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            agents_path = os.path.join(tmp_dir, "AGENTS.md")
            valid_agents = (
                "# AGENTS.md\n"
                "### 0.2 PROMPT CACHING & IMMUTABLE PREFIX ARCHITECTURE\n"
                + ("Immutable rule anchor line for prompt cache stability.\n" * 140)
                + "## 1.1 PRE-FLIGHT REASONING CHECKLIST\n---\n"
                + "## 2. RECOMMENDED\n- Keep concise.\n"
            )
            with open(agents_path, "w", encoding="utf-8") as f:
                f.write(valid_agents)

            res_a = sar.assemble_cached_rule_payload(repo_root=tmp_dir, dynamic_suffix="Execute task alpha")
            res_b = sar.assemble_cached_rule_payload(
                repo_root=tmp_dir,
                dynamic_suffix="Execute task beta at 2026-11-24T12:00:00Z",
            )
            self.assertEqual(res_a["prefix_sha256"], res_b["prefix_sha256"])
            self.assertTrue(res_a["is_cache_eligible"])
            self.assertGreaterEqual(res_a["prefix_tokens"], CachePrefixEnforcer.MIN_CACHE_TOKENS)
            self.assertGreater(res_b["suffix_tokens"], 0)
            self.assertIn("payload", res_a)
            self.assertIn("cached_content", res_a["payload"])

            # Boundary: empty directory without AGENTS.md or CLAUDE.md does not crash
            empty_dir = os.path.join(tmp_dir, "empty")
            os.makedirs(empty_dir, exist_ok=True)
            res_empty = sar.assemble_cached_rule_payload(repo_root=empty_dir, dynamic_suffix="Fallback task")
            self.assertFalse(res_empty["is_cache_eligible"])
            self.assertEqual(res_empty["prefix_tokens"], 0)
            self.assertIn("payload", res_empty)

    def test_single_agent_solo_boundary_across_rules_and_bridges(self):
        """AGENTS.md, skills, workflows, and generated AI bridges enforce /solo single-agent boundary."""
        agents_path = os.path.join(REPO_ROOT, "AGENTS.md")
        solo_skill_path = os.path.join(REPO_ROOT, ".agent", "skills", "solo", "SKILL.md")
        legacy_solo_skill_path = os.path.join(REPO_ROOT, ".agent", "skills", "solo-swarm", "SKILL.md")
        solo_workflow_path = os.path.join(REPO_ROOT, "ai-agents", "workflows", "solo.md")
        legacy_solo_workflow_path = os.path.join(REPO_ROOT, "ai-agents", "workflows", "solo-swarm.md")
        plan_skill_path = os.path.join(REPO_ROOT, ".agent", "skills", "super-plan", "SKILL.md")

        self.assertTrue(os.path.isfile(solo_skill_path), "Missing .agent/skills/solo/SKILL.md")
        self.assertFalse(os.path.exists(legacy_solo_skill_path), "Legacy .agent/skills/solo-swarm/SKILL.md should be removed")
        self.assertTrue(os.path.isfile(solo_workflow_path), "Missing ai-agents/workflows/solo.md")
        self.assertFalse(os.path.exists(legacy_solo_workflow_path), "Legacy ai-agents/workflows/solo-swarm.md should be removed")

        with open(agents_path, "r", encoding="utf-8") as f:
            agents_text = f.read()
        self.assertIn("/solo", agents_text)
        self.assertNotIn("/solo-swarm", agents_text)
        self.assertIn("/teamwork", agents_text)
        self.assertRegex(agents_text.lower(), r"forbid.*spawn.*swarm|strictly forbidden to spawn")
        self.assertIn("Thế Vị (@TeeVee98)", agents_text)
        self.assertIn("MIT License", agents_text)
        self.assertIn("17. **Mandatory Adversarial Self-Audit", agents_text)

        with open(solo_skill_path, "r", encoding="utf-8") as f:
            solo_skill_text = f.read()
        self.assertIn("name: solo", solo_skill_text)
        self.assertNotIn("/solo-swarm", solo_skill_text)
        self.assertRegex(solo_skill_text.lower(), r"forbid.*swarm|never spawn.*swarm|do not spawn")
        self.assertIn("/teamwork", solo_skill_text)

        with open(solo_workflow_path, "r", encoding="utf-8") as f:
            solo_wf_text = f.read()
        self.assertIn("trigger: /solo", solo_wf_text)
        self.assertNotIn("/solo-swarm", solo_wf_text)

        with open(plan_skill_path, "r", encoding="utf-8") as f:
            plan_skill_text = f.read()
        self.assertIn("/solo", plan_skill_text)
        self.assertNotIn("/solo-swarm", plan_skill_text)
        self.assertIn("/teamwork", plan_skill_text)
        self.assertRegex(plan_skill_text.lower(), r"one session|single-agent")

        for gen_text in (
            sar.generate_claude_md(is_template=False),
            sar.generate_claude_md(is_template=True),
            sar.generate_cursorrules(),
            sar.generate_windsurfrules(is_template=False),
            sar.generate_cursor_mdc(is_template=False),
            sar.generate_copilot_instructions(is_template=False),
        ):
            self.assertIn("/solo", gen_text)
            self.assertNotIn("/solo-swarm", gen_text)
            self.assertIn("/teamwork", gen_text)
            self.assertRegex(gen_text.lower(), r"forbid.*swarm|no `swarm` workers|without spawning `swarm`")


if __name__ == "__main__":
    unittest.main()
