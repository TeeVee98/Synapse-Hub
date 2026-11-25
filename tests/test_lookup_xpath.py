#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""4-Scenario Unit Tests for tools/heal/lookup_xpath.py."""

import json
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tools.heal.lookup_xpath import normalize_selector_data, resolve_json_path


class TestLookupXPath:
    def test_positive_normalize_and_resolve_via_flag_and_env(self, tmp_path, monkeypatch):
        sel_file = tmp_path / "selectors.json"
        sel_file.write_text(
            json.dumps([
                {"page": "LoginPage", "constant": "BTN_LOGIN", "tag": "button", "xpath": "//button[@id='login']"},
                {"page_class": "OrderPage", "name": "TXT_QTY", "css": "input[name='qty']"},
            ]),
            encoding="utf-8",
        )
        resolved_flag = resolve_json_path(str(sel_file))
        assert resolved_flag == os.path.abspath(str(sel_file))

        monkeypatch.setenv("XPATH_DATA_FILE", str(sel_file))
        assert resolve_json_path(None) == os.path.abspath(str(sel_file))
        monkeypatch.delenv("XPATH_DATA_FILE", raising=False)
        monkeypatch.setenv("SELECTORS_JSON", str(sel_file))
        assert resolve_json_path(None) == os.path.abspath(str(sel_file))
        monkeypatch.delenv("SELECTORS_JSON", raising=False)
        monkeypatch.setenv("LOCATORS_JSON", str(sel_file))
        assert resolve_json_path(None) == os.path.abspath(str(sel_file))

        norm = normalize_selector_data(json.loads(sel_file.read_text(encoding="utf-8")))
        assert "LoginPage" in norm and "OrderPage" in norm
        assert norm["LoginPage"][0]["constant"] == "BTN_LOGIN"

    def test_boundary_invalid_or_empty_data(self, tmp_path, monkeypatch):
        assert normalize_selector_data("invalid") == {}
        assert normalize_selector_data([]) == {}
        monkeypatch.delenv("XPATH_DATA_FILE", raising=False)
        monkeypatch.delenv("SELECTORS_JSON", raising=False)
        monkeypatch.delenv("LOCATORS_JSON", raising=False)
        monkeypatch.chdir(tmp_path)
        resolved = resolve_json_path(str(tmp_path / "missing.json"))
        # Falls back to hub archive if present or None; never crashes
        assert resolved is None or os.path.isfile(resolved)

    def test_cli_page_match_keyword_match_and_not_found(self, tmp_path, monkeypatch, capsys):
        from tools.heal.lookup_xpath import main as lookup_main

        sel_file = tmp_path / "selectors.json"
        sel_file.write_text(
            json.dumps({
                "CheckoutPage": [
                    {"constant": "BTN_PAY", "tag": "button", "xpath": "//button[@id='pay']"},
                    {"name": "TXT_NOTE", "css": "textarea.note"},
                    {"selector": "[data-testid='pay-btn']"},
                ],
                "DictPage": {
                    "LINK_HELP": "//a[@href='/help']",
                },
            }),
            encoding="utf-8",
        )

        monkeypatch.setattr(sys, "argv", ["lookup_xpath.py", "checkoutpage", "--file", str(sel_file)])
        lookup_main()
        out_page = capsys.readouterr().out
        assert "- BTN_PAY (button): //button[@id='pay']" in out_page
        assert "- TXT_NOTE (element): textarea.note" in out_page
        assert "- SELECTOR (element): [data-testid='pay-btn']" in out_page

        monkeypatch.setattr(sys, "argv", ["lookup_xpath.py", "BTN_PAY", "--file", str(sel_file)])
        lookup_main()
        assert "[CheckoutPage] BTN_PAY (button): //button[@id='pay']" in capsys.readouterr().out

        monkeypatch.setattr(sys, "argv", ["lookup_xpath.py", "textarea.note", "--file", str(sel_file)])
        lookup_main()
        assert "[CheckoutPage] TXT_NOTE (element): textarea.note" in capsys.readouterr().out

        monkeypatch.setattr(sys, "argv", ["lookup_xpath.py", "pay-btn", "--file", str(sel_file)])
        lookup_main()
        assert "[CheckoutPage]  (element): [data-testid='pay-btn']" in capsys.readouterr().out

        monkeypatch.setattr(sys, "argv", ["lookup_xpath.py", "/help", "--file", str(sel_file)])
        lookup_main()
        assert "[DictPage] LINK_HELP (element): //a[@href='/help']" in capsys.readouterr().out

        monkeypatch.setattr(sys, "argv", ["lookup_xpath.py", "NONEXISTENT_XYZ_999", "--file", str(sel_file)])
        lookup_main()
        assert "No selectors found matching" in capsys.readouterr().out

        res_no_file = subprocess.run(
            [sys.executable, os.path.join(ROOT_DIR, "tools", "heal", "lookup_xpath.py"), "CheckoutPage", "--file", str(tmp_path / "missing.json")],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res_no_file.returncode in (0, 1)
