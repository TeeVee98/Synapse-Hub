#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/diagram_architect.py — Standalone Self-Contained SVG & HTML Diagram Builder
Inspired by Cathryn Lavery's diagram-design standard.
Generates fully self-contained SVG and HTML architectural diagrams
with zero Mermaid dependencies, guaranteed text contrast, and mathematical containment.
100% UTF-8 No BOM.
"""

import sys
import os
import argparse
from typing import Dict, Any

# Enforce UTF-8 stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def generate_fsm_diagram() -> str:
    """Generates the 5-Stage FSM flow diagram of Synapse Hub."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 240" width="100%" height="240" style="background:#0f172a; border-radius:12px; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <defs>
    <linearGradient id="cyan-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#06b6d4"/>
      <stop offset="100%" stop-color="#3b82f6"/>
    </linearGradient>
    <linearGradient id="purple-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6"/>
      <stop offset="100%" stop-color="#ec4899"/>
    </linearGradient>
    <linearGradient id="emerald-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#64748b"/>
    </marker>
  </defs>

  <!-- Connectors -->
  <line x1="180" y1="120" x2="225" y2="120" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="380" y1="120" x2="425" y2="120" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="580" y1="120" x2="625" y2="120" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="780" y1="120" x2="825" y2="120" stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- Stage 1 -->
  <g transform="translate(30, 60)">
    <rect width="150" height="120" rx="10" fill="#1e293b" stroke="#06b6d4" stroke-width="2"/>
    <rect width="150" height="28" rx="10" fill="#06b6d4"/>
    <text x="75" y="19" text-anchor="middle" fill="#0f172a" font-size="12" font-weight="bold">STAGE 1: DISCOVERY</text>
    <text x="75" y="60" text-anchor="middle" fill="#f8fafc" font-size="13" font-weight="600">test-designer</text>
    <text x="75" y="80" text-anchor="middle" fill="#94a3b8" font-size="11">RBT Risk Matrices</text>
    <text x="75" y="98" text-anchor="middle" fill="#38bdf8" font-size="11">Spec SDD / Gherkin</text>
  </g>

  <!-- Stage 2 -->
  <g transform="translate(230, 60)">
    <rect width="150" height="120" rx="10" fill="#1e293b" stroke="#3b82f6" stroke-width="2"/>
    <rect width="150" height="28" rx="10" fill="#3b82f6"/>
    <text x="75" y="19" text-anchor="middle" fill="#ffffff" font-size="12" font-weight="bold">STAGE 2: SYNTHESIS</text>
    <text x="75" y="60" text-anchor="middle" fill="#f8fafc" font-size="13" font-weight="600">pom-crafter</text>
    <text x="75" y="80" text-anchor="middle" fill="#94a3b8" font-size="11">Clean POM Classes</text>
    <text x="75" y="98" text-anchor="middle" fill="#60a5fa" font-size="11">Zero Script Locators</text>
  </g>

  <!-- Stage 3 -->
  <g transform="translate(430, 60)">
    <rect width="150" height="120" rx="10" fill="#1e293b" stroke="#8b5cf6" stroke-width="2"/>
    <rect width="150" height="28" rx="10" fill="#8b5cf6"/>
    <text x="75" y="19" text-anchor="middle" fill="#ffffff" font-size="12" font-weight="bold">STAGE 3: EXECUTION</text>
    <text x="75" y="60" text-anchor="middle" fill="#f8fafc" font-size="13" font-weight="600">test-runner</text>
    <text x="75" y="80" text-anchor="middle" fill="#94a3b8" font-size="11">100% Pure Headless</text>
    <text x="75" y="98" text-anchor="middle" fill="#c084fc" font-size="11">Parallel Worktrees</text>
  </g>

  <!-- Stage 4 -->
  <g transform="translate(630, 60)">
    <rect width="150" height="120" rx="10" fill="#1e293b" stroke="#f59e0b" stroke-width="2"/>
    <rect width="150" height="28" rx="10" fill="#f59e0b"/>
    <text x="75" y="19" text-anchor="middle" fill="#0f172a" font-size="12" font-weight="bold">STAGE 4: HEALING</text>
    <text x="75" y="60" text-anchor="middle" fill="#f8fafc" font-size="13" font-weight="600">failure-analyst</text>
    <text x="75" y="80" text-anchor="middle" fill="#94a3b8" font-size="11">AOM Diff Healing</text>
    <text x="75" y="98" text-anchor="middle" fill="#fbbf24" font-size="11">Pinpoint RCA</text>
  </g>

  <!-- Stage 5 -->
  <g transform="translate(830, 60)">
    <rect width="150" height="120" rx="10" fill="#1e293b" stroke="#10b981" stroke-width="2"/>
    <rect width="150" height="28" rx="10" fill="#10b981"/>
    <text x="75" y="19" text-anchor="middle" fill="#0f172a" font-size="12" font-weight="bold">STAGE 5: DoD ACCEPT</text>
    <text x="75" y="60" text-anchor="middle" fill="#f8fafc" font-size="13" font-weight="600">quality-gatekeeper</text>
    <text x="75" y="80" text-anchor="middle" fill="#94a3b8" font-size="11">10 Quality Gates</text>
    <text x="75" y="98" text-anchor="middle" fill="#34d399" font-size="11">Mutation >= 80%</text>
  </g>

  <!-- Title bar -->
  <text x="500" y="32" text-anchor="middle" fill="#e2e8f0" font-size="15" font-weight="700" letter-spacing="1">SYNAPSE HUB — 5-STAGE AUTONOMOUS FSM ENGINE</text>
</svg>"""
    return svg

def generate_clean_pom_diagram() -> str:
    """Generates the Clean POM Flat Architecture diagram."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 280" width="100%" height="280" style="background:#0b0f19; border-radius:12px; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <defs>
    <marker id="pom-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#06b6d4"/>
    </marker>
  </defs>

  <text x="450" y="35" text-anchor="middle" fill="#ffffff" font-size="16" font-weight="bold">CLEAN POM / FLAT ARCHITECTURE INVARIANT</text>

  <!-- Box 1: Test Scripts -->
  <g transform="translate(40, 70)">
    <rect width="240" height="160" rx="8" fill="#131b2e" stroke="#ef4444" stroke-width="2"/>
    <text x="120" y="35" text-anchor="middle" fill="#f87171" font-size="14" font-weight="bold">Test Scripts (tests/)</text>
    <line x1="20" y1="50" x2="220" y2="50" stroke="#334155"/>
    <text x="25" y="75" fill="#f8fafc" font-size="12">✅ Business actions only</text>
    <text x="25" y="100" fill="#f8fafc" font-size="12">✅ loginPage.login(u, p)</text>
    <text x="25" y="125" fill="#ef4444" font-size="12">❌ ZERO Raw XPaths / CSS</text>
    <text x="25" y="145" fill="#ef4444" font-size="12">❌ ZERO findTestObject</text>
  </g>

  <!-- Arrow 1 -> 2 -->
  <line x1="280" y1="150" x2="335" y2="150" stroke="#06b6d4" stroke-width="2" marker-end="url(#pom-arrow)"/>

  <!-- Box 2: Page Classes -->
  <g transform="translate(340, 70)">
    <rect width="240" height="160" rx="8" fill="#131b2e" stroke="#06b6d4" stroke-width="2"/>
    <text x="120" y="35" text-anchor="middle" fill="#22d3ee" font-size="14" font-weight="bold">Page Classes (pages/)</text>
    <line x1="20" y1="50" x2="220" y2="50" stroke="#334155"/>
    <text x="25" y="75" fill="#f8fafc" font-size="12">✅ Encapsulated Locators</text>
    <text x="25" y="100" fill="#f8fafc" font-size="12">✅ extends BasePage</text>
    <text x="25" y="125" fill="#f8fafc" font-size="12">✅ Semantic action methods</text>
    <text x="25" y="145" fill="#f8fafc" font-size="12">✅ Smart Wait integration</text>
  </g>

  <!-- Arrow 2 -> 3 -->
  <line x1="580" y1="150" x2="635" y2="150" stroke="#06b6d4" stroke-width="2" marker-end="url(#pom-arrow)"/>

  <!-- Box 3: BasePage / Framework -->
  <g transform="translate(640, 70)">
    <rect width="220" height="160" rx="8" fill="#131b2e" stroke="#10b981" stroke-width="2"/>
    <text x="110" y="35" text-anchor="middle" fill="#34d399" font-size="14" font-weight="bold">BasePage & Helpers</text>
    <line x1="20" y1="50" x2="200" y2="50" stroke="#334155"/>
    <text x="25" y="75" fill="#f8fafc" font-size="12">✅ uniqueCode("AUTO_")</text>
    <text x="25" y="100" fill="#f8fafc" font-size="12">✅ Dynamic Smart Waits</text>
    <text x="25" y="125" fill="#f8fafc" font-size="12">✅ Spinner detachment</text>
    <text x="25" y="145" fill="#f8fafc" font-size="12">✅ 100% UTF-8 No BOM</text>
  </g>
</svg>"""
    return svg

def build_html_wrapper(svg_content: str, title: str = "Synapse Hub Architecture Diagram") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      padding: 32px;
      background: #020617;
      color: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .diagram-container {{
      max-width: 1040px;
      width: 100%;
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }}
  </style>
</head>
<body>
  <div class="diagram-container">
    {svg_content}
  </div>
</body>
</html>"""

def main():
    parser = argparse.ArgumentParser(description="Generate self-contained standalone architectural diagrams.")
    parser.add_argument("--type", choices=["fsm", "clean-pom"], default="fsm", help="Diagram type to generate.")
    parser.add_argument("--output", "-o", help="Target output file path (.svg or .html).")
    args = parser.parse_args()

    if args.type == "fsm":
        svg = generate_fsm_diagram()
        title = "Synapse Hub — 5-Stage Autonomous FSM Engine"
    else:
        svg = generate_clean_pom_diagram()
        title = "Synapse Hub — Clean POM Architecture"

    if args.output:
        if args.output.endswith(".html"):
            content = build_html_wrapper(svg, title)
        else:
            content = svg
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[DIAGRAM ARCHITECT] Successfully exported {args.type} diagram to {args.output}")
    else:
        print(svg)

if __name__ == "__main__":
    main()
