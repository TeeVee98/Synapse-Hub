#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Gate 9: Tier-2 Skill Routing & Collision Guard.
Scans skill descriptions and rules to ensure semantic trigger overlap remains < 0.75 (Addy Osmani pattern).
"""

import os
import subprocess
import sys

from tools.core.gates.base import (
    BaseGate,
    resolve_tool_path,
    safe_print,
)


def gate_9_skill_collision(repo_root: str, mode: str = "AUTO") -> bool:
    """Gate 9: Scans skill descriptions and rules to ensure semantic trigger overlap remains < 0.75."""
    print("\n[GATE 9] Running Tier-2 Skill Routing & Collision Guard (Addy Osmani Pattern)...")
    guard_script = resolve_tool_path(repo_root, "skill_collision_guard.py", "lint")
    if not os.path.exists(guard_script):
        print("[FAIL] skill_collision_guard.py not found in tools/!")
        return False

    skills_dir = os.path.join(repo_root, ".agents", "skills")
    rules_dir = os.path.join(repo_root, ".agents", "rules")
    manifest_file = os.path.join(repo_root, "skills_manifest.json")
    if not os.path.exists(skills_dir) and not os.path.exists(manifest_file):
        print("[PASS] Target project mode: skills not present (SKIPPED).")
        return True

    # 1. Skill Schema & Policy Validation
    schema_validator = resolve_tool_path(repo_root, "validate_skills_schema.py", "lint")

    if os.path.exists(schema_validator):
        try:
            validator_cmd = [sys.executable, schema_validator, "--check-links"]
            if os.path.exists(skills_dir):
                validator_cmd.extend(["--skills-dir", skills_dir])
            s_res = subprocess.run(
                validator_cmd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=60.0
            )
            if s_res.returncode != 0:
                print("[FAIL] Gate 9 Skill Schema Validation Failed:")
                safe_print(s_res.stdout)
                safe_print(s_res.stderr)
                return False
            print("[PASS] 100% Verified: All registered skills conform to Frontmatter Schema & Policies.")
        except Exception as s_err:
            print(f"[FAIL] Gate 9 Skill Schema Validator execution error: {s_err}")
            return False

    # 2. Addy Osmani TF-IDF Skill Collision Guard
    cmd = [sys.executable, guard_script, "--threshold", "0.75"]
    if os.path.exists(skills_dir):
        cmd.extend(["--dir", skills_dir])
    if os.path.exists(rules_dir):
        cmd.extend(["--scan-rules", "--rules-dir", rules_dir])

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=60.0)
    except subprocess.TimeoutExpired:
        print("[FAIL] skill_collision_guard.py timed out after 60s!")
        return False

    if res.returncode != 0:
        safe_print(res.stdout)
        safe_print(res.stderr)
        return False
    print("[PASS] 100% Verified: 0 skill description and rule collisions detected (similarity < 0.75).")

    # Run Mechanical UI Finish Gate ONLY when target repository actually contains frontend UI components
    has_frontend_ui = any(
        os.path.isdir(os.path.join(repo_root, ui_dir))
        for ui_dir in ("src/components", "app/components", "frontend/src", "client/src")
    )
    mech_script = resolve_tool_path(repo_root, "mechanical_ui_gate.py", "design")
    if has_frontend_ui and os.path.exists(mech_script):
        try:
            m_res = subprocess.run([sys.executable, mech_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=30.0)
            if m_res.returncode == 0:
                print("[PASS] Mechanical UI Finish Gate: Layout, contrast, and interactive elements verified.")
            else:
                safe_print(f"[WARN] Mechanical UI Finish Gate non-zero exit: {m_res.stderr.strip()[:100]}")
        except (OSError, subprocess.SubprocessError) as m_err:
            safe_print(f"[WARN] Mechanical UI Finish Gate execution error: {m_err}")

    # 3. Canonical Skills Lockfile & Content Hash Integrity Verification
    try:
        from skill_canonical_digest import validate_lockfile_integrity
        lock_ok, lock_msg = validate_lockfile_integrity(repo_root, enforce_content_hash=True)
        if not lock_ok:
            print(f"[FAIL] Gate 9 Skills Lockfile Integrity: {lock_msg}")
            return False
        print(f"[PASS] 100% Verified: {lock_msg}.")
    except Exception as lock_err:
        print(f"[FAIL] Gate 9 Skills Lockfile verification exception: {lock_err}")
        return False

    return True


class Gate09Collisions(BaseGate):
    """Gate 9: Tier-2 Skill Routing & Collision Guard."""

    gate_id = 9
    name = "Gate 9: Tier-2 Skill Routing & Collision Guard"
    key = "gate_9_skill_collision"

    def run(self, repo_root: str, mode: str = "AUTO", **kwargs) -> bool:
        return gate_9_skill_collision(repo_root, mode=mode)
