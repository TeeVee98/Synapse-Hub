#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/validate_skills_schema.py — Standalone Skill Schema & Policy Validator
Validates all skills against:
  - Layer 1: Upstream Schema Conformance (Agent Skills Specification v1.0)
  - Layer 2: Synapse Policy Extensions (Policies, 5 Sections, Code Blocks, Links & Pinning)
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


import sys
import re
import json
import argparse
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ALLOWED_CATEGORIES = {
    "test_automation_and_execution",
    "architecture_and_analysis",
    "verification_and_resilience",
    "context_and_optimization",
}

ALLOWED_POLICIES = {
    "network": {"none", "localhost-only", "sandbox-only"},
    "shell": {"none", "read-only", "workspace-sandbox"},
    "filesystem": {"read-only", "workspace-sandbox"},
}

SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+$")
SKILL_NAME_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MD_LINK_REGEX = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
GITHUB_ACTION_REGEX = re.compile(r"uses:\s*actions/([a-zA-Z0-9_-]+)@([^\s#]+)")
COMMIT_SHA_40_REGEX = re.compile(r"^[0-9a-f]{40}$")

# Unproven quantitative / superlative claims patterns
UNPROVEN_CLAIMS_PATTERNS = [
    re.compile(r"98%\s+of\s+all\s+risky\s+logic", re.IGNORECASE),
    re.compile(r"80%\s+of\s+daily\s+test\s+automation\s+defects", re.IGNORECASE),
    re.compile(r"100%\s+selector\s+hit\s+rate", re.IGNORECASE),
    re.compile(r"100%\s+in\s+200ms", re.IGNORECASE),
    re.compile(r"Infinite\s+CI/CD\s+replays\s+with\s+0\s+LLM\s+Tokens", re.IGNORECASE),
    re.compile(r"100%\s+stable\s+tests\s*\(Zero\s+Flaky\s+Disruptions\)", re.IGNORECASE),
]

REQUIRED_SECTION_PATTERNS = [
    (1, re.compile(r"^##\s+1\.\s+Trigger\s*&\s*Activation", re.IGNORECASE | re.MULTILINE), "1. Trigger & Activation ('Use when...')"),
    (2, re.compile(r"^##\s+2\.\s+Non-Goals?\s*&\s*Boundary\s*Constraints?", re.IGNORECASE | re.MULTILINE), "2. Non-Goals & Boundary Constraints"),
    (3, re.compile(r"^##\s+3\.\s+Ordered\s+Execution\s+Workflow", re.IGNORECASE | re.MULTILINE), "3. Ordered Execution Workflow"),
    (4, re.compile(r"^##\s+4\.\s+Verification\s+Points?\s*&\s*DoD", re.IGNORECASE | re.MULTILINE), "4. Verification Points & DoD"),
    (5, re.compile(r"^##\s+5\.\s+Handoff\s+Protocol", re.IGNORECASE | re.MULTILINE), "5. Handoff Protocol"),
]

# Backtick reference path pattern: matches backtick paths like `dir/file.ext` or `reports/file.json`
BACKTICK_PATH_REGEX = re.compile(r"`([a-zA-Z0-9_.-]+/[a-zA-Z0-9_./-]+\.[a-zA-Z0-9_-]+)`")


@dataclass
class CodeBlockInfo:
    language: str
    classification: str  # "runnable" | "pseudocode" | "illustrative" | "unclassified"
    code: str
    start_line: int
    has_prerequisites: bool = False
    has_test_data: bool = False
    has_expected_output: bool = False


def classify_code_blocks(file_content: str) -> List[CodeBlockInfo]:
    """
    Parses markdown content and extracts all fenced code blocks with language,
    classification (runnable, pseudocode, illustrative), and metadata.
    """
    blocks: List[CodeBlockInfo] = []
    lines = file_content.splitlines()
    in_block = False
    current_lang = ""
    current_lines: List[str] = []
    block_start_line = 0
    preceding_comment_classification: Optional[str] = None
    preceding_comment_line = -10

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()

        # Check for HTML comment classification tag immediately preceding code block
        comment_match = re.search(
            r"<!--\s*classification:\s*(runnable|pseudocode|illustrative)\s*-->",
            stripped,
            re.IGNORECASE,
        )
        if comment_match:
            preceding_comment_classification = comment_match.group(1).lower()
            preceding_comment_line = idx
            continue

        if stripped.startswith("```"):
            if not in_block:
                # Starting a code block
                in_block = True
                current_lang = stripped[3:].strip()
                current_lines = []
                block_start_line = idx
            else:
                # Ending a code block
                in_block = False
                code_text = "\n".join(current_lines)

                # Determine classification
                classification = "unclassified"
                # 1. Check preceding HTML comment if it was within 2 lines
                if preceding_comment_classification and (block_start_line - preceding_comment_line <= 2):
                    classification = preceding_comment_classification

                # 2. Check if first few lines inside code block specify classification
                if classification == "unclassified":
                    for c_line in current_lines[:3]:
                        inline_match = re.search(
                            r"(?:#|//|--|<!--)\s*classification:\s*(runnable|pseudocode|illustrative)",
                            c_line,
                            re.IGNORECASE,
                        )
                        if inline_match:
                            classification = inline_match.group(1).lower()
                            break

                # 3. Check runnable metadata
                has_prereq = bool(
                    re.search(r"(?i)(?:#|//|--)\s*(?:prerequisites?|requirements?):", code_text)
                )
                has_data = bool(
                    re.search(
                        r"(?i)(?:#|//|--)\s*(?:test\s*data|sample\s*payload|seed\s*data|sample\s*data):",
                        code_text,
                    )
                )
                has_output = bool(
                    re.search(
                        r"(?i)(?:#|//|--)\s*(?:expected\s*output|expected\s*result|expected\s*response):",
                        code_text,
                    )
                )

                blocks.append(
                    CodeBlockInfo(
                        language=current_lang,
                        classification=classification,
                        code=code_text,
                        start_line=block_start_line,
                        has_prerequisites=has_prereq,
                        has_test_data=has_data,
                        has_expected_output=has_output,
                    )
                )

                # Reset preceding comment tracking
                preceding_comment_classification = None
                preceding_comment_line = -10
        elif in_block:
            current_lines.append(line)
        else:
            # If line is non-empty and not a comment, invalidate distant preceding comment
            if stripped and not comment_match:
                if idx - preceding_comment_line > 2:
                    preceding_comment_classification = None

    return blocks


def parse_yaml_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str, List[str]]:
    """
    Extracts and parses YAML frontmatter without external pyyaml dependency.
    Falls back to yaml.safe_load if pyyaml is installed.
    """
    errors: List[str] = []
    if not content.startswith("---"):
        return None, "", ["File does not start with '---' delimiter on line 1"]

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return None, "", ["Frontmatter missing closing '---' delimiter"]

    fm_text = match.group(1)
    body = match.group(2)

    # If PyYAML is available, use it directly
    if importlib.util.find_spec("yaml") is not None:
        import yaml
        try:
            data = yaml.safe_load(fm_text)
            if isinstance(data, dict):
                return data, body, []
            errors.append("PyYAML failed to parse frontmatter as a dictionary")
            return None, "", errors
        except yaml.YAMLError as y_err:
            errors.append(f"PyYAML syntax error: {y_err}")
            return None, "", errors

    # Pure Python stdlib parser for frontmatter
    data: Dict[str, Any] = {}
    current_section: Optional[str] = None

    for line_no, raw_line in enumerate(fm_text.splitlines(), 1):
        line = raw_line.rstrip()
        if not line or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if indent == 0:
            if ":" not in stripped:
                errors.append(f"Line {line_no}: Invalid YAML key-value syntax: '{stripped}'")
                continue
            key, val = stripped.split(":", 1)
            key, val = key.strip(), val.strip()
            if not val:
                current_section = key
                data[current_section] = {}
            else:
                current_section = None
                data[key] = val.strip("\"'")
        elif indent >= 2 and current_section:
            if ":" not in stripped:
                errors.append(f"Line {line_no}: Invalid child YAML syntax in '{current_section}': '{stripped}'")
                continue
            ckey, cval = stripped.split(":", 1)
            ckey, cval = ckey.strip(), cval.strip().strip("\"'")
            if isinstance(data.get(current_section), dict):
                data[current_section][ckey] = cval

    return data, body, errors


def validate_upstream_schema(skill_data: Dict[str, Any], file_content: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Layer 1: Upstream Schema Conformance (Agent Skills Specification v1.0).
    Validates name, description, and markdown AST heading structure.
    """
    errors: List[str] = []

    # 1. Name check
    name = skill_data.get("name")
    if not name or not str(name).strip():
        errors.append("Missing required field: 'name'")
    else:
        name_str = str(name).strip()
        if len(name_str) > 64:
            errors.append(f"Field 'name' length ({len(name_str)}) exceeds 64 characters")
        if not SKILL_NAME_REGEX.match(name_str):
            errors.append(f"Invalid 'name' format: '{name_str}' (must be lowercase alphanumeric + hyphens)")

    # 2. Description check
    desc = skill_data.get("description")
    if not desc or not str(desc).strip():
        errors.append("Missing required field: 'description'")
    else:
        desc_str = str(desc).strip()
        if len(desc_str) > 1024:
            errors.append(f"Description length ({len(desc_str)}) exceeds 1024 characters")
        if "use when" not in desc_str.lower():
            errors.append("Description missing mandatory activation trigger clause ('Use when...')")

    # 3. Heading check if content provided
    if file_content is not None:
        if not re.search(r"^##?\s+", file_content, re.MULTILINE):
            errors.append("Body missing standard markdown section headings ('## ...')")

    return (len(errors) == 0, errors)


def find_repo_root(start_path: Path) -> Path:
    """Finds repository root by searching for .git, pyproject.toml, or tools directory."""
    current = start_path.resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists() or (parent / "tools").exists():
            return parent
    return current.parents[3] if len(current.parents) >= 4 else current


def validate_synapse_policy_extensions(
    skill_data: Dict[str, Any],
    file_content: str,
    file_path: str,
    check_links: bool = True,
) -> Tuple[bool, List[str]]:
    """
    Layer 2: Synapse Policy Extensions.
    Validates category, version, policies, examples/ directory, 5 required sections,
    code block classification, GitHub Actions SHA pinning, unproven claims heuristic,
    and link & backtick reference resolution.
    """
    errors: List[str] = []
    skill_file = Path(file_path).resolve()
    skill_dir = skill_file.parent
    repo_root = find_repo_root(skill_dir)

    # 1. Category check
    category = skill_data.get("category")
    if not category:
        errors.append("Missing required field: 'category'")
    elif category not in ALLOWED_CATEGORIES:
        errors.append(f"Invalid category '{category}'. Must be one of: {sorted(ALLOWED_CATEGORIES)}")

    # 2. Version check
    version = skill_data.get("version")
    if not version:
        errors.append("Missing required field: 'version'")
    elif not SEMVER_REGEX.match(str(version).strip("\"'")):
        errors.append(f"Invalid version format '{version}'. Must conform to SemVer (e.g. '1.0.0')")

    # 3. Policies check
    policies = skill_data.get("policies")
    if policies is None:
        errors.append("Missing required field: 'policies'")
    elif not isinstance(policies, dict):
        errors.append(f"'policies' must be a dictionary object, got {type(policies).__name__}")
    else:
        for pol_key, allowed_vals in ALLOWED_POLICIES.items():
            val = policies.get(pol_key)
            if not val:
                errors.append(f"Missing required policy: 'policies.{pol_key}'")
            elif val not in allowed_vals:
                errors.append(f"Invalid value '{val}' for 'policies.{pol_key}'. Must be one of: {sorted(allowed_vals)}")

    # 4. Mandatory examples/ directory check
    examples_dir = skill_dir / "examples"
    if not examples_dir.is_dir():
        errors.append("Missing mandatory 'examples/' directory (Progressive Disclosure L3)")
    elif not list(examples_dir.iterdir()):
        errors.append("'examples/' directory is empty")

    for l2_name in ("references", "resources"):
        l2_dir = skill_dir / l2_name
        if l2_dir.is_dir() and not list(l2_dir.iterdir()):
            errors.append(f"Progressive disclosure directory '{l2_name}/' exists but is empty")

    # 5. Standard 5 Required Sections Check
    for sec_num, pattern, sec_title in REQUIRED_SECTION_PATTERNS:
        if not pattern.search(file_content):
            errors.append(f"Missing required section: '## {sec_title}'")

    # 6. Code Block Classification and Language Tag Audit
    blocks = classify_code_blocks(file_content)
    for b in blocks:
        # Ignore mermaid diagrams for code language tag enforcement
        if not b.language.strip():
            errors.append(f"Line {b.start_line}: Code block missing language identifier tag (bare ```)")
        elif b.language.lower() != "mermaid":
            if b.classification not in ("runnable", "pseudocode", "illustrative"):
                errors.append(
                    f"Line {b.start_line}: Code block not classified. Must be tagged with "
                    "<!-- classification: runnable -->, <!-- classification: pseudocode -->, "
                    "or <!-- classification: illustrative -->"
                )
            elif b.classification == "runnable":
                missing_meta = []
                if not b.has_prerequisites:
                    missing_meta.append("# Prerequisites:")
                if not b.has_test_data:
                    missing_meta.append("# Test Data:")
                if not b.has_expected_output:
                    missing_meta.append("# Expected Output:")
                if missing_meta:
                    errors.append(
                        f"Line {b.start_line}: Runnable code block missing required execution metadata: "
                        + ", ".join(missing_meta)
                    )

    # 7. GitHub Actions Commit SHA Pinning Check
    for match in GITHUB_ACTION_REGEX.finditer(file_content):
        action_name = match.group(1)
        ref = match.group(2)
        if not COMMIT_SHA_40_REGEX.match(ref):
            errors.append(
                f"Unpinned GitHub Action detected: 'actions/{action_name}@{ref}'. "
                "Must be pinned to immutable 40-character commit SHA with version tag comment"
            )

    # 8. Unproven Quantitative Claims Check
    for pat in UNPROVEN_CLAIMS_PATTERNS:
        claim_match = pat.search(file_content)
        if claim_match:
            errors.append(
                f"Unproven quantitative/superlative claim detected: '{claim_match.group(0)}'. "
                "Must be replaced with contextual engineering heuristic"
            )

    # 9. Link and Backtick Reference Resolution
    if check_links:
        # Markdown links
        for match in MD_LINK_REGEX.finditer(file_content):
            target = match.group(2).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Check depth-4 excessive parent traversal link
            if "../../../../" in target:
                errors.append(
                    f"Excessive root-escaping parent traversal in relative link: '{target}'. "
                    "Use direct or intra-skill relative references"
                )
                continue
            clean_target = target.split("#")[0].split("?")[0].strip()
            if not clean_target:
                continue
            resolved = (skill_dir / clean_target).resolve()
            if not resolved.exists():
                errors.append(f"Broken relative link: '{target}' (resolved to non-existent path: {resolved})")

        # Backtick references: check paths matching repository or skill files
        for match in BACKTICK_PATH_REGEX.finditer(file_content):
            ref_path = match.group(1).strip()
            # Skip generated output directories and target project artifacts
            if any(ref_path.startswith(prefix) for prefix in ("graphify-out/", "reports/", "Reports/", "Keywords/", "build/", "dist/", "Screenshots/", ".sandbox")):
                continue
            # Only validate references that target files in known source/config directories
            if any(ref_path.startswith(prefix) for prefix in (".github/", "templates/")):
                # Check against repo root
                resolved_repo_file = (repo_root / ref_path).resolve()
                if not resolved_repo_file.exists():
                    errors.append(
                        f"Broken internal file reference in backticks: '`{ref_path}`' "
                        f"(resolved to non-existent path: {resolved_repo_file})"
                    )

    return (len(errors) == 0, errors)


def validate_skill(
    skill_md_path: Path,
    check_links: bool = True,
    layer: str = "all",
) -> List[str]:
    """Validates a single SKILL.md file against the specification and selected layer."""
    errors: List[str] = []
    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Cannot read file: {e}"]

    fm, body, parse_errors = parse_yaml_frontmatter(content)
    if parse_errors:
        return parse_errors
    if fm is None:
        return ["Failed to parse frontmatter"]

    expected_name = skill_md_path.parent.name
    actual_name = fm.get("name")

    # Layer 1: Upstream Schema Conformance
    if layer in ("upstream", "all"):
        if actual_name and actual_name != expected_name:
            errors.append(f"Field 'name' ('{actual_name}') does not match directory name ('{expected_name}')")
        ok_up, up_errs = validate_upstream_schema(fm, file_content=body)
        errors.extend(up_errs)

    # Layer 2: Synapse Policy Extensions
    if layer in ("policy", "all"):
        ok_pol, pol_errs = validate_synapse_policy_extensions(
            skill_data=fm,
            file_content=content,
            file_path=str(skill_md_path),
            check_links=check_links,
        )
        errors.extend(pol_errs)

    return errors


def check_handoff_boilerplate_diversity(
    skill_files: List[str],
    max_identical: int = 4,
) -> Tuple[bool, List[str]]:
    """Verifies that SKILL.md Handoff Output Format lines are domain-specific, not copy-pasted boilerplate."""
    from collections import Counter

    counts: Counter[str] = Counter()
    for sf in skill_files:
        try:
            txt = Path(sf).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        m = re.search(r"Output\s+Format:\*\*\s*(.+)", txt, re.IGNORECASE)
        if m:
            norm = re.sub(r"\s+", " ", m.group(1).strip())
            counts[norm] += 1

    violations = [
        f"Boilerplate Output Format duplicated {cnt}x (> {max_identical}): '{fmt}'"
        for fmt, cnt in counts.items()
        if cnt > max_identical
    ]
    return len(violations) == 0, violations


def run_validation(
    skills_dir: Path,
    check_links: bool = True,
    layer: str = "all",
) -> Tuple[int, Dict[str, List[str]]]:
    """Scans all skills under skills_dir and validates each SKILL.md for the given layer."""
    results: Dict[str, List[str]] = {}
    skill_files = sorted(skills_dir.glob("*/*/SKILL.md"))
    if not skill_files:
        manifest_candidates = [
            skills_dir / "skills_manifest.json",
            skills_dir.parent / "skills_manifest.json",
            skills_dir.parent.parent / "skills_manifest.json",
        ]
        for mc in manifest_candidates:
            if mc.is_file():
                import json
                with open(mc, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                repo_root = mc.parent
                for s in manifest_data.get("skills", []):
                    sp = repo_root / s.get("path", "")
                    if sp.is_file():
                        skill_files.append(sp)
                break
    for sf in skill_files:
        rel_path = sf.as_posix()
        errs = validate_skill(sf, check_links=check_links, layer=layer)
        if errs:
            results[rel_path] = errs

    if layer in ("policy", "all") and skill_files:
        ok_div, dup_msgs = check_handoff_boilerplate_diversity([str(sf) for sf in skill_files], max_identical=4)
        if not ok_div:
            results["_catalog_boilerplate_check"] = dup_msgs

    return len(skill_files), results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Agent Skills frontmatter schema and Synapse policies across layers."
    )
    parser.add_argument(
        "--skills-dir",
        type=str,
        default="skills",
        help="Path to the unified skills directory (default: skills)",
    )
    parser.add_argument(
        "--layer",
        choices=["upstream", "policy", "all"],
        default="all",
        help="Validation layer to execute: 'upstream' (Agent Skills v1.0 schema), 'policy' (Synapse extensions), or 'all' (default: all)",
    )
    parser.add_argument(
        "--check-links",
        action="store_true",
        default=True,
        help="Verify existence of relative markdown resource links and backtick paths (default: True)",
    )
    parser.add_argument(
        "--no-check-links",
        action="store_false",
        dest="check_links",
        help="Disable relative markdown resource link checking",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--sync-manifest",
        action="store_true",
        default=False,
        help="Synchronize skills frontmatter policies into skills_manifest.json",
    )
    parser.add_argument(
        "--manifest",
        default="skills_manifest.json",
        help="Path to skills_manifest.json (used with --sync-manifest)",
    )

    args = parser.parse_args()
    skills_path = Path(args.skills_dir).resolve()

    if not skills_path.exists():
        if (Path.cwd() / "skills_manifest.json").is_file():
            skills_path = Path.cwd()
        else:
            print(f"Error: Skills directory not found at {skills_path}", file=sys.stderr)
            return 1

    if args.sync_manifest:
        try:
            from tools.core.sync_skills_manifest import sync_manifest
        except ImportError:
            try:
                from sync_skills_manifest import sync_manifest
            except ImportError:
                sync_manifest = None
        if sync_manifest:
            manifest_p = Path(args.manifest).resolve()
            in_sync, diffs = sync_manifest(skills_path, manifest_p, write=True)
            if not in_sync:
                print(f"🔄 Synchronized {len(diffs)} items in {manifest_p}")
            else:
                print(f"✅ skills_manifest.json is in sync with {skills_path}")

    total_scanned, failures = run_validation(
        skills_path,
        check_links=args.check_links,
        layer=args.layer,
    )

    if args.json:
        output_payload = {
            "total_skills": total_scanned,
            "layer": args.layer,
            "valid_skills": total_scanned - len(failures),
            "failed_skills": len(failures),
            "passed": len(failures) == 0,
            "failures": failures,
        }
        print(json.dumps(output_payload, indent=2))
        return 0 if len(failures) == 0 else 1

    print(f"\n🔍 Validating {total_scanned} skills in {skills_path} [Layer: {args.layer}]...")
    if args.check_links and args.layer in ("policy", "all"):
        print("🔗 Checking relative markdown links and backtick references...")

    if not failures:
        print(f"✅ 100% Verified: All {total_scanned} skills conform to layer '{args.layer}'.")
        return 0

    print(f"❌ Validation failed: {len(failures)}/{total_scanned} skills have errors in layer '{args.layer}':\n")
    for file_path, err_list in failures.items():
        print(f"  • {file_path}:")
        for err in err_list:
            print(f"      - {err}")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
