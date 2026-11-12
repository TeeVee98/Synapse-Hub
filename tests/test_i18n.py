#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tests/test_i18n.py — Unit Tests for Bilingual i18n & CLI Subcommand Delegation
"""

import os
import sys
import re
import json
import unittest
import tempfile
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOLS_DIR = os.path.join(REPO_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.core.i18n import (
    resolve_language, t, MESSAGES, persist_language_preference,
    _probe_cli_flag, _probe_env_lang, _probe_config_file_lang, _probe_os_locale_lang
)
from tools.cli import (
    _extract_cli_lang, _forward_subcommand_args,
    _strip_interface_lang_flags, build_parser, _render_tiered_cli_help
)


class TestI18nModule(unittest.TestCase):
    """Validates internationalization resolution, dictionaries, and translation functions."""

    def test_messages_dictionary_completeness(self):
        """Ensures all essential keys are populated across both English and Vietnamese."""
        required_keys = [
            "banner_title", "hub_cli_description", "version_info", "usage_title", "usage_syntax",
            "core_commands_title", "advanced_highlights_title", "general_options_title",
            "opt_all", "opt_version", "opt_offline", "opt_quiet", "opt_lang",
            "tips_header", "tip_all", "tip_cmd", "tip_welcome", "tip_lang_switch",
            "cmd_doctor", "cmd_setup", "cmd_init_config", "cmd_lint",
            "cmd_verify", "cmd_export_excel", "cmd_welcome", "cmd_ui",
            "cmd_dashboard", "cmd_analyze", "cmd_mutate", "cmd_auto_heal",
            "cmd_som", "cmd_fuzz_api", "cmd_transpile",
            "cmd_help", "cmd_version", "cmd_uninstall", "cmd_clean",
            "cmd_update", "cmd_check_version", "cmd_sync_rules",
            "cmd_heal_pr", "cmd_heal", "cmd_shard", "cmd_sync_jira",
            "cmd_trend", "cmd_flaky", "cmd_canary", "cmd_watch",
            "cmd_pinpoint_failure", "cmd_ci_hook", "cmd_debt", "cmd_review",
            "cmd_safety_check", "cmd_contract_drift", "cmd_skillspector",
            "cmd_verify_author", "cmd_wcag_audit", "cmd_impact",
            "cmd_review_spec", "cmd_drift_check", "cmd_trace_data_flow",
            "cmd_distill", "cmd_gherkin", "cmd_omni_scan", "cmd_report_bug",
            "cmd_mock_shield", "cmd_visual_mask", "cmd_migrate",
            "cmd_decouple_config", "cmd_export_postman", "cmd_generate_jmx",
            "cmd_analyze_jtl", "cmd_correlate_telemetry", "cmd_analyze_newman",
            "cmd_tokens", "cmd_lookup_tc", "cmd_lookup_xpath", "cmd_generate_tc",
            "cmd_api_matrix", "cmd_canvas_diff", "cmd_validate_groovy",
            "cmd_mcp_serve", "cmd_mcp_excel", "cmd_mcp_docx", "cmd_release", "cmd_publish",
            "cmd_set_lang", "lang_saved",
            "subcommands_help",
            "typo_error", "typo_suggest", "typo_help_hint", "typo_list_hint"
        ]
        self.assertIn("en", MESSAGES)
        self.assertIn("vi", MESSAGES)
        for key in required_keys:
            self.assertIn(key, MESSAGES["en"], f"Missing key '{key}' in English dictionary")
            self.assertIn(key, MESSAGES["vi"], f"Missing key '{key}' in Vietnamese dictionary")

    def test_t_function_translation_and_formatting(self):
        """Verifies string translation and kwargs substitution."""
        # Simple translation
        en_banner = t("banner_title", lang="en")
        vi_banner = t("banner_title", lang="vi")
        self.assertIn("SYNAPSE HUB CLI", en_banner)
        self.assertIn("SYNAPSE HUB CLI", vi_banner)

        # Kwarg substitution
        ver_str = t("version_info", lang="en", version="3.2.3")
        self.assertIn("v3.2.3", ver_str)
        ver_vi = t("version_info", lang="vi", version="3.2.3")
        self.assertIn("v3.2.3", ver_vi)
        self.assertIn("Phiên bản:", ver_vi)

        # Fallback to key itself if not found
        missing = t("non_existent_key_xyz", lang="vi")
        self.assertEqual(missing, "non_existent_key_xyz")

    def test_resolve_language_precedence(self):
        """Tests 5-tier language resolution hierarchy."""
        # Tier 1: CLI flag takes absolute precedence
        self.assertEqual(resolve_language("vi"), "vi")
        self.assertEqual(resolve_language("en"), "en")
        self.assertEqual(resolve_language("VI"), "vi")
        self.assertEqual(resolve_language("EN"), "en")

        # Tier 2: ENV variable
        orig_env = os.environ.get("SYNAPSE_LANG")
        try:
            os.environ["SYNAPSE_LANG"] = "vi"
            self.assertEqual(resolve_language(None), "vi")
            os.environ["SYNAPSE_LANG"] = "en"
            self.assertEqual(resolve_language(None), "en")
        finally:
            if orig_env is not None:
                os.environ["SYNAPSE_LANG"] = orig_env
            else:
                os.environ.pop("SYNAPSE_LANG", None)

        # Tier 3: .synapse.json config
        with tempfile.TemporaryDirectory() as tmp_dir:
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmp_dir)
                cfg_path = os.path.join(tmp_dir, ".synapse.json")
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump({"language": "vi"}, f)
                # Ensure no ENV
                orig_env_val = os.environ.pop("SYNAPSE_LANG", None)
                try:
                    self.assertEqual(resolve_language(None), "vi")
                finally:
                    if orig_env_val:
                        os.environ["SYNAPSE_LANG"] = orig_env_val
            finally:
                os.chdir(orig_cwd)

    def test_resolve_language_malformed_config_fallback(self):
        """Ensures corrupted .synapse.json falls back safely to default or OS locale."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmp_dir)
                cfg_path = os.path.join(tmp_dir, ".synapse.json")
                with open(cfg_path, "w", encoding="utf-8") as f:
                    f.write("{ invalid json corrupted ...")
                orig_env = os.environ.pop("SYNAPSE_LANG", None)
                try:
                    res = resolve_language(None)
                    self.assertIn(res, ("en", "vi"))
                finally:
                    if orig_env:
                        os.environ["SYNAPSE_LANG"] = orig_env
            finally:
                os.chdir(orig_cwd)

    def test_persist_language_preference_local_and_global(self):
        """Validates persisting language to target dir, SYNAPSE_CONFIG_PATH, and reading back."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Persist to explicit target_dir
            out_file = persist_language_preference("vi", target_dir=tmp_dir)
            self.assertTrue(os.path.isfile(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("language"), "vi")

            # 2. Persist with SYNAPSE_CONFIG_PATH
            custom_cfg = os.path.join(tmp_dir, "custom_synapse.json")
            orig_env = os.environ.get("SYNAPSE_CONFIG_PATH")
            orig_lang = os.environ.pop("SYNAPSE_LANG", None)
            try:
                os.environ["SYNAPSE_CONFIG_PATH"] = custom_cfg
                persist_language_preference("en")
                self.assertTrue(os.path.isfile(custom_cfg))
                with open(custom_cfg, "r", encoding="utf-8") as f:
                    self.assertEqual(json.load(f).get("language"), "en")
                self.assertEqual(resolve_language(None), "en")

                persist_language_preference("vi")
                self.assertEqual(resolve_language(None), "vi")
            finally:
                if orig_env is not None:
                    os.environ["SYNAPSE_CONFIG_PATH"] = orig_env
                else:
                    os.environ.pop("SYNAPSE_CONFIG_PATH", None)
                if orig_lang is not None:
                    os.environ["SYNAPSE_LANG"] = orig_lang

            # 3. Invalid language raises ValueError
            with self.assertRaises(ValueError):
                persist_language_preference("french")

    def test_default_language_is_strictly_english_without_config(self):
        """Verifies that English is strictly default even when system locale is Vietnamese."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            orig_env = os.environ.get("SYNAPSE_CONFIG_PATH")
            orig_lang = os.environ.pop("SYNAPSE_LANG", None)
            orig_lc = os.environ.get("LC_ALL")
            orig_lmsg = os.environ.get("LC_MESSAGES")
            orig_os_lang = os.environ.get("LANG")
            non_existent_cfg = os.path.join(tmp_dir, "no_cfg.json")
            try:
                os.environ["SYNAPSE_CONFIG_PATH"] = non_existent_cfg
                os.environ["LC_ALL"] = "vi_VN.UTF-8"
                os.environ["LC_MESSAGES"] = "vi_VN.UTF-8"
                os.environ["LANG"] = "vi_VN.UTF-8"

                # Without explicit choice/persistence, resolve_language MUST return "en"
                self.assertEqual(resolve_language(None), "en")
            finally:
                if orig_env is not None:
                    os.environ["SYNAPSE_CONFIG_PATH"] = orig_env
                else:
                    os.environ.pop("SYNAPSE_CONFIG_PATH", None)
                if orig_lang:
                    os.environ["SYNAPSE_LANG"] = orig_lang
                if orig_lc:
                    os.environ["LC_ALL"] = orig_lc
                else:
                    os.environ.pop("LC_ALL", None)
                if orig_lmsg:
                    os.environ["LC_MESSAGES"] = orig_lmsg
                else:
                    os.environ.pop("LC_MESSAGES", None)
                if orig_os_lang:
                    os.environ["LANG"] = orig_os_lang
                else:
                    os.environ.pop("LANG", None)

    def test_probe_functions_isolated(self):
        """Verifies each isolated probe in tools.core.i18n."""
        # _probe_cli_flag
        self.assertEqual(_probe_cli_flag("vi"), "vi")
        self.assertEqual(_probe_cli_flag("VI"), "vi")
        self.assertEqual(_probe_cli_flag("en"), "en")
        self.assertEqual(_probe_cli_flag("--lang=vi"), "vi")
        self.assertEqual(_probe_cli_flag("-l=en"), "en")
        self.assertIsNone(_probe_cli_flag("--lang=python"))
        self.assertIsNone(_probe_cli_flag(None))
        self.assertIsNone(_probe_cli_flag("fr"))
        self.assertIsNone(_probe_cli_flag(""))

        # _probe_env_lang
        orig_env = os.environ.get("SYNAPSE_LANG")
        try:
            os.environ["SYNAPSE_LANG"] = "vi"
            self.assertEqual(_probe_env_lang(), "vi")
            os.environ["SYNAPSE_LANG"] = "en"
            self.assertEqual(_probe_env_lang(), "en")
            os.environ["SYNAPSE_LANG"] = "invalid"
            self.assertIsNone(_probe_env_lang())
            os.environ.pop("SYNAPSE_LANG", None)
            self.assertIsNone(_probe_env_lang())
        finally:
            if orig_env is not None:
                os.environ["SYNAPSE_LANG"] = orig_env
            else:
                os.environ.pop("SYNAPSE_LANG", None)

        # _probe_config_file_lang
        with tempfile.TemporaryDirectory() as tmp_dir:
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmp_dir)
                self.assertIsNone(_probe_config_file_lang())
                cfg_path = os.path.join(tmp_dir, ".synapse.json")
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump({"language": "vi"}, f)
                self.assertEqual(_probe_config_file_lang(), "vi")
                # Non-dictionary JSON should safely return None without throwing
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(["vi", "en"], f)
                self.assertIsNone(_probe_config_file_lang())
            finally:
                os.chdir(orig_cwd)

        # _probe_os_locale_lang
        orig_lc = os.environ.get("LC_ALL")
        try:
            os.environ["LC_ALL"] = "vi_VN.UTF-8"
            self.assertEqual(_probe_os_locale_lang(), "vi")
            os.environ["LC_ALL"] = "en_US.UTF-8"
            self.assertEqual(_probe_os_locale_lang(), "en")
            os.environ["LC_ALL"] = "fr_FR.UTF-8"
            self.assertIsNone(_probe_os_locale_lang())
        finally:
            if orig_lc is not None:
                os.environ["LC_ALL"] = orig_lc
            else:
                os.environ.pop("LC_ALL", None)



class TestCliBilingualAndDelegation(unittest.TestCase):
    """Validates that cli.py respects --lang and delegates subcommands cleanly."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.fake_cfg = os.path.join(cls.temp_dir.name, ".synapse.json")
        cls.orig_env_cfg = os.environ.get("SYNAPSE_CONFIG_PATH")
        os.environ["SYNAPSE_CONFIG_PATH"] = cls.fake_cfg

        # Backup ~/.synapse.json to prevent cross-test filesystem leakage
        cls.home_cfg = os.path.expanduser("~/.synapse.json")
        cls.home_cfg_backup = None
        if os.path.isfile(cls.home_cfg):
            try:
                with open(cls.home_cfg, "r", encoding="utf-8") as f:
                    cls.home_cfg_backup = f.read()
            except Exception as _err:
                _ = _err

    @classmethod
    def tearDownClass(cls):
        if cls.orig_env_cfg is not None:
            os.environ["SYNAPSE_CONFIG_PATH"] = cls.orig_env_cfg
        else:
            os.environ.pop("SYNAPSE_CONFIG_PATH", None)
        try:
            cls.temp_dir.cleanup()
        except Exception as _err:
            _ = _err

        # Restore ~/.synapse.json
        if cls.home_cfg_backup is not None:
            try:
                with open(cls.home_cfg, "w", encoding="utf-8") as f:
                    f.write(cls.home_cfg_backup)
            except Exception as _err:
                _ = _err
        elif os.path.isfile(cls.home_cfg):
            try:
                os.remove(cls.home_cfg)
            except Exception as _err:
                _ = _err

    def test_cli_lang_en_and_vi_banners(self):
        """Tests that --lang en and --lang vi produce properly localized CLI banners."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")

        # English
        res_en = subprocess.run(
            [sys.executable, cli_tool, "--lang", "en", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_en.returncode, 0)
        self.assertIn("CORE & DAILY WORKFLOWS", res_en.stdout)
        self.assertIn("GENERAL OPTIONS", res_en.stdout)

        # Vietnamese
        res_vi = subprocess.run(
            [sys.executable, cli_tool, "--lang", "vi", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_vi.returncode, 0)
        self.assertIn("LỆNH CỐT LÕI & THƯỜNG DÙNG", res_vi.stdout)
        self.assertIn("TÙY CHỌN CHUNG", res_vi.stdout)

    def test_cli_subcommand_help_delegation(self):
        """Verifies that subcommand --help forwards to underlying tools with detailed options."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")

        # 1. mutate --help should show --min-score and --baseline
        res_mutate = subprocess.run(
            [sys.executable, cli_tool, "mutate", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_mutate.returncode, 0)
        self.assertIn("--min-score", res_mutate.stdout)
        self.assertIn("--baseline", res_mutate.stdout)

        # 2. verify --help should show --mode and --test-cmd
        res_verify = subprocess.run(
            [sys.executable, cli_tool, "verify", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_verify.returncode, 0)
        self.assertIn("--mode", res_verify.stdout)
        self.assertIn("--test-cmd", res_verify.stdout)

        # 3. lint --help should show --strict and --format
        res_lint = subprocess.run(
            [sys.executable, cli_tool, "lint", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_lint.returncode, 0)
        self.assertIn("--strict", res_lint.stdout)
        self.assertIn("--format", res_lint.stdout)

    def test_cli_typo_bilingual_messages(self):
        """Verifies fuzzy typo messages in both English and Vietnamese."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")

        # English typo
        res_en = subprocess.run(
            [sys.executable, cli_tool, "--lang", "en", "docter"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_en.returncode, 2)
        self.assertIn("Command 'docter' does not exist", res_en.stderr)
        self.assertIn("Did you mean", res_en.stderr)

        # Vietnamese typo
        res_vi = subprocess.run(
            [sys.executable, cli_tool, "--lang", "vi", "docter"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_vi.returncode, 2)
        self.assertIn("Lệnh 'docter' không tồn tại", res_vi.stderr)
        self.assertIn("Có phải ý bạn là", res_vi.stderr)

    def test_english_typo_no_vietnamese_leakage(self):
        """Verifies that English typo suggestion has zero Vietnamese text contamination."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        res_en = subprocess.run(
            [sys.executable, cli_tool, "--lang", "en", "docter"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res_en.returncode, 2)
        self.assertNotIn("Có phải ý bạn là", res_en.stderr)

    def test_cli_lang_short_flag(self):
        """Verifies that -l short flag operates identically to --lang."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        res = subprocess.run(
            [sys.executable, cli_tool, "-l", "vi", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("LỆNH CỐT LÕI & THƯỜNG DÙNG", res.stdout)

    def test_cli_subcommand_forwarding_with_lang_flag(self):
        """Verifies that global --lang flag passed after subcommand does not break delegated tools."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        res = subprocess.run(
            [sys.executable, cli_tool, "verify", "--mode", "hub", "--lang", "vi", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("--mode", res.stdout)

    def test_extract_cli_lang_and_immediate_env_propagation(self):
        """Tests that _extract_cli_lang parses equals syntax and immediately sets SYNAPSE_LANG."""
        orig_argv = list(sys.argv)
        orig_env = os.environ.get("SYNAPSE_LANG")
        try:
            # Short flag with equals syntax
            os.environ.pop("SYNAPSE_LANG", None)
            sys.argv = ["agent-qa", "-l=vi"]
            self.assertEqual(_extract_cli_lang(), "vi")
            self.assertEqual(os.environ.get("SYNAPSE_LANG"), "vi")

            os.environ.pop("SYNAPSE_LANG", None)
            sys.argv = ["agent-qa", "-l=en"]
            self.assertEqual(_extract_cli_lang(), "en")
            self.assertEqual(os.environ.get("SYNAPSE_LANG"), "en")

            # Long flag with equals syntax
            os.environ.pop("SYNAPSE_LANG", None)
            sys.argv = ["agent-qa", "--lang=vi"]
            self.assertEqual(_extract_cli_lang(), "vi")
            self.assertEqual(os.environ.get("SYNAPSE_LANG"), "vi")

            # Space separated
            os.environ.pop("SYNAPSE_LANG", None)
            sys.argv = ["agent-qa", "-l", "vi"]
            self.assertEqual(_extract_cli_lang(), "vi")
            self.assertEqual(os.environ.get("SYNAPSE_LANG"), "vi")

            # Test with explicit argv list argument
            os.environ.pop("SYNAPSE_LANG", None)
            self.assertEqual(_extract_cli_lang(["agent-qa", "-l=en"]), "en")
            self.assertEqual(os.environ.get("SYNAPSE_LANG"), "en")

            # Invalid / missing flag leaves env alone
            os.environ.pop("SYNAPSE_LANG", None)
            sys.argv = ["agent-qa", "verify"]
            self.assertIsNone(_extract_cli_lang())
            self.assertNotIn("SYNAPSE_LANG", os.environ)
        finally:
            sys.argv = orig_argv
            if orig_env is not None:
                os.environ["SYNAPSE_LANG"] = orig_env
            else:
                os.environ.pop("SYNAPSE_LANG", None)

    def test_forward_subcommand_args_filters_equals_flags(self):
        """Tests that _forward_subcommand_args strips all -l= and --lang= forms."""
        orig_argv = list(sys.argv)
        try:
            sys.argv = [
                "agent-qa", "verify", "--mode", "hub",
                "-l=vi", "--lang=en", "-l", "vi", "--test-cmd", "pytest"
            ]
            forwarded = _forward_subcommand_args("verify")
            self.assertIn("--mode", forwarded)
            self.assertIn("hub", forwarded)
            self.assertIn("--test-cmd", forwarded)
            self.assertIn("pytest", forwarded)
            self.assertNotIn("-l=vi", forwarded)
            self.assertNotIn("--lang=en", forwarded)
            self.assertNotIn("-l", forwarded)
            self.assertNotIn("vi", forwarded)
        finally:
            sys.argv = orig_argv

    def test_cli_lang_equals_syntax_cli_execution(self):
        """Verifies CLI execution with -l=vi and -l=en flags."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        env = dict(os.environ, SYNAPSE_NON_INTERACTIVE="1")

        # -l=vi
        res_vi = subprocess.run(
            [sys.executable, cli_tool, "-l=vi", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_vi.returncode, 0)
        self.assertIn("LỆNH CỐT LÕI & THƯỜNG DÙNG", res_vi.stdout)

        # -l=en
        res_en = subprocess.run(
            [sys.executable, cli_tool, "-l=en", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_en.returncode, 0)
        self.assertIn("CORE & DAILY WORKFLOWS", res_en.stdout)

    def test_cli_unknown_flag_rejection_at_root(self):
        """Verifies that unknown flags at root parser reject with code 2 (POSIX error)."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        env = dict(os.environ, SYNAPSE_NON_INTERACTIVE="1")

        # 1. Invalid long flag
        res1 = subprocess.run(
            [sys.executable, cli_tool, "--invalid-flag"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res1.returncode, 2)
        self.assertIn("unrecognized arguments: --invalid-flag", res1.stderr)

        # 2. Invalid short flag
        res2 = subprocess.run(
            [sys.executable, cli_tool, "-z"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res2.returncode, 2)
        self.assertIn("unrecognized arguments: -z", res2.stderr)

        # 3. Known flag followed by unknown flag without subcommand
        res3 = subprocess.run(
            [sys.executable, cli_tool, "--lang", "vi", "--unknown-flag"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res3.returncode, 2)
        self.assertIn("unrecognized arguments: --unknown-flag", res3.stderr)

    def test_cli_subcommand_forwarding_filters_equals_syntax(self):
        """Verifies that -l=vi and --lang=en forwarded to underlying tools don't crash."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        env = dict(os.environ, SYNAPSE_NON_INTERACTIVE="1")

        res_vi = subprocess.run(
            [sys.executable, cli_tool, "verify", "--mode", "hub", "-l=vi", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_vi.returncode, 0)
        self.assertIn("--mode", res_vi.stdout)

        res_en = subprocess.run(
            [sys.executable, cli_tool, "verify", "--mode", "hub", "--lang=en", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_en.returncode, 0)
        self.assertIn("--mode", res_en.stdout)

    def test_cli_all_descriptions_localized(self):
        """Verifies that --all displays pure English or pure Vietnamese descriptions without mixed language."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        env = dict(os.environ, SYNAPSE_NON_INTERACTIVE="1")

        # Pure English in --all
        res_en = subprocess.run(
            [sys.executable, cli_tool, "--all", "--lang", "en"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_en.returncode, 0)
        norm_en = re.sub(r"\s+", " ", res_en.stdout)
        self.assertIn("Available subcommands", norm_en)
        self.assertIn("Execute 11 Quality Gates Definition of Done (DoD) verification", norm_en)
        self.assertIn("Launch interactive visual landing page introducing Synapse Hub", norm_en)
        self.assertNotIn("Khởi chạy Landing Page", norm_en)
        self.assertNotIn("Kiểm tra toàn diện 11 Cổng Chất Lượng", norm_en)

        # Pure Vietnamese in --all
        res_vi = subprocess.run(
            [sys.executable, cli_tool, "--all", "--lang", "vi"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_vi.returncode, 0)
        norm_vi = re.sub(r"\s+", " ", res_vi.stdout)
        self.assertIn("Danh sách các lệnh khả dụng", norm_vi)
        self.assertIn("Kiểm tra toàn diện 11 Cổng Chất Lượng DoD (Definition of Done)", norm_vi)
        self.assertIn("Khởi chạy Landing Page trực quan giới thiệu các trụ cột của Synapse Hub", norm_vi)
        self.assertNotIn("Execute 11 Quality Gates Definition of Done", norm_vi)

    def test_forward_subcommand_args_preserves_tool_language_options(self):
        """Validates that tool-specific language arguments (e.g. mock-shield --lang=python) are preserved."""
        orig_argv = list(sys.argv)
        try:
            # mock-shield with --lang=python and -l=vi
            sys.argv = ["agent-qa", "mock-shield", "--lang=python", "-l=vi"]
            forwarded = _forward_subcommand_args("mock-shield")
            self.assertIn("--lang=python", forwarded)
            self.assertNotIn("-l=vi", forwarded)

            # mock-shield with space syntax --lang cypress
            sys.argv = ["agent-qa", "mock-shield", "--lang", "cypress", "--lang=en"]
            forwarded_cypress = _forward_subcommand_args("mock-shield")
            self.assertIn("--lang", forwarded_cypress)
            self.assertIn("cypress", forwarded_cypress)
            self.assertNotIn("--lang=en", forwarded_cypress)
        finally:
            sys.argv = orig_argv

    def test_cli_lang_uppercase_flags(self):
        """Verifies that uppercase flags like -l=VI and --lang EN work seamlessly."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        env = dict(os.environ, SYNAPSE_NON_INTERACTIVE="1")

        res_vi = subprocess.run(
            [sys.executable, cli_tool, "-l=VI", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_vi.returncode, 0)
        self.assertIn("LỆNH CỐT LÕI & THƯỜNG DÙNG", res_vi.stdout)

        res_en = subprocess.run(
            [sys.executable, cli_tool, "--lang", "EN", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_en.returncode, 0)
        self.assertIn("CORE & DAILY WORKFLOWS", res_en.stdout)

    def test_cli_invalid_option_choice_error(self):
        """Verifies that invalid -l/--lang choice reports POSIX option error rather than command error."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        env = dict(os.environ, SYNAPSE_NON_INTERACTIVE="1")

        res = subprocess.run(
            [sys.executable, cli_tool, "-l=fr"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res.returncode, 2)
        self.assertIn("argument -l/--lang: invalid choice: 'fr'", res.stderr)
        self.assertNotIn("Command 'fr' does not exist", res.stderr)
        self.assertNotIn("Lệnh 'fr' không tồn tại", res.stderr)

    def test_strip_interface_lang_flags_and_domain_invariant(self):
        """Validates _strip_interface_lang_flags respects domain invariant on language values."""
        # Handles None and empty lists defensively
        self.assertEqual(_strip_interface_lang_flags(None), [])
        self.assertEqual(_strip_interface_lang_flags([]), [])

        # Strips only en/vi
        self.assertEqual(_strip_interface_lang_flags(["--lang", "vi", "test"]), ["test"])
        self.assertEqual(_strip_interface_lang_flags(["-l", "en", "run"]), ["run"])
        self.assertEqual(_strip_interface_lang_flags(["--lang=vi", "lint"]), ["lint"])
        self.assertEqual(_strip_interface_lang_flags(["-l=en", "verify"]), ["verify"])

        # Preserves non-interface languages
        self.assertEqual(
            _strip_interface_lang_flags(["--lang=python", "mock-shield"]),
            ["--lang=python", "mock-shield"]
        )
        self.assertEqual(
            _strip_interface_lang_flags(["--lang", "cypress", "mock-shield"]),
            ["--lang", "cypress", "mock-shield"]
        )

    def test_build_parser_and_render_tiered_cli_help(self):
        """Verifies build_parser creates a fully configured parser and _render_tiered_cli_help renders properly."""
        parser_en = build_parser("en")
        self.assertEqual(parser_en.prog, "agent-qa")
        self.assertEqual(parser_en.lang, "en")

        parser_vi = build_parser("vi")
        self.assertEqual(parser_vi.lang, "vi")

        rendered_en = _render_tiered_cli_help("en")
        self.assertIn("CORE & DAILY WORKFLOWS", rendered_en)

        rendered_vi = _render_tiered_cli_help("vi")
        self.assertIn("LỆNH CỐT LÕI & THƯỜNG DÙNG", rendered_vi)

    def test_language_switch_suggestion_present(self):
        """Verifies CLI help output presents a clear tip for switching languages."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        env = dict(os.environ, SYNAPSE_NON_INTERACTIVE="1")

        # English switch tip
        res_en = subprocess.run(
            [sys.executable, cli_tool, "--lang", "en", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_en.returncode, 0)
        self.assertIn("Switch language: agent-qa --lang vi (Vietnamese) | agent-qa --lang en (English)", res_en.stdout)

        # Vietnamese switch tip
        res_vi = subprocess.run(
            [sys.executable, cli_tool, "--lang", "vi", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_vi.returncode, 0)
        self.assertIn("Chuyển đổi ngôn ngữ: agent-qa --lang vi (Tiếng Việt) | agent-qa --lang en (Tiếng Anh)", res_vi.stdout)

    def test_set_lang_command(self):
        """Verifies agent-qa set-lang persists preference and updates subsequent commands."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_cfg = os.path.join(tmp_dir, "test_synapse.json")
            env = dict(os.environ, SYNAPSE_CONFIG_PATH=test_cfg, SYNAPSE_NON_INTERACTIVE="1")
            env.pop("SYNAPSE_LANG", None)

            # 1. Set to Vietnamese
            res_set_vi = subprocess.run(
                [sys.executable, cli_tool, "set-lang", "vi"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            self.assertEqual(res_set_vi.returncode, 0)
            self.assertIn("Đã lưu cấu hình ngôn ngữ giao diện", res_set_vi.stdout)

            # 2. Subsequent command without --lang runs in Vietnamese
            res_sub_vi = subprocess.run(
                [sys.executable, cli_tool, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            self.assertEqual(res_sub_vi.returncode, 0)
            self.assertIn("LỆNH CỐT LÕI & THƯỜNG DÙNG", res_sub_vi.stdout)

            # 3. Set to English
            res_set_en = subprocess.run(
                [sys.executable, cli_tool, "set-lang", "en"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            self.assertEqual(res_set_en.returncode, 0)
            self.assertIn("Interface language preference saved", res_set_en.stdout)

            # 4. Subsequent command without --lang runs in English
            res_sub_en = subprocess.run(
                [sys.executable, cli_tool, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            self.assertEqual(res_sub_en.returncode, 0)
            self.assertIn("CORE & DAILY WORKFLOWS", res_sub_en.stdout)

    def test_cli_lang_persistence_via_flag(self):
        """Verifies that passing --lang persists preference so subsequent commands use it."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_cfg = os.path.join(tmp_dir, "test_synapse.json")
            env = dict(os.environ, SYNAPSE_CONFIG_PATH=test_cfg, SYNAPSE_NON_INTERACTIVE="1")
            env.pop("SYNAPSE_LANG", None)

            # 1. Standalone --lang vi switches and confirms immediately
            res_flag_vi = subprocess.run(
                [sys.executable, cli_tool, "--lang", "vi"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=5
            )
            self.assertEqual(res_flag_vi.returncode, 0)
            self.assertIn("Đã lưu cấu hình ngôn ngữ giao diện", res_flag_vi.stdout)

            # 2. Subsequent command without --lang must now use Vietnamese
            res2 = subprocess.run(
                [sys.executable, cli_tool, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=5
            )
            self.assertEqual(res2.returncode, 0)
            self.assertIn("LỆNH CỐT LÕI & THƯỜNG DÙNG", res2.stdout)

            # 3. Standalone -l en switches back and confirms
            res_flag_en = subprocess.run(
                [sys.executable, cli_tool, "-l", "en"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=5
            )
            self.assertEqual(res_flag_en.returncode, 0)
            self.assertIn("Interface language preference saved", res_flag_en.stdout)

            # 4. Subsequent command without --lang must now use English
            res3 = subprocess.run(
                [sys.executable, cli_tool, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=5
            )
            self.assertEqual(res3.returncode, 0)
            self.assertIn("CORE & DAILY WORKFLOWS", res3.stdout)

    def test_set_lang_command_edge_cases(self):
        """Verifies agent-qa set-lang with zero args, invalid args, and localized output."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_cfg = os.path.join(tmp_dir, "test_synapse.json")
            env = dict(os.environ, SYNAPSE_CONFIG_PATH=test_cfg, SYNAPSE_NON_INTERACTIVE="1")
            env.pop("SYNAPSE_LANG", None)

            # Query current language without args
            res_cur_en = subprocess.run(
                [sys.executable, cli_tool, "set-lang"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            self.assertEqual(res_cur_en.returncode, 0)
            self.assertIn("Current interface language: English", res_cur_en.stdout)

            # Set to vi
            res_set = subprocess.run(
                [sys.executable, cli_tool, "set-lang", "vi"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            self.assertEqual(res_set.returncode, 0)

            # Query current language in vi mode
            res_cur_vi = subprocess.run(
                [sys.executable, cli_tool, "set-lang"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            self.assertEqual(res_cur_vi.returncode, 0)
            self.assertIn("Ngôn ngữ giao diện hiện tại: Tiếng Việt", res_cur_vi.stdout)

    def test_subcommand_helps_no_mixed_strings(self):
        """Verifies that subcommand helps under --lang en contain 0 Vietnamese text, and under --lang vi contain Vietnamese."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        env = dict(os.environ, SYNAPSE_NON_INTERACTIVE="1")

        # Test key subcommands across all categories
        sample_subcmds = [
            "doctor", "welcome", "init-config", "ui", "dashboard",
            "watch", "pinpoint-failure", "debt", "review", "skillspector",
            "transpile", "omni-scan", "migrate", "tokens", "lookup-tc",
            "export-excel", "release", "publish"
        ]

        import re
        import argparse
        vn_char = re.compile(r"[\u00C0-\u1EF9]")

        # 1. Subprocess boundary test: Execute a representative sample via actual subprocess to verify CLI OS boundary
        for subcmd in ["doctor", "welcome"]:
            res_en = subprocess.run(
                [sys.executable, cli_tool, "--lang", "en", subcmd, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            self.assertEqual(res_en.returncode, 0, f"Subcommand {subcmd} --help failed in en")
            en_lines = [l for l in res_en.stdout.splitlines() if "Thế Vị" not in l]
            for line in en_lines:
                self.assertIsNone(vn_char.search(line), f"Unexpected Vietnamese text in en mode for {subcmd}: {line}")
            self.assertIn("💡 Switch language:", res_en.stdout)

            res_vi = subprocess.run(
                [sys.executable, cli_tool, "--lang", "vi", subcmd, "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            self.assertEqual(res_vi.returncode, 0, f"Subcommand {subcmd} --help failed in vi")
            self.assertIn("Tùy chọn:", res_vi.stdout)
            self.assertIn("Hiển thị hướng dẫn sử dụng và thoát", res_vi.stdout)
            self.assertIn("💡 Chuyển đổi ngôn ngữ:", res_vi.stdout)

        # 2. Fast in-process validation: Verify all 18 subcommands generate pure localized help text
        p_en = build_parser("en")
        subparsers_en = next(a.choices for a in p_en._actions if isinstance(a, argparse._SubParsersAction))
        for subcmd in sample_subcmds:
            sp = subparsers_en[subcmd]
            out = sp.format_help()
            en_lines = [l for l in out.splitlines() if "Thế Vị" not in l]
            for line in en_lines:
                self.assertIsNone(vn_char.search(line), f"Unexpected Vietnamese text in en mode for {subcmd}: {line}")
            self.assertIn("💡 Switch language:", out)

        p_vi = build_parser("vi")
        subparsers_vi = next(a.choices for a in p_vi._actions if isinstance(a, argparse._SubParsersAction))
        for subcmd in sample_subcmds:
            sp = subparsers_vi[subcmd]
            out = sp.format_help()
            self.assertIn("Tùy chọn:", out)
            self.assertIn("Hiển thị hướng dẫn sử dụng và thoát", out)
            self.assertIn("💡 Chuyển đổi ngôn ngữ:", out)

    def test_all_flag_no_mixed_strings(self):
        """Verifies that --all in en and vi modes contains clean localized section titles and options."""
        cli_tool = os.path.join(TOOLS_DIR, "cli.py")
        env = dict(os.environ, SYNAPSE_NON_INTERACTIVE="1")

        # In Vietnamese
        res_vi = subprocess.run(
            [sys.executable, cli_tool, "--lang", "vi", "--all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_vi.returncode, 0)
        self.assertIn("Tham số và lệnh khả dụng:", res_vi.stdout)
        self.assertIn("Tùy chọn chung:", res_vi.stdout)
        self.assertIn("Hiển thị hướng dẫn sử dụng và thoát", res_vi.stdout)
        self.assertNotIn("positional arguments:", res_vi.stdout)
        self.assertNotIn("show this help message and exit", res_vi.stdout)

        # In English
        res_en = subprocess.run(
            [sys.executable, cli_tool, "--lang", "en", "--all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env
        )
        self.assertEqual(res_en.returncode, 0)
        self.assertIn("positional arguments:", res_en.stdout)
        self.assertIn("general options:", res_en.stdout)
        self.assertIn("show this help message and exit", res_en.stdout)
        self.assertNotIn("Tham số và lệnh khả dụng:", res_en.stdout)
        self.assertNotIn("Tùy chọn chung:", res_en.stdout)


if __name__ == "__main__":
    unittest.main()
