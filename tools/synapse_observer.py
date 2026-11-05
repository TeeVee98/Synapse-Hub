#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Synapse Cognitive Observer & Tradeoff Sentinel
----------------------------------------------
Inspired by Anthropic Claude Code 2.1.292 (wassname/cc-plugin-you-should-know).
Acts as an out-of-band observer that inspects code changes, diffs, and architectural
decisions to surface critical tradeoffs, hidden costs, or risks that the user may
have missed during rapid development.

Core Principles:
  1. High Interruption Bar: Defaults to 'learn: none' unless a real consequence exists.
  2. Human-Centric Communication: Plain-language, jargon-free title (3-7 words) and <120 words explanation.
  3. Anti-Nagging Memory: Never repeats topics that the user already acknowledged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Enforce UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

MEMORY_DIR = Path.home() / ".agent_memory"
MEMORY_FILE = MEMORY_DIR / "synapse_observer_history.json"


@dataclass
class ObserverAlert:
    tag: str  # 'Heads up' | 'You should know'
    learn: str  # 1-2 sentences (< 25 words)
    title: str  # 3-7 words bold title
    explanation: List[str]  # Bullet points explaining why and action
    topic_key: str  # Unique slug for anti-nagging memory


def is_page_class_file(file_path: str) -> bool:
    """Return True if the file path indicates a Page Class / Object Repository."""
    if not file_path:
        return False
    fp = file_path.replace("\\", "/").lower()
    # Directory path checks for dedicated Page Class subfolders
    if any(p in fp for p in ["pages/", "page_objects/", "object repository/", "object-repository/"]):
        return True

    # Test script exclusion checks
    base = Path(fp).name.lower()
    is_test_script = (
        base.startswith("test_")
        or base.endswith("_test.py")
        or "_test." in base
        or ".spec." in base
        or ".test." in base
        or any(td in fp for td in ["tests/", "scripts/", "spec/", "specs/"])
    )
    if is_test_script:
        return False

    # Filename checks
    if "page." in base or base.endswith("page") or "_page." in base:
        return True
    return False


def parse_diff_files(diff_text: str) -> List[Tuple[str, str]]:
    """Parse diff into [(file_path, added_lines_text), ...]."""
    files: List[Tuple[str, str]] = []
    current_file = ""
    current_lines: List[str] = []

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current_file or current_lines:
                files.append((current_file, "\n".join(current_lines)))
                current_lines = []
            m = re.search(r"diff --git a/.*? b/(.*)", line)
            current_file = m.group(1).strip() if m else ""
        elif line.startswith("+++ b/"):
            current_file = line[6:].strip()
        elif line.startswith("+") and not line.startswith("+++"):
            current_lines.append(line)

    if current_file or current_lines:
        files.append((current_file, "\n".join(current_lines)))

    if not files and diff_text:
        # Diff has no git headers; treat entire text as single unassociated chunk
        files.append(("", diff_text))

    return files


class SynapseObserver:
    """Out-of-band observer detecting consequential tradeoffs and risks."""

    def __init__(self, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path) if memory_path else MEMORY_FILE
        self.acknowledged_topics: set[str] = self._load_acknowledged_topics()

    def _load_acknowledged_topics(self) -> set[str]:
        if not self.memory_path.exists():
            return set()
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                acks = data.get("acknowledged", [])
                if isinstance(acks, list):
                    return set(str(x) for x in acks if x is not None)
            return set()
        except (json.JSONDecodeError, OSError, AttributeError) as err:
            sys.stderr.write(f"[SYNAPSE-OBSERVER] Warning loading memory: {err}\n")
            return set()

    def _save_memory(self) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        current = {}
        if self.memory_path.exists():
            try:
                current = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                current = {}
        current["acknowledged"] = sorted(list(self.acknowledged_topics))
        self.memory_path.write_text(
            json.dumps(current, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def is_acknowledged(self, topic_key: str) -> bool:
        """Check if topic or its base family is already acknowledged."""
        if topic_key in self.acknowledged_topics:
            return True
        base_topic = topic_key.split("::")[0]
        return base_topic in self.acknowledged_topics

    def acknowledge_topic(self, topic_key: str) -> None:
        """Mark a topic as acknowledged by the user so it won't be repeated."""
        self.acknowledged_topics.add(topic_key)
        self._save_memory()

    def unacknowledge_topic(self, topic_key: str) -> bool:
        """Remove a topic (and any child scoped keys) from acknowledged memory."""
        removed = False
        to_remove = [
            t
            for t in self.acknowledged_topics
            if t == topic_key or t.startswith(f"{topic_key}::")
        ]
        for t in to_remove:
            self.acknowledged_topics.discard(t)
            removed = True
        if removed:
            self._save_memory()
        return removed

    def reset_memory(self) -> None:
        """Reset and clear all acknowledged topics from memory."""
        self.acknowledged_topics.clear()
        self._save_memory()

    def evaluate_diff(
        self, diff_text: str, return_all: bool = False
    ) -> Union[Optional[ObserverAlert], List[ObserverAlert]]:
        """Analyze a git diff for consequential tradeoffs."""
        file_chunks = parse_diff_files(diff_text)
        alerts: List[ObserverAlert] = []

        # 1. Check for raw XPath / CSS selector directly added in test scripts
        # Locators in Page Classes are exempt (Clean POM Flat Architecture)
        locator_regex = re.compile(
            r"([\"']\/\/[a-zA-Z0-9_\-\*\[\]@=\'\" /]+[\"']|By\.(?:xpath|cssSelector|XPATH|CSS_SELECTOR|id|name|className)\b|page\.(?:locator|click|fill|hover|press|check|uncheck)\(|cy\.(?:get|find)\()",
            re.MULTILINE,
        )

        for file_path, added_text in file_chunks:
            if is_page_class_file(file_path):
                # Page classes are authorized to contain locators
                continue
            # If raw text without headers contains class Page declaration, skip
            if not file_path and re.search(r"class\s+\w+Page\b|extends\s+BasePage\b", added_text):
                continue

            # Check lines, ignoring pure comments
            has_locator = False
            for line in added_text.splitlines():
                if not line.startswith("+") or line.startswith("+++"):
                    continue
                code_part = line[1:].strip()
                if code_part.startswith("//") or code_part.startswith("/*") or code_part.startswith("*") or code_part.startswith("#"):
                    continue
                if locator_regex.search(code_part):
                    has_locator = True
                    break

            if has_locator:
                topic = f"clean_pom_raw_locator::{file_path}" if file_path else "clean_pom_raw_locator"
                if not self.is_acknowledged(topic):
                    alert = ObserverAlert(
                        tag="Heads up",
                        learn="Raw locators were added directly into test scripts instead of encapsulated in Page Classes.",
                        title="Keep Test Scripts Clean of Selectors",
                        explanation=[
                            "Clean POM Flat Architecture requires all selectors to stay inside Page Classes.",
                            "Putting raw XPath or CSS selectors directly in tests causes high maintenance debt when UI changes.",
                            "Extract the element selector into the relevant Page Class and expose a business method instead.",
                        ],
                        topic_key=topic,
                    )
                    alerts.append(alert)
                    if not return_all:
                        return alert
                break

        # 2. Check for static sleep / hardcoded delay added
        sleep_regex = re.compile(
            r"^\+[^+].*(Thread\.sleep|time\.sleep|sleep\(\s*\d+|page\.wait_for_timeout\(|asyncio\.sleep\(|WebUI\.delay\()",
            re.MULTILINE,
        )
        if sleep_regex.search(diff_text):
            topic = "static_sleep_flakiness"
            if not self.is_acknowledged(topic):
                alert = ObserverAlert(
                    tag="Heads up",
                    learn="Static sleep was introduced, which creates pipeline flakiness and slows CI runs.",
                    title="Replace Static Sleep with Dynamic Smart Wait",
                    explanation=[
                        "Hardcoded sleeps either wait too long (wasting CI time) or not long enough under load.",
                        "Use dynamic element visibility checks or network idle states instead.",
                        "Dynamic waits resume immediately once the condition is met, saving time and eliminating flakiness.",
                    ],
                    topic_key=topic,
                )
                alerts.append(alert)
                if not return_all:
                    return alert

        # 3. Check for entity creation without teardown cleanup
        has_teardown = bool(
            re.search(r"(delete|teardown|cleanup|afterEach|afterAll|drop)", diff_text, re.IGNORECASE)
        )
        if not has_teardown:
            has_creation = False
            for line in diff_text.splitlines():
                if not line.startswith("+") or line.startswith("+++"):
                    continue
                line_content = line[1:]

                # Ignore list/array/dict operations (not persistent entity creations)
                if re.search(r"\b(?:list|items|array|dict|elements|records|data|rows|values|arr)\.insert\s*\(", line_content):
                    continue
                if re.search(r"\b\w+\.insert\s*\(\s*\d+\s*,", line_content):
                    continue

                # Match DB / API entity creation
                if re.search(
                    r"(?:POST\s+[\"'/]|INSERT\s+INTO\b|createEntity\(|createUser\(|order_create\(|db\.(?:insert|save)\b)",
                    line_content,
                    re.IGNORECASE,
                ):
                    has_creation = True
                    break
                if re.search(r"\b(createEntity|createUser|order_create)\b", line_content):
                    has_creation = True
                    break
                if re.search(r"\bPOST\b", line_content) and re.search(r"[\"'/][a-zA-Z0-9_\-/]+", line_content):
                    has_creation = True
                    break

            if has_creation:
                topic = "missing_teardown_cleanup"
                if not self.is_acknowledged(topic):
                    alert = ObserverAlert(
                        tag="You should know",
                        learn="New test entities are created without explicit teardown cleanup, risking database pollution.",
                        title="Pair Test Data Creation with Automated Teardown",
                        explanation=[
                            "Creating entities without deleting them can cause unique key collisions on subsequent runs.",
                            "Always pair creation test cases with an automated cleanup in afterEach or a fixture.",
                            "Use dynamic timestamp prefixes like `uniqueCode('AUTO_')` to ensure idempotency.",
                        ],
                        topic_key=topic,
                    )
                    alerts.append(alert)
                    if not return_all:
                        return alert

        # 4. Check for deliberate shortcut marker
        shortcut_match = re.search(r"^\+[^+].*shortcut:\s*(.+)", diff_text, re.MULTILINE)
        if shortcut_match:
            shortcut_desc = shortcut_match.group(1).strip()
            topic_hash = hashlib.md5(shortcut_desc.encode("utf-8")).hexdigest()[:8]
            topic = f"shortcut_{topic_hash}"
            if not self.is_acknowledged(topic) and not self.is_acknowledged("technical_debt_shortcut"):
                alert = ObserverAlert(
                    tag="You should know",
                    learn="A deliberate technical shortcut was recorded in the diff and should be tracked.",
                    title="Tracked Shortcut Added to Codebase",
                    explanation=[
                        "A `shortcut:` comment was added to keep changes minimal and pragmatic.",
                        "Remember to audit this shortcut periodically using `tools/debt_harvester.py`.",
                        "Upgrade the shortcut before scaling this component to production load.",
                    ],
                    topic_key=topic,
                )
                alerts.append(alert)
                if not return_all:
                    return alert

        if return_all:
            return alerts
        return alerts[0] if alerts else None

    def evaluate_text(
        self, text: str, return_all: bool = False
    ) -> Union[Optional[ObserverAlert], List[ObserverAlert]]:
        """Analyze arbitrary decision text or summary for tradeoffs."""
        return self.evaluate_diff(text, return_all=return_all)


def format_observer_output(alert: Optional[ObserverAlert]) -> str:
    """Format alert according to the Claude Code observer contract."""
    if not alert:
        return "learn: none"

    lines = [
        f"learn: {alert.learn}",
        f"tag: {alert.tag}",
        "explain:",
        f"**{alert.title}**",
    ]
    for bullet in alert.explanation:
        lines.append(f"- {bullet}")
    return "\n".join(lines)


def get_git_diff(staged: bool = False) -> str:
    """Retrieve current git diff (working tree or staged)."""
    try:
        cmd = ["git", "diff", "--cached"] if staged else ["git", "diff", "HEAD"]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
        )
        return res.stdout
    except Exception as err:
        sys.stderr.write(f"[SYNAPSE-OBSERVER] Warning running git diff: {err}\n")
        return ""


def main():
    parser = argparse.ArgumentParser(
        description="Synapse Cognitive Observer & Tradeoff Sentinel"
    )
    parser.add_argument("--diff", action="store_true", help="Analyze current git diff")
    parser.add_argument("--staged", "--cached", action="store_true", help="Analyze staged git diff (pre-commit)")
    parser.add_argument("--file", "-f", type=Path, help="Analyze a specific file directly")
    parser.add_argument("--text", "-t", type=str, help="Analyze raw text / decision summary")
    parser.add_argument("--ack", type=str, help="Acknowledge a topic slug so it won't be repeated")
    parser.add_argument("--unack", type=str, help="Remove a topic slug from acknowledged memory")
    parser.add_argument("--reset", "--clear-ack", action="store_true", help="Reset all acknowledged topics from memory")
    parser.add_argument("--list-ack", action="store_true", help="List acknowledged topic slugs")
    parser.add_argument("--memory-file", type=Path, help="Custom path for anti-nagging memory file")
    parser.add_argument("--all", action="store_true", help="Evaluate and return all active alerts")
    parser.add_argument("--strict", action="store_true", help="Exit code 1 if active unacknowledged alert is found")
    parser.add_argument("--json", action="store_true", help="Output alert as JSON")
    args = parser.parse_args()

    observer = SynapseObserver(memory_path=args.memory_file)

    if args.reset:
        observer.reset_memory()
        print("Observer memory reset successfully.")
        sys.exit(0)

    if args.unack:
        removed = observer.unacknowledge_topic(args.unack)
        if removed:
            print(f"Topic '{args.unack}' unacknowledged.")
        else:
            print(f"Topic '{args.unack}' was not found in memory.")
        sys.exit(0)

    if args.ack:
        observer.acknowledge_topic(args.ack)
        print(f"Acknowledge recorded for topic: '{args.ack}'")
        sys.exit(0)

    if args.list_ack:
        print("Acknowledged topics:")
        for t in sorted(observer.acknowledged_topics):
            print(f"  - {t}")
        sys.exit(0)

    alerts: List[ObserverAlert] = []
    single_alert: Optional[ObserverAlert] = None

    if args.file:
        if not args.file.is_file():
            sys.stderr.write(f"Error: Not a regular file: {args.file}\n")
            sys.exit(2)
        content = args.file.read_text(encoding="utf-8", errors="ignore")
        # Build synthetic diff with file path header
        norm_path = str(args.file).replace("\\", "/")
        diff_text = f"diff --git a/{norm_path} b/{norm_path}\n--- a/{norm_path}\n+++ b/{norm_path}\n"
        diff_text += "\n".join("+" + line for line in content.splitlines())
        res = observer.evaluate_diff(diff_text, return_all=args.all)
        if args.all:
            alerts = res if isinstance(res, list) else ([res] if res else [])
        else:
            single_alert = res if isinstance(res, ObserverAlert) else None
    elif args.diff or args.staged:
        diff_text = get_git_diff(staged=args.staged)
        res = observer.evaluate_diff(diff_text, return_all=args.all)
        if args.all:
            alerts = res if isinstance(res, list) else ([res] if res else [])
        else:
            single_alert = res if isinstance(res, ObserverAlert) else None
    elif args.text:
        res = observer.evaluate_text(args.text, return_all=args.all)
        if args.all:
            alerts = res if isinstance(res, list) else ([res] if res else [])
        else:
            single_alert = res if isinstance(res, ObserverAlert) else None
    else:
        # Default: check working tree git diff
        diff_text = get_git_diff(staged=False)
        res = observer.evaluate_diff(diff_text, return_all=args.all)
        if args.all:
            alerts = res if isinstance(res, list) else ([res] if res else [])
        else:
            single_alert = res if isinstance(res, ObserverAlert) else None

    has_alert = bool(alerts) if args.all else (single_alert is not None)

    if args.json:
        if args.all:
            payload = [asdict(a) for a in alerts]
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            if single_alert:
                print(json.dumps(asdict(single_alert), indent=2, ensure_ascii=False))
            else:
                print(json.dumps({"learn": "none"}, indent=2))
    else:
        if args.all:
            if not alerts:
                print("learn: none")
            else:
                for idx, a in enumerate(alerts):
                    if idx > 0:
                        print("\n---")
                    print(format_observer_output(a))
        else:
            print(format_observer_output(single_alert))

    if args.strict and has_alert:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
