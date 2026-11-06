#!/usr/bin/env python3
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
import glob
import re

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
        actual_tools.update(os.listdir(tools_dir))
    # Always include Hub tools directory in decoupled architecture
    hub_tools = os.path.abspath(os.path.dirname(__file__))
    if os.path.isdir(hub_tools):
        actual_tools.update(os.listdir(hub_tools))

    return actual_pages, actual_suites, actual_cases, actual_tc_ids, actual_tools, class_methods

def find_doc_files(repo_root):
    md_patterns = [
        os.path.join(repo_root, ".agents", "**", "*.md"),
        os.path.join(repo_root, "*.md"),
    ]
    doc_files = []
    for pattern in md_patterns:
        for f in glob.glob(pattern, recursive=True):
            rel = os.path.relpath(f, repo_root)
            if any(ignored in rel for ignored in ("node_modules", ".git", "allure-results", "teamwork", "external_repos", "AUDIT_REPORT", "FINAL_REPORT")):
                continue
            doc_files.append(rel)
    return sorted(doc_files)

def lint_docs(repo_root):
    actual_pages, actual_suites, actual_cases, actual_tc_ids, actual_tools, class_methods = get_actual_entities(repo_root)
    doc_files = find_doc_files(repo_root)

    page_pattern = re.compile(r'\b([A-Z][A-Za-z0-9]+Page)\b')
    suite_pattern = re.compile(r'(?:Test Suites/|-Suite\s+["\'](?:Test Suites/)?|--testSuitePath=["\'](?:Test Suites/)?)([A-Za-z0-9_]+)')
    tool_pattern = re.compile(r'\btools/([a-zA-Z0-9_\-\.]+\.(?:py|sh|ps1|bat|js))\b')
    tc_id_pattern = re.compile(r'\b(TC-\d+)\b')
    tc_path_pattern = re.compile(r'Test Cases/([A-Za-z0-9_ \-\.\(\)]+?)(?:\.tc)?["\s\)]')
    method_pattern = re.compile(r'\b(EnterpriseHelper|BasePage|[A-Z][a-zA-Z0-9]+Page)\.([a-z][a-zA-Z0-9_]+)\s*\(')

    errors = []
    warnings = []

    # Ignored tool references (examples, output targets, artifacts)
    ignored_tool_refs = {"api_matrix.json", "output.json", "report.json", "output.txt", "summary.json"}

    # 6. Hub Mode Metadata & Count Synchronization (Anti-Drift Guard for Skills, Rules, Workflows)
    manifest_path = os.path.join(repo_root, "skills_manifest.json")
    skills_dir = os.path.join(repo_root, ".agents", "skills")
    rules_dir = os.path.join(repo_root, ".agents", "rules")
    workflows_dir = os.path.join(repo_root, ".agents", "workflows")

    if os.path.exists(manifest_path) and os.path.isdir(skills_dir):
        import json
        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest_data = json.load(mf)
            manifest_skill_ids = set(s.get("id") for s in manifest_data.get("skills", []))
            actual_skill_dirs = set(
                d for d in os.listdir(skills_dir)
                if os.path.isdir(os.path.join(skills_dir, d))
            )
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

        is_historical = "FINAL_REPORT.md" in doc or "POM_REFACTORING_PLAN.md" in doc

        for line_no, line in enumerate(lines, 1):
            # 1. Page Class Lint (Only strictly enforced if repository defines Page Classes in Keywords/pages)
            if actual_pages:
                for m in page_pattern.finditer(line):
                    pname = m.group(1)
                    if pname not in actual_pages and pname not in GENERIC_PAGES:
                        if is_historical:
                            continue
                        errors.append(f"[{doc}:{line_no}] Non-existent Page Class referenced: '{pname}' (Must be one of {sorted(actual_pages)})")

            # 2. Test Suite Lint (Only strictly enforced if repository defines Test Suites)
            if actual_suites:
                for m in suite_pattern.finditer(line):
                    sname = m.group(1)
                    if "xxx" in sname.lower() or "example" in sname.lower():
                        continue
                    if is_historical:
                        continue
                    if sname not in actual_suites:
                        errors.append(f"[{doc}:{line_no}] Non-existent Test Suite referenced: '{sname}'")

            # 3. Tool Script Lint (Enforced in both Hub and Target modes)
            for m in tool_pattern.finditer(line):
                tname = m.group(1)
                if tname in ignored_tool_refs:
                    continue
                if tname not in actual_tools:
                    errors.append(f"[{doc}:{line_no}] Non-existent tool script referenced: 'tools/{tname}'")

            # 4. Test Case Validation (Only strictly enforced if repository defines Test Cases)
            if actual_cases and not is_historical:
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

    return errors, warnings


def check_doc_metrics_consistency(repo_root):
    """Verifies that documented counts (skills, tools, DoD gates) accurately match disk."""
    errors = []
    skills_dir = os.path.join(repo_root, ".agents", "skills")
    tools_dir = os.path.join(repo_root, "tools")

    if not os.path.isdir(skills_dir) or not os.path.isdir(tools_dir):
        return errors

    skills_count = len([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d)) and os.path.exists(os.path.join(skills_dir, d, "SKILL.md"))])
    tools_count = len([f for f in os.listdir(tools_dir) if f.endswith(".py") and f != "__init__.py"])

    obsolete_patterns = [
        (re.compile(r'\b(42|50)\s+(kỹ năng|skills?)\b', re.IGNORECASE), f"Obsolete skill count detected (real count: {skills_count})"),
        (re.compile(r'\b(60|68)\s+(công cụ|tools?)\b', re.IGNORECASE), f"Obsolete tool count detected (real count: {tools_count})"),
        (re.compile(r'\b9\s+Cổng\s+Chất\s+Lượng\b', re.IGNORECASE), "Obsolete gate count detected: must refer to 10 Cổng Chất Lượng DoD (Gate 0–9)"),
    ]

    docs_to_check = [
        os.path.join(repo_root, "README.md"),
        os.path.join(repo_root, "README.en.md"),
        os.path.join(repo_root, "docs", "ARCHITECTURE.md"),
        os.path.join(repo_root, "docs", "CONTRIBUTING.md"),
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
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

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
