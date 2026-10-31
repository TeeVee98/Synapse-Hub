#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
tools/welcome_page.py — Interactive Visual Landing Page for Synapse Hub
-------------------------------------------------------------------------
Generates and automatically launches a modern, responsive, 100% self-contained
HTML5 product landing page that introduces Synapse Hub's capabilities across
Manual, Automation, API, and Performance testing.

Features:
  - 100% air-gapped & offline-ready (Zero external CDNs or remote dependencies).
  - Dark glassmorphism interface with responsive layout.
  - Interactive tabs covering the 4 Core Pillars of QA Intelligence.
  - Interactive CLI Cheatsheet with 1-click clipboard copy.
  - Comparison matrix vs existing industry tools (ESLint, Stryker, Allure, Healenium).
  - 6 Subagent Swarm Profiles & 9 Quality Gates DoD showcase.
  - Automatic browser launching on setup, pull, or CLI dispatch.
"""

import os
import sys
import json
import argparse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HUB_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))


def get_hub_metadata() -> Dict[str, Any]:
    """Retrieves version and catalog count from skills_manifest.json."""
    manifest_path = os.path.join(HUB_ROOT, "skills_manifest.json")
    meta = {
        "version": "2.3.0",
        "totalSkills": 28,
        "author": "Thế Vị (@TeeVee998)",
        "repo": "https://github.com/TeeVee998/Synapse-Hub"
    }
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                meta["version"] = data.get("version", meta["version"])
                meta["totalSkills"] = data.get("totalSkills", meta["totalSkills"])
        except Exception:
            pass
    return meta


def generate_welcome_html(target_repo: Optional[str] = None, stack_info: Optional[Dict[str, str]] = None) -> str:
    """Renders the standalone interactive HTML5 landing page."""
    meta = get_hub_metadata()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    target_name = "Target Project"
    framework_name = "Polyglot QA Framework"
    if stack_info:
        target_name = stack_info.get("name", target_name)
        framework_name = stack_info.get("framework", framework_name)
    elif target_repo:
        target_name = os.path.basename(os.path.abspath(target_repo))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Synapse Hub — Complete QA Intelligence for AI Agents</title>
    <style>
        :root {{
            --bg-primary: #07090e;
            --bg-secondary: #0d121d;
            --bg-card: rgba(17, 24, 39, 0.75);
            --bg-card-hover: rgba(30, 41, 59, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(99, 102, 241, 0.35);
            --text-main: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-cyan: #06b6d4;
            --accent-indigo: #6366f1;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --accent-purple: #a855f7;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: var(--bg-primary);
            color: var(--text-main);
            font-family: var(--font-sans);
            line-height: 1.6;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 85% 25%, rgba(6, 182, 212, 0.10) 0%, transparent 45%),
                radial-gradient(circle at 50% 80%, rgba(16, 185, 129, 0.08) 0%, transparent 50%);
            background-attachment: fixed;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
        }}

        /* Navbar */
        nav {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(7, 9, 14, 0.85);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-color);
            padding: 16px 0;
        }}
        .nav-inner {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: var(--text-main);
        }}
        .brand-icon {{
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-indigo));
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 0 16px rgba(99, 102, 241, 0.4);
        }}
        .brand-name {{
            font-size: 18px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(to right, #fff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .version-tag {{
            font-size: 11px;
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            padding: 2px 8px;
            border-radius: 12px;
            border: 1px solid rgba(99, 102, 241, 0.3);
            font-weight: 700;
            font-family: var(--font-mono);
        }}
        .nav-links {{
            display: flex;
            align-items: center;
            gap: 20px;
            list-style: none;
        }}
        .nav-links a {{
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: color 0.2s;
        }}
        .nav-links a:hover {{ color: var(--accent-cyan); }}
        .nav-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        /* Buttons */
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 9px 18px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }}
        .btn-primary {{
            background: linear-gradient(135deg, var(--accent-indigo), #4f46e5);
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
        }}
        .btn-primary:hover {{
            background: linear-gradient(135deg, #4f46e5, #4338ca);
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(79, 70, 229, 0.6);
        }}
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border: 1px solid var(--border-color);
        }}
        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
        }}
        .btn-emerald {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-emerald);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}
        .btn-emerald:hover {{
            background: rgba(16, 185, 129, 0.25);
            border-color: var(--accent-emerald);
        }}

        /* Hero Section */
        .hero {{
            padding: 72px 0 48px;
            text-align: center;
        }}
        .hero-pill {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.25);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            color: #a5b4fc;
            margin-bottom: 24px;
        }}
        .hero h1 {{
            font-size: 48px;
            font-weight: 800;
            letter-spacing: -1.2px;
            line-height: 1.15;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #ffffff 20%, #cbd5e1 60%, var(--accent-cyan) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .hero p {{
            font-size: 18px;
            color: var(--text-secondary);
            max-width: 780px;
            margin: 0 auto 32px;
            line-height: 1.6;
        }}
        .hero-buttons {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            margin-bottom: 48px;
            flex-wrap: wrap;
        }}

        /* Stats Ribbon */
        .stats-ribbon {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 64px;
        }}
        .stat-item {{
            text-align: center;
            padding: 8px 16px;
            border-right: 1px solid var(--border-color);
        }}
        .stat-item:last-child {{ border-right: none; }}
        .stat-val {{
            font-size: 32px;
            font-weight: 800;
            font-family: var(--font-mono);
            letter-spacing: -1px;
            margin-bottom: 4px;
        }}
        .stat-label {{
            font-size: 13px;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}

        /* Section Headers */
        .section-header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .section-tag {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--accent-cyan);
            margin-bottom: 8px;
            display: block;
        }}
        .section-title {{
            font-size: 32px;
            font-weight: 800;
            letter-spacing: -0.8px;
            margin-bottom: 12px;
        }}
        .section-desc {{
            font-size: 15px;
            color: var(--text-secondary);
            max-width: 650px;
            margin: 0 auto;
        }}

        /* 4 Pillars Grid */
        .pillars-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
            margin-bottom: 80px;
        }}
        .pillar-card {{
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 32px;
            transition: all 0.25s ease;
            position: relative;
            overflow: hidden;
        }}
        .pillar-card:hover {{
            background: var(--bg-card-hover);
            border-color: var(--border-highlight);
            transform: translateY(-3px);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
        }}
        .pillar-icon-box {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .pillar-title {{
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .pillar-desc {{
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 20px;
            line-height: 1.6;
        }}
        .pillar-features {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .pillar-features li {{
            font-size: 13px;
            color: #cbd5e1;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }}
        .pillar-features li span.check {{
            color: var(--accent-emerald);
            font-weight: bold;
        }}

        /* Hero Highlights (3 Cards) */
        .highlights-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 80px;
        }}
        .highlight-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .highlight-badge {{
            display: inline-block;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            margin-bottom: 14px;
            align-self: flex-start;
        }}
        .highlight-title {{
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .highlight-desc {{
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 16px;
            line-height: 1.5;
        }}
        .code-snippet {{
            background: #05070a;
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 10px 12px;
            border-radius: 8px;
            font-family: var(--font-mono);
            font-size: 12px;
            color: #38bdf8;
            overflow-x: auto;
        }}

        /* Terminal Cheatsheet */
        .terminal-box {{
            background: #05070b;
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 80px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
        }}
        .terminal-header {{
            background: #0b0f17;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border-color);
        }}
        .terminal-dots {{
            display: flex;
            gap: 6px;
        }}
        .terminal-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}
        .dot-red {{ background: #ef4444; }}
        .dot-yellow {{ background: #f59e0b; }}
        .dot-green {{ background: #10b981; }}
        .terminal-title {{
            font-size: 12px;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }}
        .terminal-tabs {{
            display: flex;
            background: #090d14;
            border-bottom: 1px solid var(--border-color);
            overflow-x: auto;
        }}
        .terminal-tab {{
            padding: 10px 18px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            border-right: 1px solid var(--border-color);
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            white-space: nowrap;
        }}
        .terminal-tab.active {{
            color: var(--text-main);
            background: #05070b;
            border-bottom: 2px solid var(--accent-cyan);
        }}
        .terminal-body {{
            padding: 24px;
            min-height: 180px;
            font-family: var(--font-mono);
        }}
        .cmd-line {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            padding: 12px 16px;
            border-radius: 10px;
            margin-bottom: 12px;
        }}
        .cmd-text {{
            font-size: 14px;
            color: #a5f3fc;
        }}
        .cmd-text span.prompt {{
            color: var(--accent-indigo);
            user-select: none;
            margin-right: 8px;
        }}
        .copy-btn {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: var(--text-secondary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-family: var(--font-sans);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .copy-btn:hover {{
            background: rgba(255, 255, 255, 0.15);
            color: #fff;
        }}
        .cmd-desc {{
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 4px;
            font-family: var(--font-sans);
            padding-left: 4px;
        }}

        /* Comparison Table */
        .comparison-table-wrap {{
            overflow-x: auto;
            margin-bottom: 80px;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 8px;
        }}
        table.comparison-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 13px;
        }}
        table.comparison-table th, table.comparison-table td {{
            padding: 14px 18px;
            border-bottom: 1px solid var(--border-color);
        }}
        table.comparison-table th {{
            font-weight: 700;
            color: #cbd5e1;
            background: rgba(255, 255, 255, 0.02);
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        table.comparison-table tr:last-child td {{ border-bottom: none; }}
        table.comparison-table tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        .col-synapse {{
            background: rgba(99, 102, 241, 0.08);
            font-weight: 600;
        }}
        .pill-win {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-emerald);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 700;
            display: inline-block;
        }}

        /* 9 Quality Gates Grid */
        .gates-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 80px;
        }}
        .gate-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .gate-top {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .gate-badge {{
            font-size: 10px;
            font-family: var(--font-mono);
            font-weight: 700;
            background: rgba(6, 182, 212, 0.15);
            color: var(--accent-cyan);
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .gate-pass {{
            font-size: 11px;
            font-weight: 700;
            color: var(--accent-emerald);
        }}
        .gate-name {{
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .gate-desc {{
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.4;
        }}

        /* Swarm Agents Grid */
        .swarm-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 80px;
        }}
        .agent-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.2s;
        }}
        .agent-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.4);
        }}
        .agent-icon {{
            font-size: 24px;
            margin-bottom: 12px;
        }}
        .agent-role {{
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .agent-id {{
            font-size: 11px;
            font-family: var(--font-mono);
            color: var(--accent-indigo);
            margin-bottom: 8px;
            display: block;
        }}
        .agent-desc {{
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.5;
        }}

        /* Footer */
        footer {{
            border-top: 1px solid var(--border-color);
            padding: 48px 0 32px;
            background: #040609;
            margin-top: 40px;
        }}
        .footer-grid {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 24px;
            margin-bottom: 32px;
        }}
        .footer-brand p {{
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .footer-links {{
            display: flex;
            gap: 20px;
            list-style: none;
        }}
        .footer-links a {{
            color: var(--text-secondary);
            font-size: 13px;
            text-decoration: none;
            transition: color 0.2s;
        }}
        .footer-links a:hover {{ color: var(--accent-cyan); }}
        .footer-bottom {{
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 24px;
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
        }}
        .footer-bottom a {{
            color: #818cf8;
            text-decoration: none;
        }}
        .footer-bottom a:hover {{ text-decoration: underline; }}

        /* Toast notification */
        .toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: rgba(16, 185, 129, 0.95);
            color: #fff;
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 1000;
        }}
        .toast.show {{
            transform: translateY(0);
            opacity: 1;
        }}

        @media (max-width: 900px) {{
            .hero h1 {{ font-size: 36px; }}
            .pillars-grid, .highlights-grid, .gates-grid, .swarm-grid {{ grid-template-columns: 1fr; }}
            .stats-ribbon {{ grid-template-columns: repeat(2, 1fr); gap: 20px; }}
            .stat-item {{ border-right: none; }}
            .nav-links {{ display: none; }}
        }}
    </style>
</head>
<body>

    <!-- Sticky Navigation -->
    <nav>
        <div class="container nav-inner">
            <a href="#" class="brand">
                <div class="brand-icon">⚡</div>
                <div>
                    <span class="brand-name">SYNAPSE HUB</span>
                    <span class="version-tag">v{meta['version']}</span>
                </div>
            </a>
            <ul class="nav-links">
                <li><a href="#pillars">4 Testing Pillars</a></li>
                <li><a href="#hero-features">Hero Features</a></li>
                <li><a href="#quickstart">CLI Cheatsheet</a></li>
                <li><a href="#quality-gates">9 Quality Gates</a></li>
                <li><a href="#comparison">Benchmark vs Tools</a></li>
            </ul>
            <div class="nav-actions">
                <a href="PROJECT_DASHBOARD.html" class="btn btn-secondary" title="Open Standalone Health Dashboard">📊 Dashboard</a>
                <a href="{meta['repo']}" target="_blank" rel="noopener" class="btn btn-primary">⭐ GitHub</a>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <header class="hero">
        <div class="container">
            <div class="hero-pill">
                <span>🛡️ Enterprise AI Quality Intelligence Hub</span>
                <span>&bull;</span>
                <span>Active Target: {target_name} ({framework_name})</span>
            </div>
            <h1>The Complete QA Intelligence Hub<br>for AI Coding Agents</h1>
            <p>
                Empowering QA Engineers and Autonomous AI Agents across 
                <strong>Manual</strong>, <strong>Automation</strong>, <strong>API</strong>, and <strong>Performance</strong> testing. 
                Equipped with 100% offline-first AST sentinels, 6 swarm profiles, and 9 Quality Gates Definition-of-Done.
            </p>
            <div class="hero-buttons">
                <a href="#quickstart" class="btn btn-primary" style="padding: 12px 24px; font-size: 15px;">🚀 5-Second Quickstart</a>
                <a href="#pillars" class="btn btn-secondary" style="padding: 12px 24px; font-size: 15px;">🎯 Explore 4 Pillars</a>
                <a href="#quality-gates" class="btn btn-emerald" style="padding: 12px 24px; font-size: 15px;">🛡️ View 9 Quality Gates</a>
            </div>

            <!-- Stats Ribbon -->
            <div class="stats-ribbon">
                <div class="stat-item">
                    <div class="stat-val" style="color: var(--accent-cyan);">{meta['totalSkills']}+</div>
                    <div class="stat-label">Standardized AI Skills</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val" style="color: var(--accent-emerald);">9 / 9</div>
                    <div class="stat-label">Quality Gates DoD</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val" style="color: var(--accent-indigo);">6</div>
                    <div class="stat-label">Autonomous Swarm Roles</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val" style="color: var(--accent-amber);">100%</div>
                    <div class="stat-label">Air-Gapped & Offline Ready</div>
                </div>
            </div>
        </div>
    </header>

    <main class="container">

        <!-- 4 Core Pillars Section -->
        <section id="pillars" style="scroll-margin-top: 80px;">
            <div class="section-header">
                <span class="section-tag">Comprehensive Discipline</span>
                <h2 class="section-title">The 4 Pillars of QA Intelligence</h2>
                <p class="section-desc">Synapse Hub bridges manual exploratory testing with bleeding-edge AI automation, robust contract API testing, and backend endurance verification.</p>
            </div>

            <div class="pillars-grid">
                <!-- Pillar 1: Manual -->
                <div class="pillar-card">
                    <div class="pillar-icon-box" style="background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan);">🎯</div>
                    <div class="pillar-title">
                        <span>1. Manual Testing (AI-RBT)</span>
                        <span class="pill-win">Risk-Based</span>
                    </div>
                    <p class="pillar-desc">Transforms vague requirements into rigorous, boundary-tested manual test cases with zero hallucinations.</p>
                    <ul class="pillar-features">
                        <li><span class="check">✓</span> <strong>6-Stage Risk-Based Testing:</strong> Priority classification by business blast radius and failure probability.</li>
                        <li><span class="check">✓</span> <strong>15-Field Input Matrix:</strong> Exhaustive boundary checks (Email, Phone, Currency, Regex, SQLi chars).</li>
                        <li><span class="check">✓</span> <strong>12-Column Excel Exporter:</strong> 1-click Markdown-to-Excel export with formulas and conditional formatting.</li>
                        <li><span class="check">✓</span> <strong>Edge-Case Discovery:</strong> Auto-flags double-click submission, concurrent race conditions, and session timeouts.</li>
                    </ul>
                </div>

                <!-- Pillar 2: Automation -->
                <div class="pillar-card">
                    <div class="pillar-icon-box" style="background: rgba(99, 102, 241, 0.15); color: #818cf8);">⚡</div>
                    <div class="pillar-title">
                        <span>2. Test Automation & Clean POM</span>
                        <span class="pill-win">Flat Architecture</span>
                    </div>
                    <p class="pillar-desc">Enforces Clean Page Object Model standards where test scripts strictly call business action methods.</p>
                    <ul class="pillar-features">
                        <li><span class="check">✓</span> <strong>Zero-Locator Scripts:</strong> Raw XPaths and CSS selectors strictly forbidden inside test cases.</li>
                        <li><span class="check">✓</span> <strong>5-Stage FSM Swarm:</strong> Deterministic workflow from live element probing to self-healing execution.</li>
                        <li><span class="check">✓</span> <strong>Sub-200ms Live Probing:</strong> Headless Playwright live DOM/AOM inspection before writing locators.</li>
                        <li><span class="check">✓</span> <strong>Polyglot Codebase:</strong> Native support for Playwright (TS/JS), Cypress, Selenium, Pytest, and Katalon.</li>
                    </ul>
                </div>

                <!-- Pillar 3: API & Contract -->
                <div class="pillar-card">
                    <div class="pillar-icon-box" style="background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald);">🌐</div>
                    <div class="pillar-title">
                        <span>3. API & Contract Intelligence</span>
                        <span class="pill-win">Zero Drift</span>
                    </div>
                    <p class="pillar-desc">End-to-end API lifecycle testing from OpenAPI/Swagger contracts to live chaos network simulation.</p>
                    <ul class="pillar-features">
                        <li><span class="check">✓</span> <strong>OpenAPI Spec-to-Matrix:</strong> Compiles OpenAPI specs into positive, boundary, and negative test suites.</li>
                        <li><span class="check">✓</span> <strong>API Drift Sentinel:</strong> AST-based schema change detector prevents breaking contract changes.</li>
                        <li><span class="check">✓</span> <strong>Network Mock Shield:</strong> In-browser HTTP/GraphQL stubbing, network throttling, and 500 error injection.</li>
                        <li><span class="check">✓</span> <strong>Newman / Postman Bridge:</strong> Automated Postman collection conversion and execution diagnostics.</li>
                    </ul>
                </div>

                <!-- Pillar 4: Performance -->
                <div class="pillar-card">
                    <div class="pillar-icon-box" style="background: rgba(245, 158, 11, 0.15); color: var(--accent-amber);">📈</div>
                    <div class="pillar-title">
                        <span>4. Performance & Reliability</span>
                        <span class="pill-win">SLA Enforcer</span>
                    </div>
                    <p class="pillar-desc">Backend stress benchmarking, Core Web Vitals telemetry, and anti-flakiness quarantine management.</p>
                    <ul class="pillar-features">
                        <li><span class="check">✓</span> <strong>Multi-Engine Load Generator:</strong> Generates production k6, Locust, and Apache JMeter (.jmx) plans.</li>
                        <li><span class="check">✓</span> <strong>Core Web Vitals Profiler:</strong> Measures LCP, CLS, and INP with CDP deep profiling.</li>
                        <li><span class="check">✓</span> <strong>Flaky Test Sentinel:</strong> Non-deterministic variance scoring and automated quarantine quarantine gating.</li>
                        <li><span class="check">✓</span> <strong>Matrix Duration Sharder:</strong> Bin-packing algorithm balances parallel CI runners within 5% variance.</li>
                    </ul>
                </div>
            </div>
        </section>

        <!-- 3 Hero Highlights -->
        <section id="hero-features" style="scroll-margin-top: 80px;">
            <div class="section-header">
                <span class="section-tag">Ground-Truth Rigor</span>
                <h2 class="section-title">3 Hero Superpowers</h2>
                <p class="section-desc">Key architectural innovations that prevent AI hallucinations, tautological tests, and pipeline flakiness.</p>
            </div>

            <div class="highlights-grid">
                <div class="highlight-card">
                    <div>
                        <span class="highlight-badge" style="background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.3);">HERO 1 &bull; AST LINTER</span>
                        <h3 class="highlight-title">Fake-Pass Sentinel</h3>
                        <p class="highlight-desc">AI agents often generate empty tests or catch-and-ignore blocks to make CI appear green. Our AST linter scans the syntax tree to catch 0-assertion tests and swallowed exceptions in 0.02s.</p>
                    </div>
                    <div class="code-snippet">npx synapse-hub lint</div>
                </div>

                <div class="highlight-card">
                    <div>
                        <span class="highlight-badge" style="background: rgba(168, 85, 247, 0.15); color: var(--accent-purple); border: 1px solid rgba(168, 85, 247, 0.3);">HERO 2 &bull; MUTATION ENGINE</span>
                        <h3 class="highlight-title">Syntactic Micro-Mutator</h3>
                        <p class="highlight-desc">Inverts operators, strips return values, and mutates condition boundaries. Verifies test assertions catch real defects with a mandatory Mutation Score threshold of &ge; 80%.</p>
                    </div>
                    <div class="code-snippet">npx synapse-hub mutate --min-score 80</div>
                </div>

                <div class="highlight-card">
                    <div>
                        <span class="highlight-badge" style="background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); border: 1px solid rgba(6, 182, 212, 0.3);">HERO 3 &bull; CONTEXT SHIELD</span>
                        <h3 class="highlight-title">95% Log Distillation</h3>
                        <p class="highlight-desc">CLI and Gradle dumps containing 2,000+ lines cause LLM "Lost in the Middle" errors. Distills raw output down to the exact failing line and the last 3 network requests.</p>
                    </div>
                    <div class="code-snippet">npx synapse-hub distill &lt;log_file&gt;</div>
                </div>
            </div>
        </section>

        <!-- Interactive Terminal / Quickstart Cheatsheet -->
        <section id="quickstart" style="scroll-margin-top: 80px;">
            <div class="section-header">
                <span class="section-tag">Instant Productivity</span>
                <h2 class="section-title">Zero-Configuration CLI Cheatsheet</h2>
                <p class="section-desc">Run all Synapse Hub capabilities directly via npx without manual configuration.</p>
            </div>

            <div class="terminal-box">
                <div class="terminal-header">
                    <div class="terminal-dots">
                        <div class="terminal-dot dot-red"></div>
                        <div class="terminal-dot dot-yellow"></div>
                        <div class="terminal-dot dot-green"></div>
                    </div>
                    <div class="terminal-title">synapse-hub-cli &bull; zsh</div>
                    <div style="font-size: 11px; color: var(--accent-emerald);">● Ready</div>
                </div>

                <div class="terminal-tabs">
                    <div class="terminal-tab active" onclick="switchTab(event, 'tab-doctor')">1. Doctor</div>
                    <div class="terminal-tab" onclick="switchTab(event, 'tab-setup')">2. Setup Project</div>
                    <div class="terminal-tab" onclick="switchTab(event, 'tab-verify')">3. Verify 9 Gates</div>
                    <div class="terminal-tab" onclick="switchTab(event, 'tab-lint')">4. Scan Fake-Pass</div>
                    <div class="terminal-tab" onclick="switchTab(event, 'tab-excel')">5. Export Excel</div>
                    <div class="terminal-tab" onclick="switchTab(event, 'tab-dashboard')">6. Dashboard</div>
                </div>

                <div class="terminal-body">
                    <!-- Tab Doctor -->
                    <div id="tab-doctor" class="tab-pane">
                        <div class="cmd-line">
                            <div class="cmd-text"><span class="prompt">$</span>npx synapse-hub doctor</div>
                            <button class="copy-btn" onclick="copyCmd('npx synapse-hub doctor')">Copy</button>
                        </div>
                        <p class="cmd-desc">🩺 Runs a 1-click diagnostic scan verifying Python 3.9+, Node.js, Git hooks, browser drivers, and Central Agent Memory.</p>
                    </div>

                    <!-- Tab Setup -->
                    <div id="tab-setup" class="tab-pane" style="display:none;">
                        <div class="cmd-line">
                            <div class="cmd-text"><span class="prompt">$</span>npx synapse-hub setup</div>
                            <button class="copy-btn" onclick="copyCmd('npx synapse-hub setup')">Copy</button>
                        </div>
                        <p class="cmd-desc">⚡ 1-click bootstrap of target repository: generates PROJECT_AI_GUIDE.md, universal AI bridges, AST map, and pre-push sentinel.</p>
                    </div>

                    <!-- Tab Verify -->
                    <div id="tab-verify" class="tab-pane" style="display:none;">
                        <div class="cmd-line">
                            <div class="cmd-text"><span class="prompt">$</span>npx synapse-hub verify</div>
                            <button class="copy-btn" onclick="copyCmd('npx synapse-hub verify')">Copy</button>
                        </div>
                        <p class="cmd-desc">🛡️ Enforces all 9 Quality Gates Definition-of-Done (UTF-8 No BOM, Clean POM, Path Portability, Mutation &ge; 80%).</p>
                    </div>

                    <!-- Tab Lint -->
                    <div id="tab-lint" class="tab-pane" style="display:none;">
                        <div class="cmd-line">
                            <div class="cmd-text"><span class="prompt">$</span>npx synapse-hub lint</div>
                            <button class="copy-btn" onclick="copyCmd('npx synapse-hub lint')">Copy</button>
                        </div>
                        <p class="cmd-desc">🔍 AST scan detecting fake passes (0 assertions), empty catch blocks, and swallowed exceptions across all test scripts.</p>
                    </div>

                    <!-- Tab Excel -->
                    <div id="tab-excel" class="tab-pane" style="display:none;">
                        <div class="cmd-line">
                            <div class="cmd-text"><span class="prompt">$</span>npx synapse-hub export-excel &lt;path_to_markdown&gt;</div>
                            <button class="copy-btn" onclick="copyCmd('npx synapse-hub export-excel')">Copy</button>
                        </div>
                        <p class="cmd-desc">📊 Compiles markdown test cases into a professional 12-column Excel workbook with status dropdowns and formulas.</p>
                    </div>

                    <!-- Tab Dashboard -->
                    <div id="tab-dashboard" class="tab-pane" style="display:none;">
                        <div class="cmd-line">
                            <div class="cmd-text"><span class="prompt">$</span>npx synapse-hub dashboard</div>
                            <button class="copy-btn" onclick="copyCmd('npx synapse-hub dashboard')">Copy</button>
                        </div>
                        <p class="cmd-desc">📈 Compiles and opens the standalone executive QA HTML report in your browser.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Comparison Table Section -->
        <section id="comparison" style="scroll-margin-top: 80px;">
            <div class="section-header">
                <span class="section-tag">Value Proposition</span>
                <h2 class="section-title">How Synapse Hub Compares</h2>
                <p class="section-desc">Why enterprise teams choose Synapse Hub as the unified intelligence layer over fragmented single-purpose tools.</p>
            </div>

            <div class="comparison-table-wrap">
                <table class="comparison-table">
                    <thead>
                        <tr>
                            <th>Capability / Dimension</th>
                            <th class="col-synapse" style="color: var(--accent-cyan);">⚡ Synapse Hub</th>
                            <th>ESLint Plugin (Playwright)</th>
                            <th>Stryker Mutator</th>
                            <th>Allure Framework</th>
                            <th>Healenium</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Scope & Lifecycle</strong></td>
                            <td class="col-synapse"><span class="pill-win">Full 4-Pillar QA Hub</span></td>
                            <td>JS/TS Linter Only</td>
                            <td>Mutation Engine Only</td>
                            <td>Test Reporter Only</td>
                            <td>Self-Healing Proxy Only</td>
                        </tr>
                        <tr>
                            <td><strong>Target Audience</strong></td>
                            <td class="col-synapse"><span class="pill-win">AI Agents + QA Engineers</span></td>
                            <td>Frontend Developers</td>
                            <td>Senior Developers</td>
                            <td>QA Leads / Managers</td>
                            <td>Selenium SDETs</td>
                        </tr>
                        <tr>
                            <td><strong>Multi-Language AST</strong></td>
                            <td class="col-synapse"><span class="pill-win">Python, TS, JS, Groovy, Java</span></td>
                            <td>JavaScript / TypeScript</td>
                            <td>JS, C#, Scala</td>
                            <td>Polyglot (Output only)</td>
                            <td>Java / Python (Selenium)</td>
                        </tr>
                        <tr>
                            <td><strong>Fake-Pass AST Sentinel</strong></td>
                            <td class="col-synapse"><span class="pill-win">Native (0.02s Scan)</span></td>
                            <td>Partial (expect rules)</td>
                            <td>❌ No (High execution cost)</td>
                            <td>❌ No</td>
                            <td>❌ No</td>
                        </tr>
                        <tr>
                            <td><strong>Air-Gapped & Offline Ready</strong></td>
                            <td class="col-synapse"><span class="pill-win">100% Offline (Zero API cost)</span></td>
                            <td>100% Offline</td>
                            <td>100% Offline</td>
                            <td>100% Offline</td>
                            <td>Requires DB / Backend</td>
                        </tr>
                        <tr>
                            <td><strong>Manual QA (AI-RBT & Excel)</strong></td>
                            <td class="col-synapse"><span class="pill-win">Native 12-Col Exporter</span></td>
                            <td>❌ No</td>
                            <td>❌ No</td>
                            <td>❌ No</td>
                            <td>❌ No</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>

        <!-- 9 Quality Gates DoD Section -->
        <section id="quality-gates" style="scroll-margin-top: 80px;">
            <div class="section-header">
                <span class="section-tag">Zero-Hallucination Pipeline</span>
                <h2 class="section-title">9 Quality Gates DoD Sentinel</h2>
                <p class="section-desc">Every AI-generated test script must satisfy all 9 Quality Gates before code can be committed or merged.</p>
            </div>

            <div class="gates-grid">
                <div class="gate-card">
                    <div class="gate-top"><span class="gate-badge">GATE 0</span><span class="gate-pass">✓ PASS</span></div>
                    <div class="gate-name">Author Attribution & Integrity</div>
                    <div class="gate-desc">Cryptographic provenance invariant preserving author Thế Vị (@TeeVee998) MIT license.</div>
                </div>
                <div class="gate-card">
                    <div class="gate-top"><span class="gate-badge">GATE 1</span><span class="gate-pass">✓ PASS</span></div>
                    <div class="gate-name">UTF-8 No BOM & Clean Encoding</div>
                    <div class="gate-desc">100% UTF-8 without BOM or mojibake bytes across all test files and configs.</div>
                </div>
                <div class="gate-card">
                    <div class="gate-top"><span class="gate-badge">GATE 2</span><span class="gate-pass">✓ PASS</span></div>
                    <div class="gate-name">Path Portability</div>
                    <div class="gate-desc">Zero machine-specific absolute file paths (/Users/..., C:\\...) committed to git.</div>
                </div>
                <div class="gate-card">
                    <div class="gate-top"><span class="gate-badge">GATE 3</span><span class="gate-pass">✓ PASS</span></div>
                    <div class="gate-name">Clean POM Flat Architecture</div>
                    <div class="gate-desc">Strictly zero raw XPaths or CSS selectors inside test scripts; encapsulated in Pages.</div>
                </div>
                <div class="gate-card">
                    <div class="gate-top"><span class="gate-badge">GATE 4</span><span class="gate-pass">✓ PASS</span></div>
                    <div class="gate-name">AI Documentation Anti-Drift</div>
                    <div class="gate-desc">Zero hallucinated classes or missing test suites between code and PROJECT_AI_GUIDE.md.</div>
                </div>
                <div class="gate-card">
                    <div class="gate-top"><span class="gate-badge">GATE 5</span><span class="gate-pass">✓ PASS</span></div>
                    <div class="gate-name">Temporary File Blacklist</div>
                    <div class="gate-desc">Zero temporary files (*.tmp, *.db, memory dumps) polluting repository workspace.</div>
                </div>
                <div class="gate-card">
                    <div class="gate-top"><span class="gate-badge">GATE 6</span><span class="gate-pass">✓ PASS</span></div>
                    <div class="gate-name">Credential Security Sentinel</div>
                    <div class="gate-desc">Zero hardcoded plaintext passwords, private keys, or API tokens in scripts.</div>
                </div>
                <div class="gate-card">
                    <div class="gate-top"><span class="gate-badge">GATE 7</span><span class="gate-pass">✓ PASS</span></div>
                    <div class="gate-name">Static Defect & Fake-Pass</div>
                    <div class="gate-desc">Meta Infer-style AST scan catching 0-assertion tests and swallowed exception blocks.</div>
                </div>
                <div class="gate-card">
                    <div class="gate-top"><span class="gate-badge">GATE 8</span><span class="gate-pass">✓ PASS</span></div>
                    <div class="gate-name">Syntactic Micro-Mutation</div>
                    <div class="gate-desc">Requires test suite mutation score &ge; 80% to eliminate tautological test cases.</div>
                </div>
            </div>
        </section>

        <!-- Subagent Swarm Architecture -->
        <section id="swarm" style="scroll-margin-top: 80px;">
            <div class="section-header">
                <span class="section-tag">Autonomous Multi-Agent System</span>
                <h2 class="section-title">6 Specialized Subagent Profiles</h2>
                <p class="section-desc">Coordinated through a single front-door FSM architecture to avoid decision paralysis.</p>
            </div>

            <div class="swarm-grid">
                <div class="agent-card">
                    <div class="agent-icon">👑</div>
                    <div class="agent-role">Lead QA Orchestrator</div>
                    <span class="agent-id">@orchestrator</span>
                    <p class="agent-desc">Ingests user intent, scopes impact, bootstraps projects, and enforces sequential FSM transitions.</p>
                </div>
                <div class="agent-card">
                    <div class="agent-icon">🔍</div>
                    <div class="agent-role">Live Interaction Explorer</div>
                    <span class="agent-id">@live-explorer</span>
                    <p class="agent-desc">Probes live web DOM/AOM under 200ms using headless Playwright. Zero selector guessing.</p>
                </div>
                <div class="agent-card">
                    <div class="agent-icon">🏛️</div>
                    <div class="agent-role">Clean POM Crafter</div>
                    <span class="agent-id">@pom-crafter</span>
                    <p class="agent-desc">Designs multi-language Page Classes and test scripts enforcing strict Clean POM Flat Architecture.</p>
                </div>
                <div class="agent-card">
                    <div class="agent-icon">⚡</div>
                    <div class="agent-role">Test Execution Runner</div>
                    <span class="agent-id">@test-runner</span>
                    <p class="agent-desc">Dispatches headless test runs via CLI, balances parallel runner shards, and distills 95% of log noise.</p>
                </div>
                <div class="agent-card">
                    <div class="agent-icon">🩺</div>
                    <div class="agent-role">Failure Autopsy Analyst</div>
                    <span class="agent-id">@failure-analyst</span>
                    <p class="agent-desc">Closed-loop failure diagnosis from JUnit XML and screenshots; generates auto-healing PR plans.</p>
                </div>
                <div class="agent-card">
                    <div class="agent-icon">🛡️</div>
                    <div class="agent-role">Quality Gatekeeper Sentinel</div>
                    <span class="agent-id">@quality-gatekeeper</span>
                    <p class="agent-desc">Final gatekeeper enforcing all 9 Quality Gates DoD and &ge; 80% mutation score before task completion.</p>
                </div>
            </div>
        </section>

    </main>

    <!-- Footer -->
    <footer>
        <div class="container">
            <div class="footer-grid">
                <div class="footer-brand">
                    <div class="brand">
                        <div class="brand-icon">⚡</div>
                        <span class="brand-name">SYNAPSE HUB</span>
                    </div>
                    <p>The Enterprise AI Agent Quality Engineering & Autonomous Skill Network.</p>
                </div>
                <ul class="footer-links">
                    <li><a href="PROJECT_DASHBOARD.html">Dashboard</a></li>
                    <li><a href="{meta['repo']}">GitHub Repository</a></li>
                    <li><a href="{meta['repo']}/issues">Report an Issue</a></li>
                    <li><a href="{meta['repo']}/blob/develop/docs/CONTRIBUTING.md">Contributing</a></li>
                </ul>
            </div>
            <div class="footer-bottom">
                <p>
                    Original Creator: <strong>{meta['author']}</strong> &bull; Released under the 
                    <a href="{meta['repo']}/blob/develop/LICENSE" target="_blank" rel="noopener">MIT License</a>.
                    All author attribution notices preserved in accordance with open-source licensing.
                </p>
                <p style="margin-top: 6px; font-size: 11px; color: var(--text-muted);">Generated on {now_str} &bull; Offline & Air-Gapped Ready</p>
            </div>
        </div>
    </footer>

    <!-- Toast Notification -->
    <div id="toast" class="toast">✓ Copied to clipboard!</div>

    <!-- Interactive Script -->
    <script>
        function switchTab(evt, tabId) {{
            const tabs = document.querySelectorAll('.terminal-tab');
            const panes = document.querySelectorAll('.tab-pane');
            
            tabs.forEach(t => t.classList.remove('active'));
            panes.forEach(p => p.style.display = 'none');
            
            evt.currentTarget.classList.add('active');
            const target = document.getElementById(tabId);
            if (target) target.style.display = 'block';
        }}

        function copyCmd(cmd) {{
            if (navigator.clipboard && window.isSecureContext) {{
                navigator.clipboard.writeText(cmd).then(() => showToast());
            }} else {{
                const textArea = document.createElement("textarea");
                textArea.value = cmd;
                textArea.style.position = "fixed";
                textArea.style.left = "-9999px";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {{
                    document.execCommand('copy');
                    showToast();
                }} catch (err) {{
                    console.error('Failed to copy', err);
                }}
                document.body.removeChild(textArea);
            }}
        }}

        function showToast() {{
            const toast = document.getElementById('toast');
            toast.classList.add('show');
            setTimeout(() => {{
                toast.classList.remove('show');
            }}, 2000);
        }}
    </script>
</body>
</html>
"""
    return html


def write_welcome_page(output_path: Optional[str] = None, target_repo: Optional[str] = None, stack_info: Optional[Dict[str, str]] = None) -> str:
    """Generates and writes the welcome landing page to disk."""
    if not output_path:
        base_dir = target_repo if target_repo else HUB_ROOT
        reports_dir = os.path.join(base_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        output_path = os.path.join(reports_dir, "WELCOME.html")
    else:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    html_content = generate_welcome_html(target_repo=target_repo, stack_info=stack_info)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path


def open_welcome_page(file_path: str) -> bool:
    """
    Opens the welcome page in the user's default browser if not running in headless/CI mode.
    Returns True if successfully launched, False otherwise.
    """
    if os.environ.get("CI") or os.environ.get("HEADLESS"):
        return False

    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        return False

    file_url = f"file://{abs_path}"
    try:
        webbrowser.open(file_url)
        return True
    except Exception:
        return False


def generate_welcome_page(target_repo: Optional[str] = None, output_path: Optional[str] = None, stack_info: Optional[Dict[str, str]] = None, open_browser: bool = True) -> str:
    """
    Full workflow helper: generates the landing page and opens it if requested.
    """
    out_file = write_welcome_page(output_path=output_path, target_repo=target_repo, stack_info=stack_info)
    if open_browser:
        opened = open_welcome_page(out_file)
        if opened:
            print(f"  🚀 Opened Synapse Hub visual landing page in your browser.")
    return out_file


def main():
    parser = argparse.ArgumentParser(description="Synapse Hub Visual Landing Page Generator")
    parser.add_argument("target", nargs="?", default=None, help="Target repository directory (default: current directory)")
    parser.add_argument("--output", "-o", default=None, help="Output HTML file path (default: reports/WELCOME.html)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser after generating the page")
    parser.add_argument("--open", action="store_true", help="Explicitly open the browser")
    args = parser.parse_args()

    target_dir = os.path.abspath(args.target) if args.target else HUB_ROOT
    should_open = not args.no_browser if (not os.environ.get("CI")) else args.open

    print(f"🎨 Generating Synapse Hub Visual Landing Page...")
    out_path = generate_welcome_page(
        target_repo=target_dir,
        output_path=args.output,
        open_browser=should_open
    )
    print(f"✅ Landing page generated successfully at:\n   file://{out_path}")
    print(f"👉 You can re-open it anytime with: npx synapse-hub welcome")


if __name__ == "__main__":
    main()
