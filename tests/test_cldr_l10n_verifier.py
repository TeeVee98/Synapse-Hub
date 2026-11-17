#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

from tools.cldr_l10n_verifier import (
    CLDR_LOCALES,
    pseudo_localize,
    verify_date_format,
    verify_currency_format,
    verify_collation_order,
    HTMLHardcodedStringAuditor,
)


def test_cldr_locales_registered():
    assert "en-US" in CLDR_LOCALES
    assert "vi-VN" in CLDR_LOCALES
    assert "de-DE" in CLDR_LOCALES
    assert "ja-JP" in CLDR_LOCALES
    assert "ar-SA" in CLDR_LOCALES


def test_pseudo_localization_transformation():
    original = "Hello World"
    pseudo = pseudo_localize(original)
    assert pseudo.startswith("[!!! ")
    assert pseudo.endswith(" !!!]")
    # Verifies length expansion for UI clipping detection
    assert len(pseudo) > len(original)
    # Verifies accented characters
    assert "Ĥèłłò" in pseudo or "World" not in pseudo


def test_pseudo_localization_placeholder_preservation():
    template = "Welcome, {username}! Your balance is %s."
    pseudo = pseudo_localize(template)
    # Placeholders must NOT be mangled
    assert "{username}" in pseudo
    assert "%s" in pseudo


def test_date_format_verification():
    # vi-VN: DD/MM/YYYY
    ok_vn, _ = verify_date_format("17/11/2026", "vi-VN")
    assert ok_vn is True
    fail_vn, _ = verify_date_format("11/17/2026", "vi-VN")
    assert fail_vn is False

    # en-US: MM/DD/YYYY
    ok_us, _ = verify_date_format("11/17/2026", "en-US")
    assert ok_us is True

    # de-DE: DD.MM.YYYY
    ok_de, _ = verify_date_format("17.11.2026", "de-DE")
    assert ok_de is True


def test_currency_format_verification():
    # vi-VN: e.g. 1.250.000 ₫
    ok_vn, _ = verify_currency_format("1.250.000 ₫", "vi-VN")
    assert ok_vn is True
    fail_vn, _ = verify_currency_format("$1,250.00", "vi-VN")
    assert fail_vn is False

    # en-US: $1,250.00
    ok_us, _ = verify_currency_format("$1,250.00", "en-US")
    assert ok_us is True


def test_collation_order():
    sorted_vn = ["An", "Ân", "Bình", "Cường", "Đức"]
    is_sorted, _ = verify_collation_order(sorted_vn, "vi-VN")
    assert is_sorted is True


def test_html_hardcoded_string_auditor():
    html = "<div><h1>Welcome to Dashboard</h1><p>{{ t('subtitle') }}</p></div>"
    auditor = HTMLHardcodedStringAuditor()
    auditor.feed(html)
    assert len(auditor.hardcoded_strings) >= 1
    found_texts = [s["text"] for s in auditor.hardcoded_strings]
    assert "Welcome to Dashboard" in found_texts
