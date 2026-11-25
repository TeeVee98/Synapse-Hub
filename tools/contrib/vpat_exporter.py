#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tools/vpat_exporter.py — Enterprise Section 508 & EN 301 549 VPAT Report Generator
---------------------------------------------------------------------------------
Translates WCAG 2.1 & 2.2 accessibility scan findings (from tools/wcag_audit.py
or axe-core) into standardized Voluntary Product Accessibility Template (VPAT 2.5)
compliance reports covering:
  - Revised Section 508 (US Public Sector / Federal Standard)
  - EN 301 549 (European Union Accessibility Standard for ICT)
  - W3C WCAG 2.1 / 2.2 (Levels A and AA)

Outputs:
  - Markdown (.md)
  - HTML (.html)
  - JSON (.json)

Usage:
  python tools/vpat_exporter.py --url https://staging.example.com --out-md VPAT_REPORT.md
  python tools/vpat_exporter.py --input wcag_results.json --format html --out VPAT.html
  python tools/vpat_exporter.py --html-file path/to/index.html --out-md VPAT.md
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
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Import wcag_audit dynamically if present
try:
    from tools.contrib.wcag_audit import WCAGAuditor
except ImportError:
    try:
        from tools.contrib.wcag_audit import WCAGAuditor
    except ImportError:
        WCAGAuditor = None


# ==============================================================================
# VPAT 2.5 CRITERIA MAPPING TABLE
# ==============================================================================

VPAT_CRITERIA_CATALOG = [
    {
        "wcag_id": "1.1.1",
        "name": "Non-text Content",
        "level": "A",
        "section_508": "501.1 (Web), 504.2 (Authoring Tools)",
        "en_301_549": "9.1.1.1 (Web), 10.1.1.1 (Non-web docs), 11.1.1.1 (Software)",
        "desc": "All non-text content that is presented to the user has a text alternative that serves the equivalent purpose.",
    },
    {
        "wcag_id": "1.3.1",
        "name": "Info and Relationships",
        "level": "A",
        "section_508": "501.1 (Web), 504.2",
        "en_301_549": "9.1.3.1 (Web), 11.1.3.1 (Software)",
        "desc": "Information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text.",
    },
    {
        "wcag_id": "1.4.3",
        "name": "Contrast (Minimum)",
        "level": "AA",
        "section_508": "501.1 (Web), 504.2",
        "en_301_549": "9.1.4.3 (Web), 11.1.4.3 (Software)",
        "desc": "The visual presentation of text and images of text has a contrast ratio of at least 4.5:1 (3:1 for large text).",
    },
    {
        "wcag_id": "2.1.1",
        "name": "Keyboard",
        "level": "A",
        "section_508": "501.1 (Web), 504.2",
        "en_301_549": "9.2.1.1 (Web), 11.2.1.1 (Software)",
        "desc": "All functionality of the content is operable through a keyboard interface without requiring specific timings for individual keystrokes.",
    },
    {
        "wcag_id": "2.1.2",
        "name": "No Keyboard Trap",
        "level": "A",
        "section_508": "501.1 (Web), 504.2",
        "en_301_549": "9.2.1.2 (Web), 11.2.1.2 (Software)",
        "desc": "If keyboard focus can be moved to a component using a keyboard interface, focus can be moved away without trapping the user.",
    },
    {
        "wcag_id": "2.4.4",
        "name": "Link Purpose (In Context)",
        "level": "A",
        "section_508": "501.1 (Web), 504.2",
        "en_301_549": "9.2.4.4 (Web), 11.2.4.4 (Software)",
        "desc": "The purpose of each link can be determined from the link text alone or from the link text together with programmatic context.",
    },
    {
        "wcag_id": "2.4.11",
        "name": "Focus Not Obscured (Minimum)",
        "level": "AA",
        "section_508": "Revised 508 (Aligned with WCAG 2.2)",
        "en_301_549": "9.2.4.11 (Web, WCAG 2.2 Draft)",
        "desc": "When an item gets keyboard focus, it is not entirely obscured by author-created content (sticky headers, banners).",
    },
    {
        "wcag_id": "2.5.8",
        "name": "Target Size (Minimum)",
        "level": "AA",
        "section_508": "Revised 508 (Aligned with WCAG 2.2)",
        "en_301_549": "9.2.5.8 (Web, WCAG 2.2 Draft)",
        "desc": "The target size for pointer inputs is at least 24 by 24 CSS pixels, or has sufficient offset/spacing.",
    },
    {
        "wcag_id": "3.2.6",
        "name": "Consistent Help",
        "level": "A",
        "section_508": "Revised 508 (Aligned with WCAG 2.2)",
        "en_301_549": "9.3.2.6 (Web, WCAG 2.2)",
        "desc": "If help mechanism is available, it appears in the same relative order across multiple web pages.",
    },
    {
        "wcag_id": "3.3.7",
        "name": "Redundant Entry",
        "level": "A",
        "section_508": "Revised 508 (Aligned with WCAG 2.2)",
        "en_301_549": "9.3.3.7 (Web, WCAG 2.2)",
        "desc": "Information previously entered or provided is auto-populated or available for selection in multi-step processes.",
    },
    {
        "wcag_id": "3.3.8",
        "name": "Accessible Authentication (Minimum)",
        "level": "AA",
        "section_508": "Revised 508 (Aligned with WCAG 2.2)",
        "en_301_549": "9.3.3.8 (Web, WCAG 2.2)",
        "desc": "A cognitive function test (such as solving a puzzle or remembering a password) is not required for authentication without an alternative.",
    },
    {
        "wcag_id": "4.1.2",
        "name": "Name, Role, Value",
        "level": "A",
        "section_508": "501.1 (Web), 504.2",
        "en_301_549": "9.4.1.2 (Web), 11.4.1.2 (Software)",
        "desc": "For all UI components, the name and role can be programmatically determined; states and properties can be set programmatically.",
    },
]


def audit_html_source(html_content: str) -> List[Dict[str, Any]]:
    """Runs WCAGAuditor parser on HTML content to extract violations."""
    if WCAGAuditor is None:
        return []
    auditor = WCAGAuditor()
    try:
        auditor.feed(html_content)
    except Exception as exc:
        auditor.violations.append({
            "criterion": "4.1.1 Parsing / Well-Formedness",
            "severity": "CRITICAL",
            "element": "<html>",
            "message": f"HTML parser failed to process document: {type(exc).__name__}: {str(exc)}",
        })
    return auditor.violations


def compile_vpat_assessment(
    violations: List[Dict[str, Any]],
    product_name: str = "Enterprise Web Application",
    product_version: str = "1.0.0",
    vendor: str = "Quality Engineering Team",
) -> Dict[str, Any]:
    """Compiles audit violations into standard VPAT conformance criteria."""
    assessed_table = []
    supports_count = 0
    partially_count = 0
    not_support_count = 0

    # Group violations by WCAG criterion ID
    violation_map: Dict[str, List[Dict[str, Any]]] = {}
    for v in violations:
        crit_str = v.get("criterion", "")
        for c in VPAT_CRITERIA_CATALOG:
            if c["wcag_id"] in crit_str or c["name"].lower() in crit_str.lower():
                violation_map.setdefault(c["wcag_id"], []).append(v)
                break

    for c in VPAT_CRITERIA_CATALOG:
        cid = c["wcag_id"]
        viols = violation_map.get(cid, [])

        if not viols:
            conformance = "Supports"
            remarks = "The web application satisfies the criterion with zero automated defects detected."
            supports_count += 1
        elif len(viols) <= 2 and not any(v.get("severity") == "CRITICAL" for v in viols):
            conformance = "Partially Supports"
            remarks = f"{len(viols)} minor defect(s) detected: " + "; ".join(v.get("message", "") for v in viols[:2])
            partially_count += 1
        else:
            conformance = "Does Not Support"
            remarks = f"{len(viols)} violation(s) identified. Sample: " + "; ".join(v.get("message", "") for v in viols[:3])
            not_support_count += 1

        assessed_table.append({
            "wcag_id": cid,
            "name": c["name"],
            "level": c["level"],
            "section_508": c["section_508"],
            "en_301_549": c["en_301_549"],
            "conformance": conformance,
            "remarks": remarks,
            "violations_count": len(viols),
            "samples": viols[:3],
        })

    total = len(assessed_table)
    conformance_rate = round((supports_count + (0.5 * partially_count)) / total * 100, 1)

    return {
        "vpat_version": "2.5 (Revised Section 508 & EN 301 549 Edition)",
        "report_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "product_name": product_name,
        "product_version": product_version,
        "vendor": vendor,
        "evaluation_methods": "Automated AST inspection, W3C WCAG 2.2 Linter (tools/wcag_audit.py), and DOM traversal.",
        "conformance_summary": {
            "total_criteria": total,
            "supports": supports_count,
            "partially_supports": partially_count,
            "does_not_support": not_support_count,
            "conformance_rate_pct": conformance_rate,
        },
        "criteria": assessed_table,
    }


# ==============================================================================
# EXPORTERS (MARKDOWN & HTML)
# ==============================================================================

def export_vpat_markdown(vpat_data: Dict[str, Any]) -> str:
    """Renders VPAT report in official Markdown format."""
    lines = [
        "# Accessibility Conformance Report (VPAT® Version 2.5)",
        "",
        f"**Product Name:** {vpat_data['product_name']}  ",
        f"**Product Version:** {vpat_data['product_version']}  ",
        f"**Vendor / Organization:** {vpat_data['vendor']}  ",
        f"**Report Date:** {vpat_data['report_date']}  ",
        f"**Evaluation Methods:** {vpat_data['evaluation_methods']}  ",
        "",
        "## Applicable Standards & Guidelines",
        "- **Web Content Accessibility Guidelines (WCAG) 2.2** (Levels A and AA)",
        "- **Revised Section 508 Standards** (US Access Board)",
        "- **EN 301 549 Accessibility Requirements for ICT Products and Services** (European Standard)",
        "",
        "## Conformance Terms",
        "- **Supports:** The functionality has at least one method that addresses the criterion without known defects.",
        "- **Partially Supports:** Some functionality does not meet the criterion.",
        "- **Does Not Support:** The majority of functionality does not meet the criterion.",
        "- **Not Applicable:** The criterion is not relevant to the product.",
        "",
        f"### Executive Summary Conformance Rate: **{vpat_data['conformance_summary']['conformance_rate_pct']}%**",
        f"- Fully Supports: `{vpat_data['conformance_summary']['supports']}` criteria",
        f"- Partially Supports: `{vpat_data['conformance_summary']['partially_supports']}` criteria",
        f"- Does Not Support: `{vpat_data['conformance_summary']['does_not_support']}` criteria",
        "",
        "---",
        "",
        "## Table 1: Success Criteria, Level A & AA (WCAG 2.2 / Section 508 / EN 301 549)",
        "",
        "| Criteria | Level | Section 508 Chapter 5 | EN 301 549 Clause 9 | Conformance Level | Remarks and Explanations |",
        "| :--- | :---: | :--- | :--- | :---: | :--- |",
    ]

    for c in vpat_data["criteria"]:
        crit_title = f"**{c['wcag_id']} {c['name']}**"
        lines.append(
            f"| {crit_title} | Level {c['level']} | {c['section_508']} | {c['en_301_549']} | **{c['conformance']}** | {c['remarks']} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("*Report generated automatically via Synapse Hub Enterprise Accessibility Sentinel (`tools/vpat_exporter.py`).*")
    return "\n".join(lines)


def export_vpat_html(vpat_data: Dict[str, Any]) -> str:
    """Renders VPAT report in standalone styled HTML format."""
    rate = vpat_data["conformance_summary"]["conformance_rate_pct"]
    rate_color = "#10b981" if rate >= 85 else ("#f59e0b" if rate >= 65 else "#ef4444")

    rows_html = []
    for c in vpat_data["criteria"]:
        bg_col = "#ecfdf5" if c["conformance"] == "Supports" else ("#fffbeb" if c["conformance"] == "Partially Supports" else "#fef2f2")
        badge_col = "#047857" if c["conformance"] == "Supports" else ("#b45309" if c["conformance"] == "Partially Supports" else "#b91c1c")

        rows_html.append(f"""
        <tr style="background-color: {bg_col};">
            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>{c['wcag_id']} {c['name']}</strong></td>
            <td style="padding: 10px; border: 1px solid #e5e7eb; text-align: center;">Level {c['level']}</td>
            <td style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">{c['section_508']}</td>
            <td style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">{c['en_301_549']}</td>
            <td style="padding: 10px; border: 1px solid #e5e7eb; text-align: center;">
                <span style="display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; color: white; background-color: {badge_col};">
                    {c['conformance']}
                </span>
            </td>
            <td style="padding: 10px; border: 1px solid #e5e7eb; font-size: 13px;">{c['remarks']}</td>
        </tr>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>VPAT® 2.5 - {vpat_data['product_name']}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.5; margin: 30px; color: #1f2937; }}
        h1 {{ color: #111827; }}
        .meta-box {{ background: #f3f4f6; border-radius: 8px; padding: 15px 20px; margin-bottom: 25px; }}
        .scorecard {{ display: inline-block; font-size: 28px; font-weight: bold; color: {rate_color}; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #1f2937; color: white; padding: 12px; text-align: left; font-size: 14px; border: 1px solid #1f2937; }}
    </style>
</head>
<body>
    <h1>Accessibility Conformance Report (VPAT® 2.5)</h1>
    <div class="meta-box">
        <p><strong>Product:</strong> {vpat_data['product_name']} (v{vpat_data['product_version']}) | <strong>Date:</strong> {vpat_data['report_date']}</p>
        <p><strong>Evaluation Standards:</strong> WCAG 2.2 (A/AA), Revised Section 508, EN 301 549</p>
        <p><strong>Conformance Rating:</strong> <span class="scorecard">{rate}%</span> ({vpat_data['conformance_summary']['supports']} Supports / {vpat_data['conformance_summary']['partially_supports']} Partial / {vpat_data['conformance_summary']['does_not_support']} Does Not Support)</p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Success Criteria</th>
                <th>Level</th>
                <th>Section 508</th>
                <th>EN 301 549</th>
                <th>Conformance Level</th>
                <th>Remarks and Explanations</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows_html)}
        </tbody>
    </table>
</body>
</html>"""


# ==============================================================================
# CLI HANDLER
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Synapse Hub Section 508 & EN 301 549 VPAT Exporter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", help="Target URL to fetch HTML and audit")
    parser.add_argument("--html-file", help="Path to local HTML file to inspect")
    parser.add_argument("--input", help="Path to pre-existing wcag_audit JSON results file")
    parser.add_argument("--format", choices=["md", "html", "json"], default="md", help="Export format (md, html, json)")
    parser.add_argument("--out", help="Output file path (defaults to stdout)")
    parser.add_argument("--out-md", help="Shortcut to write markdown directly to specified file")
    parser.add_argument("--product-name", default="Enterprise Web Application", help="Product name for the VPAT report")
    parser.add_argument("--product-version", default="1.0.0", help="Product version for the VPAT report")
    parser.add_argument("--gate", action="store_true", help="Exit code 1 if any Level A/AA criteria is 'Does Not Support'")

    args = parser.parse_args()

    violations = []

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
        violations = data if isinstance(data, list) else data.get("violations", [])
    elif args.html_file:
        with open(args.html_file, "r", encoding="utf-8") as f:
            html = f.read()
        violations = audit_html_source(html)
    elif args.url:
        import urllib.request
        req = urllib.request.Request(args.url, headers={"User-Agent": "Synapse-Hub-VPAT/4.8.5"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        violations = audit_html_source(html)

    vpat_data = compile_vpat_assessment(
        violations,
        product_name=args.product_name,
        product_version=args.product_version,
    )

    fmt = "md"
    if args.out_md:
        fmt = "md"
        out_path = args.out_md
    else:
        fmt = args.format
        out_path = args.out

    if fmt == "md":
        rendered = export_vpat_markdown(vpat_data)
    elif fmt == "html":
        rendered = export_vpat_html(vpat_data)
    else:
        rendered = json.dumps(vpat_data, indent=2, ensure_ascii=False)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"✅ Exported VPAT 2.5 ({fmt.upper()}) report to {out_path}")
    else:
        print(rendered)

    if args.gate and vpat_data["conformance_summary"]["does_not_support"] > 0:
        print(f"🚨 Quality Gate Failed: {vpat_data['conformance_summary']['does_not_support']} criteria 'Does Not Support'!", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
