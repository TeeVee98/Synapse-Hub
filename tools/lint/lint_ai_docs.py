#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Enterprise AI Documentation & Artifact Linter (Anti-Drift Guard v2.0)
---------------------------------------------------------------
Automatically cross-references AI skills, agent instructions, and markdown
documents against the actual repository files, classes, methods, and test cases.

Checks:
  1. Page Class references: Matches against Keywords/pages/*.groovy.
  2. Test Suite references: Matches against Test Suites/*.ts.
  3. Tool script references: Matches against tools/*.
  4. Test Case references: Matches against Test Cases/*.tc (and validates TC-1..259 range).
  5. Method call references: Matches EnterpriseHelper.xxx() and BasePage.xxx() against real AST/regex methods.

Prevents AI agents from hallucinating nonexistent PageClasses, suites, tools, methods, or test cases.
Supports both Target Test Project mode and Hub Repository mode.
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
import glob
import re
from dataclasses import dataclass, field
from typing import List, Optional

ENTRY_DOC_PATHS = [
    "README.md",
    "README.en.md",
    "SECURITY.md",
    ".github/CONTRIBUTING.md",
    "docs/ARCHITECTURE.md",
    "docs/ARCHITECTURE.en.md",
    "docs/QUALITY_GATES.md",
    "docs/QUALITY_GATES.en.md",
    "docs/CLI_REFERENCE.md",
    "docs/CLI_REFERENCE.en.md",
    "docs/CI_CD_INTEGRATION.md",
    "docs/CI_CD_INTEGRATION.en.md",
    "docs/CONTRIBUTING.md",
    "docs/CONTRIBUTING.en.md",
    "docs/MCP_SETUP.md",
    "docs/MCP_SETUP.en.md",
    "docs/CLIENT_SUPPORT_MATRIX.md",
]

_IGNORED_LINK_AUDIT_DOCS = {
    "AUDIT_REPORT.md",
    "AUDIT_REMEDIATION_PLAN.md",
    "PERFORMANCE_AUDIT_REPORT.md",
    "CHANGELOG.md",
    "implementation_plan.md",
}

_EXTERNAL_OR_ANCHOR_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "data:",
    "javascript:",
    "#",
)


@dataclass(frozen=True)
class BrokenMarkdownLinkDTO:
    """Represents a broken relative Markdown link found in documentation."""

    source_doc: str
    line_number: int
    link_label: str
    target_path: str


@dataclass(frozen=True)
class EntryDocAuditResultDTO:
    """Aggregated audit result for entry-point documentation checks."""

    checked_docs: List[str]
    broken_links: List[BrokenMarkdownLinkDTO] = field(default_factory=list)
    metric_errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DocCodeFenceAuditDTO:
    """Audit result from scanning canonical skill code blocks for banned anti-patterns."""

    scanned_blocks: int
    violations: List[str] = field(default_factory=list)

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

GENERIC_PAGES = {
    "WebPage", "CurrentPage", "LandingPage", "GitHubPage", "SamplePage",
    "BasePage", "Page", "SinglePage", "MultiPage"
}

def extract_groovy_methods(file_path):
    """Extracts standard public/static methods from a Groovy class file."""
    methods = set()
    if not os.path.exists(file_path):
        return methods
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
            lines = fp.readlines()
        method_pattern = re.compile(
            r'^\s*(?:@\w+\s+)*(?:public|protected|private)?\s*(?:static\s+)?(?:final\s+)?'
            r'(?:void|def|String|int|boolean|List[^\s]*|TestObject|WebDriver|[A-Za-z0-9_<>\[\]]+)\s+([a-z][a-zA-Z0-9_]*)\s*\('
        )
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            m = method_pattern.search(line)
            if m:
                mname = m.group(1)
                if mname not in {"if", "for", "while", "switch", "catch"}:
                    methods.add(mname)
    except (OSError, UnicodeDecodeError) as err:
        sys.stderr.write(f"Notice: Parse methods skipped for {file_path}: {err}\n")
    return methods

def get_actual_entities(repo_root):
    pages_dir = os.path.join(repo_root, "Keywords", "pages")
    helpers_dir = os.path.join(repo_root, "Keywords", "helpers")
    suites_dir = os.path.join(repo_root, "Test Suites")
    cases_dir = os.path.join(repo_root, "Test Cases")
    tools_dir = os.path.join(repo_root, "tools")

    actual_pages = set()
    class_methods = {}

    if os.path.isdir(pages_dir):
        for f in os.listdir(pages_dir):
            if f.endswith(".groovy"):
                pname = f[:-7]
                actual_pages.add(pname)
                class_methods[pname] = extract_groovy_methods(os.path.join(pages_dir, f))

    if os.path.isdir(helpers_dir):
        for f in os.listdir(helpers_dir):
            if f.endswith(".groovy"):
                hname = f[:-7]
                class_methods[hname] = extract_groovy_methods(os.path.join(helpers_dir, f))

    actual_suites = set()
    if os.path.isdir(suites_dir):
        for f in os.listdir(suites_dir):
            if f.endswith(".ts"):
                actual_suites.add(f[:-3])

    actual_cases = set()
    actual_tc_ids = set()
    if os.path.isdir(cases_dir):
        for f in os.listdir(cases_dir):
            if f.endswith(".tc"):
                base_name = f[:-3]
                actual_cases.add(base_name)
                m = re.match(r'(TC-\d+)', base_name)
                if m:
                    actual_tc_ids.add(m.group(1))

    actual_tools = set()
    if os.path.isdir(tools_dir):
        for _root, _, _files in os.walk(tools_dir):
            actual_tools.update(_files)
    # Always include Hub tools directory in decoupled architecture
    hub_tools = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if os.path.isdir(hub_tools):
        for _root, _, _files in os.walk(hub_tools):
            actual_tools.update(_files)

    return actual_pages, actual_suites, actual_cases, actual_tc_ids, actual_tools, class_methods

def find_doc_files(repo_root):
    md_patterns = [
        os.path.join(repo_root, ".agents", "**", "*.md"),
        os.path.join(repo_root, "ai-agents", "**", "*.md"),
        os.path.join(repo_root, "docs", "**", "*.md"),
        os.path.join(repo_root, "standards", "**", "*.md"),
        os.path.join(repo_root, "templates", "**", "*.md"),
        os.path.join(repo_root, "skills", "**", "*.md"),
        os.path.join(repo_root, "testing", "**", "*.md"),
        os.path.join(repo_root, "requirement", "**", "*.md"),
        os.path.join(repo_root, ".cursor", "rules", "*.mdc"),
        os.path.join(repo_root, ".github", "**", "*.md"),
        os.path.join(repo_root, "CLAUDE.md"),
        os.path.join(repo_root, "AGENTS.md"),
        os.path.join(repo_root, "*.md"),
    ]
    doc_files = []
    for pattern in md_patterns:
        for f in glob.glob(pattern, recursive=True):
            if not os.path.isfile(f):
                continue
            rel = os.path.relpath(f, repo_root).replace("\\", "/")
            if any(ignored in rel for ignored in ("node_modules", ".git", "allure-results", "teamwork", "external_repos", "AUDIT_REPORT", "FINAL_REPORT", "AUDIT_REMEDIATION_PLAN", "docs/reports", "docs/research")):
                continue
            doc_files.append(rel)
    return sorted(list(set(doc_files)))

def lint_docs(repo_root):
    actual_pages, actual_suites, actual_cases, actual_tc_ids, actual_tools, class_methods = get_actual_entities(repo_root)
    doc_files = find_doc_files(repo_root)

    page_pattern = re.compile(r'\b([A-Z][A-Za-z0-9]+Page)\b')
    suite_pattern = re.compile(r'(?:Test Suites/|-Suite\s+["\'](?:Test Suites/)?|--testSuitePath=["\'](?:Test Suites/)?)([A-Za-z0-9_]+)')
    tool_pattern = re.compile(r'\b(tools/[a-zA-Z0-9_\-/]+\.(?:py|sh|ps1|bat|js))\b')
    tc_id_pattern = re.compile(r'\b(TC-\d+)\b')
    tc_path_pattern = re.compile(r'Test Cases/([A-Za-z0-9_ \-\.\(\)]+?)(?:\.tc)?["\s\)]')
    method_pattern = re.compile(r'\b(EnterpriseHelper|BasePage|[A-Z][a-zA-Z0-9]+Page)\.([a-z][a-zA-Z0-9_]+)\s*\(')

    errors = []
    warnings = []

    # Ignored tool references (examples, output targets, artifacts)
    ignored_tool_refs = {"api_matrix.json", "output.json", "report.json", "output.txt", "summary.json", "custom_security_headers.py"}

    # 6. Hub Mode Metadata & Count Synchronization (Anti-Drift Guard for Skills, Rules, Workflows)
    manifest_path = os.path.join(repo_root, "skills_manifest.json")
    skills_dir = os.path.join(repo_root, "skills")
    if not os.path.isdir(skills_dir):
        skills_dir = os.path.join(repo_root, ".agents", "skills")
    rules_dir = os.path.join(repo_root, ".agents", "rules")
    workflows_dir = os.path.join(repo_root, "ai-agents", "workflows")
    if not os.path.isdir(workflows_dir):
        workflows_dir = os.path.join(repo_root, ".agents", "workflows")

    if os.path.exists(manifest_path) and os.path.isdir(skills_dir):
        import json
        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest_data = json.load(mf)
            manifest_skill_ids = set(s.get("id") for s in manifest_data.get("skills", []))
            # v4.0: skills are 2 levels deep (domain/skill-id/SKILL.md)
            actual_skill_dirs = set()
            for s in manifest_data.get("skills", []):
                sp = s.get("path", "")
                sid = s.get("id", "")
                if sp and os.path.isfile(os.path.join(repo_root, sp)):
                    actual_skill_dirs.add(sid)
            if os.path.isdir(skills_dir):
                for domain_entry in os.listdir(skills_dir):
                    domain_path = os.path.join(skills_dir, domain_entry)
                    if not os.path.isdir(domain_path):
                        continue
                    for skill_entry in os.listdir(domain_path):
                        skill_path = os.path.join(domain_path, skill_entry)
                        if os.path.isdir(skill_path):
                            actual_skill_dirs.add(skill_entry)
            unregistered = actual_skill_dirs - manifest_skill_ids
            if unregistered:
                errors.append(f"[skills_manifest.json] Skills on disk not in manifest: {sorted(unregistered)}")
            ghost_manifest = manifest_skill_ids - actual_skill_dirs
            if ghost_manifest:
                errors.append(f"[skills_manifest.json] Skills in manifest missing on disk: {sorted(ghost_manifest)}")

            total_declared = manifest_data.get("totalSkills", len(manifest_skill_ids))
            if total_declared != len(actual_skill_dirs):
                errors.append(f"[skills_manifest.json] totalSkills ({total_declared}) does not match actual count ({len(actual_skill_dirs)})")

            if os.path.isdir(rules_dir):
                actual_rules_count = len([f for f in os.listdir(rules_dir) if f.endswith(".md")])
            else:
                actual_rules_count = 0

            if os.path.isdir(workflows_dir):
                actual_workflows_count = len([f for f in os.listdir(workflows_dir) if f.endswith(".md")])
            else:
                actual_workflows_count = 0

            readme_path = os.path.join(repo_root, "README.md")
            if os.path.exists(readme_path):
                with open(readme_path, "r", encoding="utf-8", errors="ignore") as rf:
                    readme_text = rf.read()
                m_rules = re.search(r'\((\d+)\s+Core Rules\)', readme_text)
                if m_rules and int(m_rules.group(1)) != actual_rules_count:
                    errors.append(f"[README.md] Documented Core Rules count ({m_rules.group(1)}) differs from actual rules on disk ({actual_rules_count})")

                m_wf = re.search(r'\((\d+)\s+Workflows\)', readme_text)
                if m_wf and int(m_wf.group(1)) != actual_workflows_count:
                    errors.append(f"[README.md] Documented Workflows count ({m_wf.group(1)}) differs from actual workflows on disk ({actual_workflows_count})")

                skill_table_matches = re.findall(r'\|\s*\d+\s*\|\s*`([a-z0-9\-]+)`\s*\|', readme_text)
                for sid in skill_table_matches:
                    if sid not in actual_skill_dirs:
                        errors.append(f"[README.md] Non-existent skill referenced in skills table: '{sid}'")

            arch_path = os.path.join(repo_root, "docs", "ARCHITECTURE.md")
            if os.path.exists(arch_path):
                with open(arch_path, "r", encoding="utf-8", errors="ignore") as af:
                    arch_text = af.read()
                m_arch_skills = re.search(r'Catalog\["(\d+)\s+Standardized Skills', arch_text)
                if m_arch_skills and int(m_arch_skills.group(1)) != len(actual_skill_dirs):
                    errors.append(f"[ARCHITECTURE.md] Documented skills count ({m_arch_skills.group(1)}) differs from actual skills on disk ({len(actual_skill_dirs)})")
        except Exception as e:
            errors.append(f"Failed to validate skills_manifest.json: {e}")

    for doc in doc_files:
        full_path = os.path.join(repo_root, doc)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                lines = fp.readlines()
        except Exception as e:
            errors.append(f"Cannot read {doc}: {e}")
            continue

        doc_normalized = doc.replace("\\", "/")
        is_managed_skill_doc = (
            doc_normalized.startswith(".agents/skills/")
            and os.path.isfile(os.path.join(repo_root, ".agents", "skills", ".synapse-managed.json"))
        )
        is_historical = (
            "FINAL_REPORT.md" in doc_normalized
            or "POM_REFACTORING_PLAN.md" in doc_normalized
            or "CHANGELOG.md" in doc_normalized
            or "AUDIT_REMEDIATION_PLAN.md" in doc_normalized
            or "docs/reports" in doc_normalized
            or "docs/research" in doc_normalized
        )

        for line_no, line in enumerate(lines, 1):
            # 1. Page Class Lint (Only strictly enforced if repository defines Page Classes in Keywords/pages)
            if actual_pages:
                for m in page_pattern.finditer(line):
                    pname = m.group(1)
                    if pname not in actual_pages and pname not in GENERIC_PAGES:
                        if is_historical or is_managed_skill_doc:
                            continue
                        errors.append(f"[{doc}:{line_no}] Non-existent Page Class referenced: '{pname}' (Must be one of {sorted(actual_pages)})")

            # 2. Test Suite Lint (Only strictly enforced if repository defines Test Suites)
            if actual_suites:
                for m in suite_pattern.finditer(line):
                    sname = m.group(1)
                    if "xxx" in sname.lower() or "example" in sname.lower():
                        continue
                    if is_historical or is_managed_skill_doc:
                        continue
                    if sname not in actual_suites:
                        errors.append(f"[{doc}:{line_no}] Non-existent Test Suite referenced: '{sname}'")

            # 3. Tool Script Lint (Physical file existence check on disk)
            for m in tool_pattern.finditer(line):
                tool_path = m.group(1)
                tname = os.path.basename(tool_path)
                if tname in ignored_tool_refs or tool_path in ignored_tool_refs:
                    continue
                if is_historical:
                    continue
                full_tool_path = os.path.join(repo_root, tool_path)
                if not os.path.isfile(full_tool_path):
                    hub_tool_path = os.path.join(_REPO_ROOT, tool_path)
                    if not os.path.isfile(hub_tool_path):
                        errors.append(f"[{doc}:{line_no}] Non-existent tool script referenced: '{tool_path}'")

            # 4. Test Case Validation (Only strictly enforced if repository defines Test Cases)
            if actual_cases and not (is_historical or is_managed_skill_doc):
                # 4a. Validate TC-xxx numeric range
                for m in tc_id_pattern.finditer(line):
                    tcid = m.group(1)
                    num = int(tcid[3:])
                    if num < 1 or num > 259:
                        errors.append(f"[{doc}:{line_no}] Out-of-range Test Case ID referenced: '{tcid}' (Valid range: TC-1 to TC-259)")

                # 4b. Validate full Test Cases/... paths
                for m in tc_path_pattern.finditer(line):
                    tcname = m.group(1).strip()
                    if "xxx" in tcname.lower() or "*" in tcname or "example" in tcname.lower():
                        continue
                    if tcname.endswith(".tc"):
                        tcname = tcname[:-3]
                    if tcname not in actual_cases:
                        # Check prefix match
                        matching = [c for c in actual_cases if c.startswith(tcname)]
                        if not matching:
                            errors.append(f"[{doc}:{line_no}] Non-existent Test Case path referenced: 'Test Cases/{tcname}'")

            # 5. Method Call Lint (Cross-checks Class.method() against Groovy AST/regex)
            for m in method_pattern.finditer(line):
                cname = m.group(1)
                mname = m.group(2)
                if "xxx" in mname.lower() or "example" in mname.lower():
                    continue
                if cname in class_methods:
                    valid_methods = class_methods[cname]
                    # Also include inherited BasePage methods if it's a Page class
                    if cname != "BasePage" and "BasePage" in class_methods:
                        valid_methods = valid_methods.union(class_methods["BasePage"])

                    if mname not in valid_methods:
                        errors.append(f"[{doc}:{line_no}] Non-existent method referenced: '{cname}.{mname}()' (Class '{cname}' does not define this method)")

    # 6. Documentation Metrics Consistency (Detects stale skill/tool/gate numbers)
    metric_errors = check_doc_metrics_consistency(repo_root)
    errors.extend(metric_errors)

    # 7. Entry-Point Relative Markdown Link Verification (Anti-Broken-Link Guard)
    link_errors = check_markdown_relative_links(repo_root, doc_paths=ENTRY_DOC_PATHS)
    errors.extend(link_errors)

    # 8. Canonical Skill Code-Fence Anti-Pattern Check (bans waitForTimeout / networkidle in SKILL.md)
    fence_audit = check_skill_code_fences(repo_root)
    errors.extend(fence_audit.violations)

    # 9. Bilingual Documentation Parity & Single-Source Bridge Parity (Hub Mode only)
    from tools.core.gates.base import detect_repo_mode

    if detect_repo_mode(repo_root) == "HUB":
        bilingual_pairs = [
            ("README.md", "README.en.md"),
            (os.path.join("docs", "ARCHITECTURE.md"), os.path.join("docs", "ARCHITECTURE.en.md")),
        ]
        for vi_rel, en_rel in bilingual_pairs:
            vi_path = os.path.join(repo_root, vi_rel)
            en_path = os.path.join(repo_root, en_rel)
            if os.path.exists(vi_path) and not os.path.exists(en_path):
                errors.append(f"Missing English bilingual documentation counterpart for {vi_rel}: expected {en_rel}")
            elif not os.path.exists(vi_path) and os.path.exists(en_path):
                errors.append(f"Missing Vietnamese bilingual documentation counterpart for {en_rel}: expected {vi_rel}")

        # Verify zero drift across generated IDE rule bridges when checking canonical Hub root
        if os.path.abspath(repo_root) == os.path.abspath(_REPO_ROOT):
            import io as _io
            from tools.core import sync_agent_rules
            _old_out = sys.stdout
            sys.stdout = _io.StringIO()
            try:
                sync_rc = sync_agent_rules.sync_all(check_only=True)
            finally:
                sys.stdout = _old_out
            if sync_rc != 0:
                errors.append(
                    "[sync_agent_rules] IDE bridge files (CLAUDE.md, .cursorrules, .windsurfrules, copilot-instructions.md) "
                    "drifted from canonical AGENTS.md. Run 'python tools/core/sync_agent_rules.py'."
                )

        # Verify tool script paths inside skill examples (.bats, .json, .sh)
        for ex_ext in ("*.bats", "*.json", "*.sh"):
            for ex_file in glob.glob(os.path.join(repo_root, "skills", "**", "examples", ex_ext), recursive=True):
                try:
                    with open(ex_file, "r", encoding="utf-8", errors="ignore") as ef:
                        ex_text = ef.read()
                    for m_tool in tool_pattern.finditer(ex_text):
                        t_rel = m_tool.group(1)
                        if os.path.basename(t_rel) in ignored_tool_refs or t_rel in ignored_tool_refs:
                            continue
                        if not os.path.isfile(os.path.join(repo_root, t_rel)):
                            rel_ex = os.path.relpath(ex_file, repo_root).replace("\\", "/")
                            errors.append(f"[{rel_ex}] Non-existent tool script referenced in skill example: '{t_rel}'")
                except OSError:
                    continue

    return errors, warnings


def check_skill_code_fences(repo_root: str) -> DocCodeFenceAuditDTO:
    """Scans fenced code blocks in skills/**/SKILL.md and references/*.md for banned wait anti-patterns."""
    skills_root = os.path.join(repo_root, "skills")
    if not os.path.isdir(skills_root):
        return DocCodeFenceAuditDTO(scanned_blocks=0, violations=[])

    banned_wait_re = re.compile(r"\bwaitForTimeout\s*\(")
    banned_netidle_re = re.compile(
        r"waitForLoadState\(\s*['\"]networkidle['\"]\s*\)|waitUntil\s*:\s*['\"]networkidle['\"]"
    )
    antipattern_comment_re = re.compile(
        r"(?:classification:\s*anti-pattern|anti-pattern|❌|\bavoid\b|\bnever\b|\bforbid|\bprohibit|\bban\b)",
        re.IGNORECASE,
    )

    scanned_blocks = 0
    violations: List[str] = []

    skill_docs = sorted(
        set(glob.glob(os.path.join(skills_root, "*", "*", "SKILL.md")))
        | set(glob.glob(os.path.join(skills_root, "*", "*", "references", "*.md")))
    )
    for skill_md in skill_docs:
        rel_doc = os.path.relpath(skill_md, repo_root).replace("\\", "/")
        try:
            with open(skill_md, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except OSError:
            continue

        in_fence = block_is_antipattern = False
        recent_lines: List[str] = []

        for line_no, raw_line in enumerate(lines, 1):
            stripped = raw_line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                if not in_fence:
                    in_fence = True
                    scanned_blocks += 1
                    context_header = " ".join(recent_lines[-2:])
                    block_is_antipattern = bool(
                        re.search(r"classification:\s*anti-pattern", context_header, re.IGNORECASE)
                    )
                else:
                    in_fence = False
                recent_lines.append(stripped)
                continue

            if not in_fence:
                recent_lines.append(stripped)
                continue

            if block_is_antipattern or antipattern_comment_re.search(stripped):
                continue

            if banned_wait_re.search(stripped):
                violations.append(
                    f"[{rel_doc}:{line_no}] Canonical skill code block contains prohibited static sleep 'waitForTimeout()'"
                )
            if banned_netidle_re.search(stripped):
                violations.append(
                    f"[{rel_doc}:{line_no}] Canonical skill code block contains flaky unconditional 'waitForLoadState(networkidle)'"
                )

    return DocCodeFenceAuditDTO(scanned_blocks=scanned_blocks, violations=violations)


def _discover_entry_doc_paths(repo_root: str) -> List[str]:
    """Discovers root, .github/, and docs/ Markdown files when explicit paths are omitted."""
    candidates: List[str] = []
    search_dirs = [
        repo_root,
        os.path.join(repo_root, ".github"),
        os.path.join(repo_root, "docs"),
    ]
    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for entry in sorted(os.listdir(directory)):
            if not entry.endswith(".md") or entry in _IGNORED_LINK_AUDIT_DOCS:
                continue
            full = os.path.join(directory, entry)
            if os.path.isfile(full):
                candidates.append(os.path.relpath(full, repo_root).replace("\\", "/"))
    return candidates


def check_markdown_relative_links(repo_root: str, doc_paths: Optional[List[str]] = None) -> List[str]:
    """Detects broken relative Markdown links in root and docs/ entry files."""
    target_docs = doc_paths if doc_paths is not None else _discover_entry_doc_paths(repo_root)
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]*)\)')
    inline_code_pattern = re.compile(r'`[^`]*`')
    errors: List[str] = []

    for rel_doc in target_docs:
        norm_doc = rel_doc.replace("\\", "/")
        abs_doc = os.path.join(repo_root, rel_doc)
        if not os.path.isfile(abs_doc):
            continue

        with open(abs_doc, "r", encoding="utf-8", errors="ignore") as fp:
            lines = fp.readlines()

        in_fence = False
        doc_dir = os.path.dirname(abs_doc)
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            cleaned = inline_code_pattern.sub("", line)
            for match in link_pattern.finditer(cleaned):
                label = match.group(1).strip()
                raw_target = match.group(2).strip()
                if not raw_target:
                    continue
                target_token = raw_target.split()[0].strip("<>")
                if not target_token or target_token.lower().startswith(_EXTERNAL_OR_ANCHOR_PREFIXES):
                    continue
                target_file = target_token.split("#", 1)[0].split("?", 1)[0]
                if not target_file:
                    continue

                resolved = os.path.normpath(os.path.join(doc_dir, target_file))
                if not os.path.exists(resolved):
                    finding = BrokenMarkdownLinkDTO(
                        source_doc=norm_doc,
                        line_number=line_no,
                        link_label=label,
                        target_path=target_file,
                    )
                    errors.append(
                        f"[{finding.source_doc}:{finding.line_number}] Broken relative Markdown link "
                        f"'[{finding.link_label}]({finding.target_path})' -> target does not exist"
                    )

    return errors


def check_doc_metrics_consistency(repo_root: str) -> List[str]:
    """Verifies that documented counts (skills, tools, DoD gates) accurately match disk."""
    errors: List[str] = []
    skills_dir = os.path.join(repo_root, "skills")
    if not os.path.isdir(skills_dir):
        skills_dir = os.path.join(repo_root, ".agents", "skills")
    tools_dir = os.path.join(repo_root, "tools")

    has_skills = os.path.isdir(skills_dir)
    has_tools = os.path.isdir(tools_dir)
    if not has_skills and not has_tools:
        return errors

    skills_count = 0
    if has_skills:
        # v4.0+: skills are 2 levels deep (domain/skill-id/SKILL.md)
        skills_count = sum(
            1
            for domain_entry in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, domain_entry))
            for skill_entry in os.listdir(os.path.join(skills_dir, domain_entry))
            if os.path.isdir(os.path.join(skills_dir, domain_entry, skill_entry))
            and os.path.exists(os.path.join(skills_dir, domain_entry, skill_entry, "SKILL.md"))
        )

    tools_count = 0
    if has_tools:
        for walk_root, dir_names, file_names in os.walk(tools_dir):
            dir_names[:] = [d for d in dir_names if d != "__pycache__"]
            tools_count += sum(
                1 for fname in file_names if fname.endswith(".py") and fname != "__init__.py"
            )

    obsolete_patterns = [
        (re.compile(r'\b(42|50)\s+(kỹ năng|skills?)\b', re.IGNORECASE), f"Obsolete skill count detected (real count: {skills_count})"),
        (re.compile(r'\b(60|68)\s+(công cụ|tools?)\b', re.IGNORECASE), f"Obsolete tool count detected (real count: {tools_count})"),
        (re.compile(r'\b(9|10)\s+Cổng\s+Chất\s+Lượng\b', re.IGNORECASE), "Obsolete gate count detected: must refer to 11 Cổng Chất Lượng DoD (Gate 1–11)"),
        (re.compile(r'\b(9|10)\s+Quality\s+Gates\b', re.IGNORECASE), "Obsolete gate count detected: must refer to 11 Quality Gates DoD (Gate 1–11)"),
    ]

    docs_to_check = [
        os.path.join(repo_root, "README.md"),
        os.path.join(repo_root, "README.en.md"),
        os.path.join(repo_root, ".github", "CONTRIBUTING.md"),
        os.path.join(repo_root, "docs", "ARCHITECTURE.md"),
        os.path.join(repo_root, "docs", "ARCHITECTURE.en.md"),
        os.path.join(repo_root, "docs", "CONTRIBUTING.md"),
        os.path.join(repo_root, "docs", "CONTRIBUTING.en.md"),
    ]

    for doc_path in docs_to_check:
        if not os.path.exists(doc_path):
            continue
        rel_doc = os.path.relpath(doc_path, repo_root)
        with open(doc_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                for pattern, msg in obsolete_patterns:
                    if pattern.search(line):
                        errors.append(f"[{rel_doc}:{line_no}] {msg}: '{line.strip()}'")

    return errors

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Enterprise AI Documentation & Artifact Linter")
    parser.add_argument("target", nargs="?", default=None, help="Path to repository root to lint")
    parser.add_argument("--repo", default=None, help="Path to repository root to lint")
    args = parser.parse_args()

    target_path = args.repo or args.target
    if target_path:
        repo_root = os.path.abspath(target_path)
    else:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    print(f"[AI-DOCS-LINT] Running Documentation & Artifact Linter on: {os.path.basename(repo_root)}")
    errors, warnings = lint_docs(repo_root)

    if warnings:
        print(f"\n[WARN] {len(warnings)} Warnings:")
        for w in warnings:
            print(f"   - {w}")

    if errors:
        print(f"\n[FAIL] {len(errors)} Lint Errors Found (Documentation Drift / Hallucination):")
        for e in errors:
            print(f"   - {e}")
        print("\n[BLOCKED] Verification failed: Please align documentation with real disk entities.")
        return 1
    else:
        print("[PASS] All documented tools, PageClasses, Suites, and Method calls verified on disk.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
