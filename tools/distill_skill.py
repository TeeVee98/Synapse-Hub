#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
"""
tools/distill_skill.py — Dual-Skill Distillation Engine
Inspired by titanwings/distilly (26.6k ⭐).

Distills unified agent skills and guidelines into two decoupled artifacts:
1. work_skill.md: Concrete procedures, CLI commands, step sequences, and DoD gates.
2. persona_skill.md: Cognitive heuristics, identity, communication style, and invariants.

Prevents persona drift and execution ambiguity across multi-agent swarms.
100% Python Standard Library (zero external dependencies).
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

PERSONA_KEYWORDS = {
    "identity", "role", "tone", "communication", "telemetry", "badge",
    "heuristic", "ruling", "philosophy", "senior dev", "protocol",
    "style", "mindset", "falsification", "anti-pattern", "blacklist",
}

PROCEDURE_KEYWORDS = {
    "command", "cli", "run", "step", "execute", "workflow", "script",
    "verification", "dod", "gate", "curl", "test", "matrix", "schema",
    "setup", "install", "teardown", "mutation", "assertion",
}


def parse_frontmatter(content: str) -> Tuple[Dict[str, str], str]:
    """Extracts YAML frontmatter if present and returns (frontmatter_dict, remaining_body)."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content

    raw_yaml = match.group(1)
    body = match.group(2)
    meta = {}
    for line in raw_yaml.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip().strip("\"'")
    return meta, body


def split_markdown_sections(body: str) -> List[Tuple[str, str]]:
    """Splits markdown content into a list of (heading_title, section_text)."""
    lines = body.splitlines()
    sections: List[Tuple[str, str]] = []
    current_title = "Introduction"
    current_lines: List[str] = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block

        heading_match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading_match and not in_code_block:
            if current_lines:
                sections.append((current_title, "\n".join(current_lines)))
                current_lines = []
            current_title = heading_match.group(2).strip()
            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines)))

    return sections


def classify_section(title: str, text: str) -> str:
    """Classifies a section as 'work', 'persona', or 'shared'."""
    lower_title = title.lower()
    lower_text = text.lower()

    persona_score = sum(1 for kw in PERSONA_KEYWORDS if kw in lower_title) * 3
    persona_score += sum(1 for kw in PERSONA_KEYWORDS if kw in lower_text)

    proc_score = sum(1 for kw in PROCEDURE_KEYWORDS if kw in lower_title) * 3
    proc_score += sum(1 for kw in PROCEDURE_KEYWORDS if kw in lower_text)

    # Code blocks strongly indicate procedural work
    code_blocks = len(re.findall(r"```[a-zA-Z0-9_-]*", text))
    proc_score += code_blocks * 2

    if persona_score > proc_score * 1.5:
        return "persona"
    if proc_score > persona_score * 1.2:
        return "work"
    return "shared"


def distill_skill(content: str, base_name: str = "agent-skill") -> Tuple[str, str]:
    """
    Distills skill content into (work_skill_markdown, persona_skill_markdown).
    """
    meta, body = parse_frontmatter(content)
    sections = split_markdown_sections(body)

    work_sections: List[str] = []
    persona_sections: List[str] = []

    for title, text in sections:
        classification = classify_section(title, text)
        if classification == "persona":
            persona_sections.append(text)
        elif classification == "work":
            work_sections.append(text)
        else:
            # Shared: include in both if relevant
            work_sections.append(text)
            persona_sections.append(text)

    skill_title = meta.get("name", base_name)
    skill_desc = meta.get("description", "Distilled Agent Skill")

    work_skill_md = (
        f"---\n"
        f"name: {skill_title}-work\n"
        f"description: \"Procedural execution guide for {skill_desc}\"\n"
        f"type: procedural_work_skill\n"
        f"---\n\n"
        f"# {skill_title} — Procedural Work Skill\n\n"
        + "\n\n".join(work_sections).strip() + "\n"
    )

    persona_skill_md = (
        f"---\n"
        f"name: {skill_title}-persona\n"
        f"description: \"Cognitive heuristics, persona invariants and communication for {skill_desc}\"\n"
        f"type: cognitive_persona_skill\n"
        f"---\n\n"
        f"# {skill_title} — Cognitive Persona Skill\n\n"
        + "\n\n".join(persona_sections).strip() + "\n"
    )

    return work_skill_md, persona_skill_md


def distill_file(input_path: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
    """Reads a file, distills it, and writes work_skill.md & persona_skill.md."""
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input skill file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    out_dir = output_dir or os.path.dirname(os.path.abspath(input_path))
    os.makedirs(out_dir, exist_ok=True)

    work_md, persona_md = distill_skill(content, base_name=base_name)

    work_path = os.path.join(out_dir, "work_skill.md")
    persona_path = os.path.join(out_dir, "persona_skill.md")

    with open(work_path, "w", encoding="utf-8") as f:
        f.write(work_md)

    with open(persona_path, "w", encoding="utf-8") as f:
        f.write(persona_md)

    return work_path, persona_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Dual-Skill Distillation Engine (titanwings/distilly pattern)")
    parser.add_argument("input", help="Path to input SKILL.md or guideline file")
    parser.add_argument("--out-dir", default=None, help="Output directory for work_skill.md and persona_skill.md")
    args = parser.parse_args()

    work_p, persona_p = distill_file(args.input, args.out_dir)
    print(f"✅ Successfully distilled dual skills:")
    print(f"   - Procedural Work Skill: {work_p}")
    print(f"   - Cognitive Persona:     {persona_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
