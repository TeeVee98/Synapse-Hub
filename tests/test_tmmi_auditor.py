#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

from tools.contrib.tmmi_auditor import (
    TMMI_LEVEL_CRITERIA,
    audit_tmmi_maturity,
)


def test_tmmi_criteria_definitions():
    assert 2 in TMMI_LEVEL_CRITERIA
    assert 3 in TMMI_LEVEL_CRITERIA
    assert 4 in TMMI_LEVEL_CRITERIA
    assert 5 in TMMI_LEVEL_CRITERIA

    for lvl, data in TMMI_LEVEL_CRITERIA.items():
        assert "title" in data
        assert "description" in data
        assert len(data["checks"]) >= 4
        for chk in data["checks"]:
            assert "id" in chk
            assert "name" in chk
            assert "path" in chk


def test_audit_tmmi_maturity_execution():
    res = audit_tmmi_maturity()
    assert res["standard"].startswith("TMMi")
    assert res["certified_maturity_level"] in (2, 3, 4, 5)
    assert "maturity_summary" in res

    for lvl in ("level_2", "level_3", "level_4", "level_5"):
        assert lvl in res["maturity_summary"]
        summary = res["maturity_summary"][lvl]
        assert "compliance_pct" in summary
        assert "passed_checks" in summary
