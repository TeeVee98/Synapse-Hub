# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""Tests for Enterprise QA Hub Observability Dashboard."""

import os
import tempfile
from tools.dashboard.serve_dashboard import collect_hub_telemetry, generate_dashboard_html


def test_collect_hub_telemetry():
    """Verify telemetry collects metrics without errors and adheres to schema."""
    telemetry = collect_hub_telemetry()
    assert isinstance(telemetry, dict)
    assert telemetry["hub_name"] == "Synapse-Hub Enterprise QA"
    assert telemetry["author"] == "Thế Vị (@TeeVee98)"
    assert "quality_gates" in telemetry
    assert len(telemetry["quality_gates"]) == 10
    assert all(g["status"] == "PASS" for g in telemetry["quality_gates"])
    assert telemetry["skills_summary"]["total"] >= 50
    assert telemetry["tools_summary"]["total"] >= 100


def test_generate_dashboard_html():
    """Verify HTML generation produces valid, styled self-contained HTML."""
    telemetry = collect_hub_telemetry()
    html = generate_dashboard_html(telemetry)
    assert "<!DOCTYPE html>" in html
    assert "Synapse Hub - Enterprise QA Observability Dashboard" in html
    assert "Thế Vị (@TeeVee98)" in html
    assert "10 / 10" in html
    assert "GATE 1" in html
    assert "GATE 10" in html


def test_dashboard_export_file():
    """Verify HTML dashboard export to temporary file."""
    telemetry = collect_hub_telemetry()
    html = generate_dashboard_html(telemetry)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        temp_path = f.name

    try:
        assert os.path.exists(temp_path)
        with open(temp_path, "r", encoding="utf-8") as rf:
            content = rf.read()
        assert len(content) > 1000
        assert "Synapse Hub Observability" in content
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
