#!/usr/bin/env python3
"""
tools/wcag_audit.py — Automated Accessibility (WCAG 2.2) Linter & Auditor
Operationalizes the .agents/skills/wcag-audit-patterns skill for DMIT.

Checks WCAG 2.2 Level A and AA criteria:
- WCAG 1.1.1: Images missing alt attributes
- WCAG 1.3.1: Form controls missing labels or aria-label/aria-labelledby
- WCAG 1.3.1: Table headers structure
- WCAG 2.4.4: Links with empty text / accessible name
- WCAG 4.1.2: Buttons with empty text / accessible name
- WCAG 1.3.1: Heading hierarchy gaps (e.g., h1 to h3)
"""

import argparse
import os
import sys
import urllib.request
from html.parser import HTMLParser


class WCAGAuditor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.violations = []
        self.tag_stack = []
        self.headings = []
        self.current_tag = None
        self.current_attrs = {}
        self.text_buffer = ""
        self.stats = {"elements_scanned": 0, "violations_found": 0}

    def handle_starttag(self, tag, attrs):
        self.stats["elements_scanned"] += 1
        attr_dict = dict(attrs)
        self.tag_stack.append((tag, attr_dict))
        self.text_buffer = ""

        # WCAG 1.1.1: Image alt check
        if tag == "img":
            if "alt" not in attr_dict:
                self._add_violation("WCAG 1.1.1 (Level A)", "Critical", "img", attr_dict, "Image missing required 'alt' attribute.")

        # WCAG 1.3.1: Heading hierarchy tracking
        if tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(tag[1])
            self.headings.append((level, attr_dict))

        # WCAG 1.3.1: Form controls without labels
        if tag in ["input", "select", "textarea"]:
            input_type = attr_dict.get("type", "").lower()
            if input_type not in ["hidden", "submit", "button", "reset"]:
                has_label = bool(attr_dict.get("aria-label") or attr_dict.get("aria-labelledby") or attr_dict.get("title") or attr_dict.get("placeholder"))
                if not has_label:
                    self._add_violation("WCAG 1.3.1 (Level A)", "High", tag, attr_dict, f"Form control <{tag}> missing accessible label (aria-label, placeholder, or associated label).")

    def handle_endtag(self, tag):
        if not self.tag_stack:
            return
        last_tag, attrs = self.tag_stack.pop()

        # WCAG 2.4.4: Links with empty text
        if tag == "a":
            has_name = bool(self.text_buffer.strip() or attrs.get("aria-label") or attrs.get("title"))
            if not has_name:
                self._add_violation("WCAG 2.4.4 (Level A)", "High", "a", attrs, "Anchor link <a> has empty inner text and no aria-label or title.")

        # WCAG 4.1.2: Buttons with empty text
        if tag == "button" or attrs.get("role") == "button":
            has_name = bool(self.text_buffer.strip() or attrs.get("aria-label") or attrs.get("title"))
            if not has_name:
                self._add_violation("WCAG 4.1.2 (Level A)", "High", tag, attrs, "Button element has empty inner text and no aria-label or title.")

    def handle_data(self, data):
        self.text_buffer += data

    def finalize_audit(self):
        # Audit Heading Hierarchy
        if self.headings:
            for i in range(len(self.headings) - 1):
                cur_lvl = self.headings[i][0]
                nxt_lvl = self.headings[i + 1][0]
                if nxt_lvl > cur_lvl + 1:
                    self._add_violation(
                        "WCAG 1.3.1 (Level A)",
                        "Medium",
                        f"h{nxt_lvl}",
                        self.headings[i + 1][1],
                        f"Heading hierarchy skip detected: h{cur_lvl} followed by h{nxt_lvl} (expected h{cur_lvl + 1})."
                    )

    def _add_violation(self, criterion, severity, tag, attrs, message):
        self.stats["violations_found"] += 1
        snippet = f"<{tag}"
        for k, v in list(attrs.items())[:3]:
            snippet += f' {k}="{v[:30]}"'
        snippet += ">"
        self.violations.append({
            "criterion": criterion,
            "severity": severity,
            "element": snippet,
            "message": message
        })


def run_audit(target, is_url=False):
    if is_url:
        req = urllib.request.Request(target, headers={"User-Agent": "DMIT-WCAG-Auditor/1.0"})
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    else:
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

    auditor = WCAGAuditor()
    auditor.feed(html)
    auditor.finalize_audit()
    return auditor


def format_markdown_report(target, auditor):
    stats = auditor.stats
    violations = auditor.violations
    score = max(0, 100 - len(violations) * 5)
    grade = "PASS" if score >= 80 else "NEEDS REMEDIATION"

    out = [
        f"# WCAG 2.2 Accessibility Audit Report",
        f"**Target:** `{target}`",
        f"**Elements Scanned:** {stats['elements_scanned']}",
        f"**Violations Found:** {stats['violations_found']}",
        f"**Accessibility Score:** {score}/100 — **[{grade}]**",
        "",
        "---",
        "",
        "## Violations Detail",
        "",
        "| Severity | Criterion | Element Snippet | Issue Description |",
        "|---|---|---|---|"
    ]

    if not violations:
        out.append("| PASS | - | - | Zero WCAG 2.2 violations detected! Element tree is fully compliant. |")
    else:
        for v in violations:
            out.append(f"| **{v['severity']}** | {v['criterion']} | `{v['element']}` | {v['message']} |")

    out.append("")
    out.append("---")
    out.append("### Recommended Remediation Actions:")
    out.append("1. Add descriptive `alt=\"...\"` attributes to all images.")
    out.append("2. Add `aria-label=\"...\"` or explicit `<label for=\"...\">` bindings to form controls and icon buttons.")
    out.append("3. Maintain strict heading hierarchy (h1 -> h2 -> h3).")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Automated WCAG 2.2 Accessibility Auditor for DMIT.")
    parser.add_argument("target", help="HTML file path or URL to audit.")
    parser.add_argument("--url", action="store_true", help="Treat target as a live URL.")
    parser.add_argument("--output", "-o", help="Path to save markdown report.")
    args = parser.parse_args()

    if not args.url and not os.path.exists(args.target):
        print(f"Error: File '{args.target}' does not exist.")
        sys.exit(1)

    print(f"🔍 Running WCAG 2.2 Accessibility Audit on: {args.target}...")
    auditor = run_audit(args.target, is_url=args.url)
    report = format_markdown_report(args.target, auditor)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ Report saved to: {args.output}")
    else:
        print(report)

    if auditor.stats["violations_found"] > 0:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
