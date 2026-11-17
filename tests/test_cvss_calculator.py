#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

import pytest
from tools.cvss_calculator import (
    calculate_cvss,
    calculate_cvss_v31,
    calculate_cvss_v40,
    get_severity_rating,
    cvss_roundup,
)


def test_cvss_roundup():
    assert cvss_roundup(4.02) == 4.1
    assert cvss_roundup(4.0) == 4.0
    assert cvss_roundup(0.0) == 0.0
    assert cvss_roundup(9.82) == 9.9


def test_severity_ratings():
    assert get_severity_rating(0.0) == "NONE"
    assert get_severity_rating(2.5) == "LOW"
    assert get_severity_rating(5.5) == "MEDIUM"
    assert get_severity_rating(7.5) == "HIGH"
    assert get_severity_rating(9.8) == "CRITICAL"


def test_cvss_v31_critical_standard():
    vec = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    res = calculate_cvss_v31(vec)
    assert res["version"] == "3.1"
    assert res["base_score"] == 9.8
    assert res["severity"] == "CRITICAL"
    assert res["impact_sub_score"] > 0.9
    assert res["exploitability"] > 3.8


def test_cvss_v31_scope_changed():
    vec = "CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:C/C:H/I:H/A:H"
    res = calculate_cvss_v31(vec)
    assert res["version"] == "3.1"
    assert res["base_score"] == 9.1
    assert res["severity"] == "CRITICAL"


def test_cvss_v31_medium_and_temporal():
    vec = "CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:U/C:L/I:L/A:N/E:P/RL:O"
    res = calculate_cvss_v31(vec)
    assert res["base_score"] == 4.6
    assert res["temporal_score"] <= res["base_score"]
    assert res["severity"] == "MEDIUM"


def test_cvss_v31_zero_impact():
    vec = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N"
    res = calculate_cvss_v31(vec)
    assert res["base_score"] == 0.0
    assert res["severity"] == "NONE"


def test_cvss_v40_calculation():
    vec = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"
    res = calculate_cvss_v40(vec)
    assert res["version"] == "4.0"
    assert res["base_score"] == 10.0
    assert res["severity"] == "CRITICAL"


def test_cvss_unified_dispatcher():
    res_31 = calculate_cvss("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
    assert res_31["version"] == "3.1"
    assert res_31["base_score"] == 9.8

    res_40 = calculate_cvss("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N")
    assert res_40["version"] == "4.0"
    assert res_40["base_score"] == 10.0


def test_cvss_invalid_vectors():
    with pytest.raises(ValueError):
        calculate_cvss_v31("INVALID_VECTOR")

    with pytest.raises(ValueError):
        calculate_cvss_v31("CVSS:3.1/AV:N/AC:L")  # Missing mandatory metrics

    with pytest.raises(ValueError):
        calculate_cvss_v40("CVSS:4.0/AV:INVALID")
