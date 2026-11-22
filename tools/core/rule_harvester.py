#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/rule_harvester.py — Dynamic Rule & Episodic Learning Harvester (Level 4 Adaptive Hub)
------------------------------------------------------------------------------------------
Analyzes execution telemetry, flaky test logs, healing caches, and shortcut markers to
synthesize adaptive lessons and propose continuous rule evolutions for AGENTS.md.

Usage:
  python3 tools/rule_harvester.py
  python3 tools/rule_harvester.py --suggest
  python3 tools/rule_harvester.py --json
"""
import os
import sys

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass


import os
import sys
import subprocess
import re
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
REPORTS_DIR = os.path.join(REPO_ROOT, "reports")


class DynamicRuleHarvester:
    """Harvests episodic lessons, test telemetry, and suggests adaptive rules."""

    def __init__(self, repo_root: str = REPO_ROOT):
        self.repo_root = os.path.abspath(repo_root)
        self.reports_dir = os.path.join(self.repo_root, "reports")

    def harvest_flaky_telemetry(self) -> List[Dict[str, Any]]:
        """Harvests unstable test telemetry from reports directory."""
        findings = []
        flaky_pattern = os.path.join(self.reports_dir, "*flaky*.json")
        import glob
        for p in glob.glob(flaky_pattern):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        findings.extend(data)
                    elif isinstance(data, dict):
                        findings.append(data)
            except Exception:
                continue
        return findings

    def harvest_shortcut_debt(self) -> List[Dict[str, Any]]:
        """Scans codebase for deliberate 'shortcut:' markers."""
        shortcuts = []
        debt_regex = re.compile(r'(?:#|//|/\*|--|<!--)\s*shortcut:\s*(.+?)(?:\*/|-->)?$', re.IGNORECASE)
        ignore_dirs = {".git", "node_modules", "build", "dist", ".venv", "venv", "__pycache__"}

        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if file.endswith((".py", ".ts", ".js", ".groovy", ".java", ".md")):
                    fpath = os.path.join(root, file)
                    rel_path = os.path.relpath(fpath, self.repo_root)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            for idx, line in enumerate(f, 1):
                                match = debt_regex.search(line)
                                if match:
                                    shortcuts.append({
                                        "file": rel_path,
                                        "line": idx,
                                        "note": match.group(1).strip()
                                    })
                    except Exception:
                        continue
        return shortcuts

    def harvest_mutation_loss(self) -> Optional[Dict[str, Any]]:
        """Inspects mutant baseline for surviving mutants."""
        mutant_path = os.path.join(self.reports_dir, "mutant_baseline.json")
        if os.path.exists(mutant_path):
            try:
                with open(mutant_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as err:
                sys.stderr.write(f"Warning: Failed to parse mutant baseline: {err}\n")
                return None
        return None

    def harvest_lessons_learned(self) -> List[Dict[str, Any]]:
        """Harvests episodic lessons learned from cache_resolver or reports/lessons_learned.json."""
        lessons = []
        json_path = os.path.join(self.reports_dir, "lessons_learned.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        lessons.extend(data)
                    elif isinstance(data, dict) and "lessons_learned" in data:
                        lessons.extend(data["lessons_learned"])
            except (json.JSONDecodeError, OSError) as err:
                sys.stderr.write(f"Warning: Failed to parse {json_path}: {err}\n")

        if not lessons:
            try:
                from cache_resolver import query_lessons
                if query_lessons:
                    lessons = query_lessons("", limit=10)
            except (ImportError, OSError) as err:
                sys.stderr.write(f"Warning: Failed to query lessons from cache: {err}\n")
        return lessons

    def synthesize_adaptive_rules(self) -> List[Dict[str, str]]:
        """Synthesizes actionable rule suggestions based on harvested telemetry."""
        suggestions = []

        # 1. Flaky test pattern analysis
        flaky = self.harvest_flaky_telemetry()
        if flaky:
            suggestions.append({
                "type": "RESILIENCE_RULE",
                "trigger": "Unstable/Flaky Test Detection",
                "rule": "Enforce dynamic wait `waitForLoadState('networkidle')` and isolate flaky suites with `@quarantine` annotation."
            })

        # 2. Shortcut debt analysis
        shortcuts = self.harvest_shortcut_debt()
        if len(shortcuts) > 5:
            suggestions.append({
                "type": "TECHNICAL_DEBT_RULE",
                "trigger": f"High Shortcut Density ({len(shortcuts)} shortcuts found)",
                "rule": "Prioritize refactoring pragmatic shortcuts in core Page Classes to eliminate technical debt rots."
            })

        # 3. Mutation score analysis
        mutant = self.harvest_mutation_loss()
        if mutant:
            score = mutant.get("mutation_score", mutant.get("score", 100))
            if isinstance(score, (int, float)) and score < 80:
                suggestions.append({
                    "type": "TRUTH_ANCHOR_RULE",
                    "trigger": f"Low Mutation Sensitivity ({score:.1f}% < 80%)",
                    "rule": "Strengthen assertions on return payloads and state mutations; eliminate empty validation steps."
                })

        # 4. Episodic lessons learned analysis
        lessons = self.harvest_lessons_learned()
        if lessons:
            suggestions.append({
                "type": "EPISODIC_MEMORY_RULE",
                "trigger": f"Episodic Reflexion Memory ({len(lessons)} past failure lessons recorded)",
                "rule": "Prioritize applying historical resolution patterns from lessons_learned before attempting speculative patches."
            })

        # Baseline adaptive rule if repo is pristine
        if not suggestions:
            suggestions.append({
                "type": "STABILITY_BASELINE",
                "trigger": "Clean Telemetry Baseline",
                "rule": "Maintain strict adherence to Clean POM Flat Architecture and dynamic smart waits."
            })

        return suggestions

    def generate_report(self) -> Dict[str, Any]:
        """Compiles a full Level 4 Adaptive Insights Report."""
        flaky = self.harvest_flaky_telemetry()
        shortcuts = self.harvest_shortcut_debt()
        lessons = self.harvest_lessons_learned()
        suggestions = self.synthesize_adaptive_rules()

        # Export lessons learned snapshot if absent
        lessons_export_path = os.path.join(self.reports_dir, "lessons_learned.json")
        if lessons and not os.path.exists(lessons_export_path):
            try:
                os.makedirs(self.reports_dir, exist_ok=True)
                with open(lessons_export_path, "w", encoding="utf-8") as f:
                    json.dump(lessons, f, indent=2, ensure_ascii=False)
            except OSError as err:
                sys.stderr.write(f"Warning: Failed to export lessons learned: {err}\n")

        return {
            "timestamp": datetime.now().isoformat(),
            "level": "LEVEL_4_ADAPTIVE",
            "flaky_tests_detected": len(flaky),
            "shortcuts_harvested": len(shortcuts),
            "lessons_learned_count": len(lessons),
            "adaptive_suggestions": suggestions
        }

    def apply_rules(self, suggestions: Optional[List[Dict[str, str]]] = None) -> bool:
        """
        Applies synthesized adaptive rules into reports/adaptive_rules.json
        and triggers AI bridge synchronization.
        """
        if suggestions is None:
            suggestions = self.synthesize_adaptive_rules()

        if not suggestions:
            print("ℹ️ No adaptive rules to apply.")
            return True

        os.makedirs(self.reports_dir, exist_ok=True)
        adaptive_json_path = os.path.join(self.reports_dir, "adaptive_rules.json")
        try:
            with open(adaptive_json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "rules": suggestions
                }, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(suggestions)} adaptive rules into {adaptive_json_path}")
        except OSError as err:
            sys.stderr.write(f"Warning: Failed to save adaptive rules: {err}\n")
            return False

        # Run AI bridge rule synchronizer
        sync_script = os.path.join(SCRIPT_DIR, "sync_agent_rules.py")
        if os.path.exists(sync_script):
            try:
                subprocess.run([sys.executable, sync_script], capture_output=True, text=True, check=True)
                print("✅ Synchronized AI bridge rules.")
            except (subprocess.SubprocessError, OSError) as err:
                sys.stderr.write(f"Warning: Failed to sync AI bridges: {err}\n")

        return True


def main():
    parser = argparse.ArgumentParser(description="Level 4 Dynamic Rule & Episodic Learning Harvester")
    parser.add_argument("--json", action="store_true", help="Output raw JSON telemetry")
    parser.add_argument("--suggest", action="store_true", help="Output actionable rule evolution suggestions")
    parser.add_argument("--apply", action="store_true", help="Apply adaptive rule recommendations and synchronize bridges")
    parser.add_argument("--ratchet", action="store_true", help="Synthesize AGENTS.md Ratchet invariant candidates from failure telemetry")
    args = parser.parse_args()

    harvester = DynamicRuleHarvester()
    report = harvester.generate_report()

    if args.apply:
        harvester.apply_rules(report["adaptive_suggestions"])

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    if args.ratchet:
        print("# --- SYNAPSE HUB RATCHET RULE CANDIDATES (Hashimoto Principle) ---")
        print("# Generated from episodic failure telemetry to permanently tighten the harness.")
        for idx, item in enumerate(report["adaptive_suggestions"], 1):
            rule_text = item["rule"]
            trigger = item["trigger"]
            print(f"\n# Ratchet Candidate {idx} [{item['type']}]:")
            print(f"> **Invariant (Tightened):** {rule_text}")
            print(f"> *Root Trigger:* {trigger}")
        return 0

    print("======================================================================")
    print("      SYNAPSE HUB — LEVEL 4 DYNAMIC RULE HARVESTER                   ")
    print("======================================================================")
    print(f"  Timestamp         : {report['timestamp']}")
    print(f"  Flaky Tests Found : {report['flaky_tests_detected']}")
    print(f"  Shortcuts Found   : {report['shortcuts_harvested']}")
    print("----------------------------------------------------------------------")
    print("  ADAPTIVE RULE RECOMMENDATIONS:")
    for idx, item in enumerate(report["adaptive_suggestions"], 1):
        print(f"  [{idx}] [{item['type']}] {item['trigger']}")
        print(f"      ➔ Rule: {item['rule']}")
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
