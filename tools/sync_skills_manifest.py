#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/sync_skills_manifest.py — Synchronize Skill Policies & Frontmatter into Manifest
Synchronizes SKILL.md frontmatter policies, category, version, and description
into skills_manifest.json to maintain absolute parity.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Try importing from validate_skills_schema, or fall back to internal parser
try:
    from tools.validate_skills_schema import parse_yaml_frontmatter
except ImportError:
    try:
        from validate_skills_schema import parse_yaml_frontmatter
    except ImportError:
        import re

        def parse_yaml_frontmatter(content: str):
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if not match:
                return None, "", ["No frontmatter"]
            fm_text = match.group(1)
            body = match.group(2)
            data: Dict[str, Any] = {}
            current_section = None
            for line in fm_text.splitlines():
                line = line.rstrip()
                if not line or line.strip().startswith("#"):
                    continue
                indent = len(line) - len(line.lstrip())
                stripped = line.strip()
                if indent == 0:
                    if ":" not in stripped:
                        continue
                    k, v = stripped.split(":", 1)
                    k, v = k.strip(), v.strip().strip("\"'")
                    if not v:
                        current_section = k
                        data[current_section] = {}
                    else:
                        current_section = None
                        data[k] = v
                elif indent >= 2 and current_section:
                    if ":" not in stripped:
                        continue
                    ck, cv = stripped.split(":", 1)
                    if isinstance(data.get(current_section), dict):
                        data[current_section][ck.strip()] = cv.strip().strip("\"'")
            return data, body, []


def sync_manifest(skills_dir: Path, manifest_path: Path, write: bool = False) -> Tuple[bool, List[str]]:
    """
    Reads all SKILL.md files and compares/syncs them with manifest_path.
    Returns (in_sync: bool, diffs: List[str]).
    """
    if not manifest_path.exists():
        return False, [f"Manifest not found: {manifest_path}"]

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest_skills = manifest_data.get("skills", [])
    skill_map = {s["id"]: s for s in manifest_skills}

    diffs: List[str] = []
    skill_files = sorted(skills_dir.glob("*/*/SKILL.md"))

    for sf in skill_files:
        skill_id = sf.parent.name
        content = sf.read_text(encoding="utf-8")
        fm, _, errs = parse_yaml_frontmatter(content)
        if not fm or errs:
            diffs.append(f"{skill_id}: frontmatter parse error: {errs}")
            continue

        if skill_id not in skill_map:
            diffs.append(f"{skill_id}: missing in manifest")
            continue

        entry = skill_map[skill_id]

        # Check / sync category
        fm_cat = fm.get("category")
        if fm_cat and entry.get("category") != fm_cat:
            diffs.append(f"{skill_id}: category '{entry.get('category')}' != frontmatter '{fm_cat}'")
            entry["category"] = fm_cat

        # Check / sync version
        fm_ver = fm.get("version")
        if fm_ver and entry.get("version") != fm_ver:
            diffs.append(f"{skill_id}: version '{entry.get('version')}' != frontmatter '{fm_ver}'")
            entry["version"] = fm_ver

        # Check / sync description
        fm_desc = fm.get("description")
        if fm_desc:
            norm_fm_desc = " ".join(fm_desc.strip("\"'").split())
            norm_entry_desc = " ".join(entry.get("description", "").strip("\"'").split())
            if norm_entry_desc != norm_fm_desc:
                diffs.append(f"{skill_id}: description updated in manifest")
                entry["description"] = norm_fm_desc

        # Check / sync policies
        fm_pol = fm.get("policies")
        if fm_pol:
            if entry.get("policies") != fm_pol:
                diffs.append(f"{skill_id}: policies mismatch or missing in manifest")
                entry["policies"] = fm_pol

    # Update totalSkills count
    if manifest_data.get("totalSkills") != len(manifest_skills):
        diffs.append(f"totalSkills {manifest_data.get('totalSkills')} != {len(manifest_skills)}")
        manifest_data["totalSkills"] = len(manifest_skills)

    if diffs and write:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    in_sync = len(diffs) == 0
    return in_sync, diffs


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize skills frontmatter policies into skills_manifest.json")
    parser.add_argument("--skills-dir", default=".agents/skills", help="Path to skills directory")
    parser.add_argument("--manifest", default="skills_manifest.json", help="Path to skills_manifest.json")
    parser.add_argument("--check", action="store_true", help="Dry-run check; exits 1 if out of sync")
    parser.add_argument("--write", action="store_true", default=True, help="Write updates to manifest (default)")

    args = parser.parse_args()
    skills_dir = Path(args.skills_dir).resolve()
    manifest_path = Path(args.manifest).resolve()

    write_mode = not args.check and args.write
    in_sync, diffs = sync_manifest(skills_dir, manifest_path, write=write_mode)

    if in_sync:
        print("✅ skills_manifest.json is 100% in sync with SKILL.md frontmatters and policies.")
        return 0

    if args.check:
        print(f"❌ Drift detected ({len(diffs)} differences):")
        for d in diffs:
            print(f"  • {d}")
        return 1

    print(f"🔄 Synchronized {len(diffs)} items in {manifest_path}:")
    for d in diffs:
        print(f"  • {d}")
    print("✅ skills_manifest.json updated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
