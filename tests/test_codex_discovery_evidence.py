#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_codex_discovery_evidence.py
Verifies distinct bridge presence, MCP startup, and native Codex host discovery outcomes.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.core.validate_host_interop import verify_codex

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _seed_codex_client_fixture(root: Path) -> str:
    (root / ".codex").mkdir(parents=True, exist_ok=True)
    (root / "templates" / "ai_bridges").mkdir(parents=True, exist_ok=True)
    shutil.copy2(os.path.join(REPO_ROOT, "AGENTS.md"), root / "AGENTS.md")
    shutil.copy2(os.path.join(REPO_ROOT, ".codex", "config.toml"), root / ".codex" / "config.toml")
    shutil.copy2(
        os.path.join(REPO_ROOT, "templates", "ai_bridges", "AGENTS.md"),
        root / "templates" / "ai_bridges" / "AGENTS.md",
    )
    shutil.copy2(
        os.path.join(REPO_ROOT, "templates", "ai_bridges", "codex_config.toml"),
        root / "templates" / "ai_bridges" / "codex_config.toml",
    )
    for wf in ("solo", "review", "super-plan"):
        dest = root / ".agents" / "skills" / wf
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            os.path.join(REPO_ROOT, ".agent", "skills", wf, "SKILL.md"),
            dest / "SKILL.md",
        )
    fast_mcp = root / "fast_mcp.py"
    fast_mcp.write_text("import sys\nprint('MCP ok')\nsys.exit(0)\n", encoding="utf-8")
    return str(fast_mcp)


def test_verify_codex_discovery_with_valid_native_receipt_and_refresh():
    """Positive: Native receipt with host_version, digest, and all 3 resolved skills earns Verified."""
    from tools.core.validate_host_interop import verify_codex_discovery_evidence

    with tempfile.TemporaryDirectory() as tmpdir:
        client = Path(tmpdir)
        fast_mcp = _seed_codex_client_fixture(client)

        pkg_digest = "sha256:" + ("a" * 64)
        receipt_path = client / "native_receipt.json"
        receipt_data = {
            "host_version": "codex-cli 0.2.0",
            "package_digest": pkg_digest,
            "session_id": "sess-1",
            "discovered_skills": {
                "solo": str(client / ".agents" / "skills" / "solo" / "SKILL.md"),
                "review": str(client / ".agents" / "skills" / "review" / "SKILL.md"),
                "super-plan": str(client / ".agents" / "skills" / "super-plan" / "SKILL.md"),
            },
        }
        receipt_path.write_text(json.dumps(receipt_data), encoding="utf-8")

        res = verify_codex_discovery_evidence(
            repo_root=str(client),
            native_receipt_path=str(receipt_path),
            expected_package_digest=pkg_digest,
            mcp_script_path=fast_mcp,
        )
        assert res["outcomes"]["bridge_presence"] == "present"
        assert res["outcomes"]["mcp_startup"] == "started"
        assert res["outcomes"]["host_discovery"] == "verified"
        assert res["native_discovery_status"] == "Verified"

        # Session refresh check: new package digest invalidates old session until refreshed
        new_digest = "sha256:" + ("b" * 64)
        stale_res = verify_codex_discovery_evidence(
            repo_root=str(client),
            native_receipt_path=str(receipt_path),
            expected_package_digest=new_digest,
            mcp_script_path=fast_mcp,
        )
        assert stale_res["outcomes"]["host_discovery"] == "unverified"
        assert stale_res["native_discovery_status"] == "Unverified"

        receipt_data["package_digest"] = new_digest
        receipt_data["session_id"] = "sess-2"
        receipt_path.write_text(json.dumps(receipt_data), encoding="utf-8")
        refreshed_res = verify_codex_discovery_evidence(
            repo_root=str(client),
            native_receipt_path=str(receipt_path),
            expected_package_digest=new_digest,
            mcp_script_path=fast_mcp,
        )
        assert refreshed_res["outcomes"]["host_discovery"] == "verified"
        assert refreshed_res["native_discovery_status"] == "Verified"


def test_file_only_fixture_reports_configuration_present_not_verified():
    """Negative: File-only fixture without native receipt reports configuration present, not Verified."""
    from tools.core.validate_host_interop import verify_codex_discovery_evidence

    with tempfile.TemporaryDirectory() as tmpdir:
        client = Path(tmpdir)
        fast_mcp = _seed_codex_client_fixture(client)

        res = verify_codex_discovery_evidence(
            repo_root=str(client),
            native_receipt_path=None,
            mcp_script_path=fast_mcp,
        )
        assert res["outcomes"]["bridge_presence"] == "present"
        assert res["outcomes"]["mcp_startup"] == "started"
        assert res["outcomes"]["host_discovery"] == "unverified"
        assert res["native_discovery_status"] == "Configuration Present"

        # Explicit missing receipt path yields Unverified (not Configuration Present)
        res_explicit_missing = verify_codex_discovery_evidence(
            repo_root=str(client),
            native_receipt_path=str(client / "nonexistent_receipt.json"),
            mcp_script_path=fast_mcp,
        )
        assert res_explicit_missing["native_discovery_status"] == "Unverified"


def test_native_receipt_missing_workflow_or_external_path_yields_unverified():
    """Negative: Missing workflow, blank host_version/digest, missing skill file, or external path yields unverified."""
    from tools.core.validate_host_interop import verify_codex_discovery_evidence

    with tempfile.TemporaryDirectory() as tmpdir:
        client = Path(tmpdir)
        fast_mcp = _seed_codex_client_fixture(client)
        pkg_digest = "sha256:" + ("c" * 64)
        valid_skills = {
            "solo": str(client / ".agents" / "skills" / "solo" / "SKILL.md"),
            "review": str(client / ".agents" / "skills" / "review" / "SKILL.md"),
            "super-plan": str(client / ".agents" / "skills" / "super-plan" / "SKILL.md"),
        }

        invalid_payloads = [
            {
                "host_version": "codex-cli 0.2.0",
                "package_digest": pkg_digest,
                "discovered_skills": {
                    "solo": valid_skills["solo"],
                    "super-plan": valid_skills["super-plan"],
                },
            },
            {
                "host_version": "codex-cli 0.2.0",
                "package_digest": pkg_digest,
                "discovered_skills": {**valid_skills, "solo": "/tmp/other_project/solo/SKILL.md"},
            },
            {
                "host_version": "   ",
                "package_digest": pkg_digest,
                "discovered_skills": valid_skills,
            },
            {
                "host_version": "codex-cli 0.2.0",
                "package_digest": "   ",
                "discovered_skills": valid_skills,
            },
            {
                "host_version": "codex-cli 0.2.0",
                "package_digest": pkg_digest,
                "discovered_skills": None,
            },
            {
                "host_version": "codex-cli 0.2.0",
                "package_digest": pkg_digest,
                "discovered_skills": {**valid_skills, "solo": str(client / ".agents" / "skills" / "solo" / "MISSING.md")},
            },
        ]
        for idx, payload in enumerate(invalid_payloads):
            rp = client / f"bad_{idx}.json"
            rp.write_text(json.dumps(payload), encoding="utf-8")
            res = verify_codex_discovery_evidence(
                str(client),
                native_receipt_path=str(rp),
                expected_package_digest=pkg_digest,
                mcp_script_path=fast_mcp,
            )
            assert res["outcomes"]["host_discovery"] == "unverified", f"Case {idx} should be unverified"
            assert res["native_discovery_status"] == "Unverified", f"Case {idx} status should be Unverified"


def test_corrupt_empty_receipt_and_missing_bridge_boundaries():
    """Boundary: Corrupt/empty receipt, missing attribution, missing MCP block, and missing MCP fail closed."""
    from tools.core.validate_host_interop import verify_codex_discovery_evidence

    with tempfile.TemporaryDirectory() as empty_dir:
        res_missing = verify_codex_discovery_evidence(
            repo_root=empty_dir,
            native_receipt_path=os.path.join(empty_dir, "missing.json"),
            mcp_script_path=os.path.join(empty_dir, "missing_mcp.py"),
        )
        assert res_missing["outcomes"]["bridge_presence"] == "missing"
        assert res_missing["outcomes"]["mcp_startup"] == "failed"
        assert res_missing["outcomes"]["host_discovery"] == "unverified"
        assert res_missing["invocation_evidence"]["exit_code"] == -1

    with tempfile.TemporaryDirectory() as tmpdir:
        client = Path(tmpdir)
        fast_mcp = _seed_codex_client_fixture(client)
        bad_json = client / "corrupt.json"
        bad_json.write_text("{not-json", encoding="utf-8")
        res_corrupt = verify_codex_discovery_evidence(
            repo_root=str(client),
            native_receipt_path=str(bad_json),
            mcp_script_path=fast_mcp,
        )
        assert res_corrupt["outcomes"]["host_discovery"] == "unverified"
        assert res_corrupt["native_discovery_status"] == "Unverified"

        # Strip attribution from AGENTS.md and MCP table from .codex/config.toml
        (client / "AGENTS.md").write_text("# Generic AGENTS\n", encoding="utf-8")
        res_no_attr = verify_codex_discovery_evidence(str(client), mcp_script_path=fast_mcp)
        assert res_no_attr["outcomes"]["bridge_presence"] == "missing"
        assert res_no_attr["verdict"] == "FAILED"

        _seed_codex_client_fixture(client)
        (client / ".codex" / "config.toml").write_text("# empty config\n", encoding="utf-8")
        res_no_toml = verify_codex_discovery_evidence(str(client), mcp_script_path=fast_mcp)
        assert res_no_toml["outcomes"]["bridge_presence"] == "missing"
        assert res_no_toml["verdict"] == "FAILED"


def test_validate_host_interop_cli_and_verify_codex_compatibility():
    """CLI & Resilience: verify_codex preserves VERIFIED_PASS and emits distinct outcomes via CLI."""
    codex_res = verify_codex(REPO_ROOT)
    assert codex_res["verdict"] == "VERIFIED_PASS"
    assert codex_res["outcomes"]["bridge_presence"] == "present"
    assert codex_res["outcomes"]["mcp_startup"] == "started"
    assert codex_res["outcomes"]["host_discovery"] in ("verified", "unverified")

    proc = subprocess.run(
        [sys.executable, "tools/core/validate_host_interop.py", "--repo-root", REPO_ROOT, "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    codex_entry = next(h for h in payload["hosts"] if h["host_name"] == "OpenAI Codex")
    assert "outcomes" in codex_entry
    assert codex_entry["outcomes"]["bridge_presence"] == "present"
