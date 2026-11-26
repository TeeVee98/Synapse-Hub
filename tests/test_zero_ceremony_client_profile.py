#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
4-Scenario Verification Suite for M10:
  Zero-Ceremony Client/Starter Profile (`< 35`-line client bridge, zero Hub path leaks,
  `gate_11_token_reduction: False`, `ceremony_level: "minimal"`, and `< 2s` Spoke verification).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools.core.init_config import build_default_config
from tools.core.sync_agent_rules import (
    ZeroCeremonyProfileDTO,
    generate_client_bridge_markdown,
)


# ---------------------------------------------------------------------------
# 1. POSITIVE: Starter config & <35-line Zero-Ceremony bridge with 0 Hub leaks
# ---------------------------------------------------------------------------


def test_positive_starter_profile_config_and_zero_ceremony_bridge(tmp_path: Path) -> None:
    starter_cfg = build_default_config(project_name="SpokeApp", profile="starter")
    qg = starter_cfg["quality_gates"]
    assert qg["profile"] == "starter"
    assert qg["ceremony_level"] == "minimal"
    assert qg["mutation_min_score"] == 0
    assert qg["gates"]["gate_11_token_reduction"] is False
    assert qg["gates"]["gate_8_micro_mutator"] is False
    assert qg["gates"]["gate_7_infer_linter"] is True

    standard_cfg = build_default_config(project_name="SpokeStd", profile="standard")
    assert standard_cfg["quality_gates"]["ceremony_level"] == "standard"
    assert standard_cfg["quality_gates"]["gates"]["gate_11_token_reduction"] is False

    dto = generate_client_bridge_markdown(profile="starter")
    assert isinstance(dto, ZeroCeremonyProfileDTO)
    assert dto.profile == "starter"
    assert dto.bridge_line_count < 35
    assert dto.hub_paths_leaked == 0
    assert dto.mutation_required is False
    assert dto.passed is True
    assert "Clean POM" in dto.content
    assert "Smart Waits" in dto.content
    assert "Zero Fake-Pass" in dto.content or "Fake-Pass" in dto.content
    assert "solo_runner.py" not in dto.content
    assert "tools/core/" not in dto.content
    assert "Thế Vị (@TeeVee98)" in dto.content

    # Fast < 2s Spoke target verification loop check
    t0 = time.perf_counter()
    cfg_path = tmp_path / ".synapse.json"
    cfg_path.write_text(json.dumps(starter_cfg, indent=2), encoding="utf-8")
    bridge_path = tmp_path / "CLAUDE.md"
    bridge_path.write_text(dto.content, encoding="utf-8")
    elapsed_sec = time.perf_counter() - t0
    assert elapsed_sec < 2.0


# ---------------------------------------------------------------------------
# 2. NEGATIVE: Invalid profile raises ValueError cleanly without crash
# ---------------------------------------------------------------------------


def test_negative_invalid_profile_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unsupported profile"):
        generate_client_bridge_markdown(profile="nonexistent-tier")


# ---------------------------------------------------------------------------
# 3. BOUNDARY: Standard vs Enterprise backward-compatibility & case normalization
# ---------------------------------------------------------------------------


def test_boundary_case_normalization_and_enterprise_full_governance() -> None:
    starter_upper = generate_client_bridge_markdown(profile="STARTER")
    assert starter_upper.profile == "starter"
    assert starter_upper.bridge_line_count < 35
    assert starter_upper.hub_paths_leaked == 0

    std_dto = generate_client_bridge_markdown(profile="standard")
    assert std_dto.profile == "standard"
    assert std_dto.hub_paths_leaked == 0
    assert std_dto.mutation_required is False
    assert std_dto.passed is True

    ent_dto = generate_client_bridge_markdown(profile="enterprise")
    assert ent_dto.profile == "enterprise"
    assert ent_dto.hub_paths_leaked == 0
    assert ent_dto.mutation_required is True
    assert ent_dto.passed is True
    assert ent_dto.bridge_line_count > starter_upper.bridge_line_count


# ---------------------------------------------------------------------------
# 4. CLI CONTRACT: sync_agent_rules.py --profile starter --json & --check parity
# ---------------------------------------------------------------------------


def test_cli_sync_agent_rules_profile_flag_and_hub_check_unchanged(tmp_path: Path) -> None:
    out_bridge = tmp_path / "CLAUDE.md"
    proc = subprocess.run(
        [
            sys.executable,
            "tools/core/sync_agent_rules.py",
            "--profile",
            "starter",
            "--out",
            str(out_bridge),
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["profile"] == "starter"
    assert payload["bridge_line_count"] < 35
    assert payload["hub_paths_leaked"] == 0
    assert payload["mutation_required"] is False
    assert payload["passed"] is True
    assert out_bridge.is_file()
    assert len(out_bridge.read_text(encoding="utf-8").splitlines()) < 35

    # Default Hub --check remains 100% backward-compatible
    check_proc = subprocess.run(
        [sys.executable, "tools/core/sync_agent_rules.py", "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert check_proc.returncode == 0, check_proc.stdout + check_proc.stderr
