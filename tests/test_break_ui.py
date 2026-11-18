# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tests/test_break_ui.py — Unit tests for tools.break_ui_generator
"""

from tools.design.break_ui_generator import (
    get_break_strings,
    get_break_localization,
    get_break_numbers,
    get_break_viewports,
    generate_all_break_payloads,
)


def test_get_break_strings():
    strings = get_break_strings()
    assert len(strings) >= 5
    names = [s["name"] for s in strings]
    assert "unspaced_2000_chars" in names
    assert "zalgo_corrupted_text" in names
    assert "zero_width_spaces" in names
    # Verify unspaced length
    unspaced = next(s for s in strings if s["name"] == "unspaced_2000_chars")
    assert len(unspaced["value"]) == 2000


def test_get_break_localization():
    loc = get_break_localization()
    assert len(loc) >= 4
    names = [l["name"] for l in loc]
    assert "rtl_arabic" in names
    assert "german_compound_noun" in names
    assert "vietnamese_complex_tones" in names


def test_get_break_numbers():
    numbers = get_break_numbers()
    assert len(numbers) >= 5
    names = [n["name"] for n in numbers]
    assert "max_safe_integer_js" in names
    assert "int64_max" in names
    safe_int = next(n for n in numbers if n["name"] == "max_safe_integer_js")
    assert safe_int["value"] == 9007199254740991


def test_get_break_viewports():
    viewports = get_break_viewports()
    assert len(viewports) >= 5
    for vp in viewports:
        assert vp["width"] > 0
        assert vp["height"] > 0
        assert vp["device_scale"] >= 1.0


def test_generate_all_break_payloads():
    payload = generate_all_break_payloads()
    assert payload["version"] == "1.0.0"
    assert "categories" in payload
    assert payload["total_cases"] >= 20
    assert "strings" in payload["categories"]
    assert "localization" in payload["categories"]
    assert "numbers" in payload["categories"]
    assert "viewports" in payload["categories"]
