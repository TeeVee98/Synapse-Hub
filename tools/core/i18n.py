#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Synapse Hub — Bilingual Internationalization Engine (tools.core.i18n)
---------------------------------------------------------------------
Provides centralized English/Vietnamese message resolution across
the CLI hub, Web UI bridges, and automated developer experience tools.
Precedence: CLI flag > ENV (SYNAPSE_LANG) > .synapse.json / ~/.synapse.json > 'en'
"""

import os
import json
import locale
from typing import Dict, Any, Optional

MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "banner_title": "SYNAPSE HUB CLI — Enterprise AI Agent Quality Engineering Hub",
        "hub_cli_description": "Enterprise AI Agent Quality Engineering & Test Automation Hub CLI",
        "version_info": "Version: v{version} | Author: Thế Vị (@TeeVee998) | License: MIT",
        "usage_title": "USAGE:",
        "usage_syntax": "  agent-qa <command> [options...]",
        "core_commands_title": "🌟 CORE & DAILY WORKFLOWS:",
        "advanced_highlights_title": "🎯 ADVANCED AI/QA CAPABILITIES:",
        "general_options_title": "GENERAL OPTIONS:",
        "opt_all": "Display all 58+ advanced and infrastructure commands",
        "opt_version": "Show current version and author provenance",
        "opt_offline": "Force 100% offline air-gapped mode (zero network / LLM calls)",
        "opt_quiet": "Suppress banner, show only verdict and critical output",
        "opt_lang": "Set CLI interface language (en: English, vi: Vietnamese)",
        "tips_header": "💡 Quick Navigation Tips:",
        "tip_all": "👉 Run 'agent-qa --help --all' to inspect all 58+ commands.",
        "tip_cmd": "👉 Run 'agent-qa <command> --help' for detailed command options.",
        "tip_welcome": "👉 Run 'agent-qa welcome' to launch the interactive visual landing page.",
        "tip_lang_switch": "💡 Switch language: agent-qa --lang vi (Vietnamese) | agent-qa --lang en (English)",
        "cmd_set_lang": "Set and persist CLI interface language (en: English, vi: Vietnamese)",
        "lang_saved": "✅ Interface language preference saved: {lang_name} ({lang_code}) -> {config_path}",
        "cmd_doctor": "Run 1-click diagnostic check of environment (Node.js, Python, Git, Browsers)",
        "cmd_setup": "Autonomous 1-click bootstrap of target project (AI guide, Git hook, AST map)",
        "cmd_init_config": "Initialize standardized .synapse.json configuration for Spoke project",
        "cmd_lint": "AST scan catching fake-passes (0 assert, try-catch swallow, hard sleeps)",
        "cmd_verify": "Execute 11 Quality Gates Definition of Done (DoD) verification",
        "cmd_export_excel": "Export Markdown test cases to enterprise 12-column Excel (.xlsx)",
        "cmd_welcome": "Launch interactive visual landing page introducing Synapse Hub",
        "cmd_ui": "Launch real-time Interactive Mission Control Web UI dashboard",
        "cmd_dashboard": "Generate standalone executive HTML project health dashboard",
        "cmd_analyze": "Execute comprehensive project health & AST knowledge graph analysis",
        "cmd_mutate": "Syntactic micro-mutation testing measuring assertion sensitivity (Kill Score >= 80%)",
        "cmd_auto_heal": "Autonomous test self-healing (Reflexion K=3) using AOM contextual diff",
        "cmd_som": "Visual Set-of-Marks grounding on Canvas/GIS elements without DOM",
        "cmd_fuzz_api": "Autonomous API fuzzing & chaos fault injection breaker",
        "cmd_transpile": "Zero-token polyglot test transpilation across Playwright, Cypress, Selenium",
        "cmd_help": "Display CLI help and command search reference",
        "cmd_version": "Show Hub version and catalog metadata",
        "cmd_uninstall": "Revert and remove files installed by setup in target project",
        "cmd_clean": "Clean build artifacts, __pycache__, and bytecode",
        "cmd_update": "1-Click update Synapse-Hub to latest version from GitHub/NPM",
        "cmd_check_version": "Verify universal version synchronization across all files",
        "cmd_sync_rules": "Synchronize AGENTS.md single source of truth across all AI IDE bridges",
        "cmd_heal_pr": "Calculate self-healing confidence and generate Git PR draft",
        "cmd_heal": "Query, learn, or record-failed into semantic memory cache",
        "cmd_shard": "Balance parallel CI/CD test execution using duration-balanced bin-packing",
        "cmd_sync_jira": "Bidirectional sync with Jira / Xray / Zephyr (pull stories, push tests, create bugs)",
        "cmd_trend": "Historical Quality Trend & Flakiness Analytics Engine",
        "cmd_flaky": "Detect flaky tests and manage quarantine lifecycle",
        "cmd_canary": "Run autonomous canary resilience benchmark",
        "cmd_watch": "Real-Time incremental watch mode & test engineering HUD (< 100ms feedback)",
        "cmd_pinpoint_failure": "Parse JUnit XML and locate exact failing line in 0.1s",
        "cmd_ci_hook": "CI/CD Silent Self-Healing Pipeline Hook & Automated PR Generator",
        "cmd_debt": "Harvest shortcut: comments into a tracked technical debt ledger",
        "cmd_review": "Senior developer quality & lean diff review (bugs, security, scale, tests, bloat)",
        "cmd_safety_check": "Action Safety Firewall & Blast Radius Containment",
        "cmd_contract_drift": "Detect breaking API changes across OpenAPI / Swagger specs",
        "cmd_skillspector": "AI Agent Skill & MCP Security Sentinel (71 vectors, NVIDIA SkillSpector spec)",
        "cmd_verify_author": "Verify author attribution, provenance, and anti-tamper integrity",
        "cmd_wcag_audit": "Audit WCAG 2.2 accessibility conformance and contrast ratios",
        "cmd_impact": "Analyze code change impact using AST Knowledge Graph",
        "cmd_review_spec": "Zero-context stress-test for specifications and user stories (Elephant-Goldfish Model)",
        "cmd_drift_check": "Spec-to-Code Drift Sentinel checking Deficit & Scope Drift",
        "cmd_trace_data_flow": "Trace test data lifecycles to detect DB leaks and missing teardowns",
        "cmd_distill": "Distill and filter verbose CLI logs by 95 percent",
        "cmd_gherkin": "Compile Gherkin .feature files into test matrix, Universal IR and coverage-gap report (0-token)",
        "cmd_omni_scan": "Scan repository and build polyglot test inventory (0-token)",
        "cmd_report_bug": "Auto-generate enterprise Jira/Markdown Bug Ticket with RCA",
        "cmd_mock_shield": "Generate API Route Interception & Chaos Fault Injection Shield",
        "cmd_visual_mask": "Smart Visual Masking & Anti-Flake Animation Blocker",
        "cmd_migrate": "Autonomous suite migration from legacy (Katalon/Cypress) to modern Playwright",
        "cmd_decouple_config": "Decouple hardcoded URLs, credentials, and secrets into env profiles",
        "cmd_export_postman": "Export OpenAPI / Swagger / HAR to Postman Collection v2.1.0 with auto-asserts",
        "cmd_generate_jmx": "Generate Apache JMeter 5.x Test Plan XML (.jmx) with JMeter 360 Enterprise Capabilities",
        "cmd_analyze_jtl": "Analyze JMeter .jtl results, evaluate P90/P95/P99 SLA, and enforce CI/CD Quality Gate",
        "cmd_correlate_telemetry": "Correlate Client-Side JMeter latency with Server-Side APM CPU/RAM/DB telemetry",
        "cmd_analyze_newman": "Analyze Postman / Newman test results, triage failed assertions, and enforce CI/CD Quality Gate",
        "cmd_tokens": "Audit token usage and estimated API cost across Antigravity, Cursor, and Claude Code",
        "cmd_lookup_tc": "Search test cases by ID, tag, priority, or flow",
        "cmd_lookup_xpath": "Query cached resilient XPath & AOM locators",
        "cmd_generate_tc": "Compile natural language user stories into Clean POM test cases",
        "cmd_api_matrix": "Generate Positive, Boundary, and Negative test matrix from OpenAPI/Swagger",
        "cmd_canvas_diff": "HTML5 Canvas visual regression diffing & blank check",
        "cmd_validate_groovy": "Pre-check Groovy scripts & keywords syntax balance",
        "cmd_mcp_serve": "Start the JSON-RPC 2.0 stdio Model Context Protocol (MCP) server",
        "cmd_mcp_excel": "Start the JSON-RPC 2.0 stdio MCP Excel server",
        "cmd_mcp_docx": "Start the JSON-RPC 2.0 stdio MCP Word (.docx) server",
        "cmd_release": "1-Click atomic release: bump version across all targets, verify DoD gates, git tag & push for NPM",
        "cmd_publish": "1-Click end-to-end publish pipeline: push main, git tag, create release, GitHub package & NPM publish",
        "subcommands_help": "Available subcommands",
        "typo_error": "❌ Error: Command '{choice}' does not exist in Synapse-Hub.",
        "typo_suggest": "💡 Did you mean: {suggestions} ?",
        "typo_help_hint": "👉 Try running: agent-qa {first_match} --help",
        "typo_list_hint": "👉 Type 'agent-qa --help' to see all available commands.",
    },
    "vi": {
        "banner_title": "SYNAPSE HUB CLI — Enterprise AI Agent Quality Engineering Hub",
        "hub_cli_description": "Nền tảng kỹ thuật kiểm thử và đảm bảo chất lượng AI Agent tự động",
        "version_info": "Phiên bản: v{version} | Tác giả: Thế Vị (@TeeVee998) | Giấy phép: MIT",
        "usage_title": "CÚ PHÁP SỬ DỤNG:",
        "usage_syntax": "  agent-qa <lệnh> [tùy_chọn...]",
        "core_commands_title": "🌟 LỆNH CỐT LÕI & THƯỜNG DÙNG:",
        "advanced_highlights_title": "🎯 CÁC KHÁI NIỆM AI/QA NÂNG CAO TIÊU BIỂU:",
        "general_options_title": "TÙY CHỌN CHUNG:",
        "opt_all": "Hiển thị toàn bộ 58+ lệnh nâng cao & hạ tầng",
        "opt_version": "Hiển thị phiên bản hiện tại và thông tin tác quyền MIT",
        "opt_offline": "Ép chế độ 100% offline air-gapped (zero network / LLM calls)",
        "opt_quiet": "Ẩn banner thông tin, chỉ xuất kết quả phán quyết quan trọng",
        "opt_lang": "Chọn ngôn ngữ hiển thị giao diện CLI (en: Tiếng Anh, vi: Tiếng Việt)",
        "tips_header": "💡 Mẹo Tra Cứu:",
        "tip_all": "👉 Chạy 'agent-qa --help --all' để xem toàn bộ 58+ lệnh.",
        "tip_cmd": "👉 Chạy 'agent-qa <lệnh> --help' để xem hướng dẫn chi tiết cho từng lệnh cụ thể.",
        "tip_welcome": "👉 Chạy 'agent-qa welcome' để mở giao diện Landing Page tương tác trực quan.",
        "tip_lang_switch": "💡 Chuyển đổi ngôn ngữ: agent-qa --lang vi (Tiếng Việt) | agent-qa --lang en (Tiếng Anh)",
        "cmd_set_lang": "Thiết lập và ghi nhớ ngôn ngữ giao diện CLI (en: Tiếng Anh, vi: Tiếng Việt)",
        "lang_saved": "✅ Đã lưu cấu hình ngôn ngữ giao diện: {lang_name} ({lang_code}) -> {config_path}",
        "cmd_doctor": "Kiểm tra chẩn đoán môi trường (Node.js, Python, Git, trình duyệt)",
        "cmd_setup": "Thiết lập bảo vệ 1-click cho dự án mục tiêu (AI rules, Git hook, AST map)",
        "cmd_init_config": "Khởi tạo file cấu hình .synapse.json chuẩn hóa cho dự án Spoke",
        "cmd_lint": "Quét AST phát hiện test pass ảo (0 assert, try-catch rỗng, sleep cứng)",
        "cmd_verify": "Kiểm tra toàn diện 11 Cổng Chất Lượng DoD (Definition of Done)",
        "cmd_export_excel": "Xuất test cases Markdown sang file Excel (.xlsx) chuẩn doanh nghiệp",
        "cmd_welcome": "Khởi chạy Landing Page trực quan giới thiệu các trụ cột của Synapse Hub",
        "cmd_ui": "Khởi chạy Web UI Mission Control tương tác thời gian thực (Live Dashboard)",
        "cmd_dashboard": "Tạo dashboard HTML báo cáo sức khỏe và tiến độ kiểm thử dự án",
        "cmd_analyze": "Phân tích tổng thể sức khỏe dự án và xây dựng bản đồ tri thức AST",
        "cmd_mutate": "Kiểm thử đột biến (AST Mutation) — đo độ nhạy câu lệnh assert (Min Score >= 80%)",
        "cmd_auto_heal": "Tự sửa test hỏng (Reflexion K=3) — AI tự soi chiếu vết lỗi và đề xuất bản vá",
        "cmd_som": "Gắn nhãn thị giác (Set-of-Marks) — đánh số trực quan trên Canvas/GIS để click chính xác",
        "cmd_fuzz_api": "API Chaos Fuzzing — bắn payload đột biến bắt lỗi 500 và rò rỉ dữ liệu",
        "cmd_transpile": "Chuyển đổi ngôn ngữ test giữa Playwright, Cypress, Selenium, Katalon",
        "cmd_help": "Hiển thị hướng dẫn tra cứu lệnh CLI của Synapse Hub",
        "cmd_version": "Hiển thị phiên bản Hub và danh mục kỹ năng (metadata)",
        "cmd_uninstall": "Gỡ bỏ các file cấu hình và hook do lệnh setup cài đặt",
        "cmd_clean": "Dọn dẹp tệp build thừa, __pycache__ và bytecode rác",
        "cmd_update": "Cập nhật 1-click Synapse-Hub lên phiên bản mới nhất từ GitHub/NPM",
        "cmd_check_version": "Kiểm tra tính đồng nhất của phiên bản trên toàn bộ tệp dự án",
        "cmd_sync_rules": "Đồng bộ tệp quy tắc AGENTS.md sang tất cả cấu hình cầu nối AI IDE",
        "cmd_heal_pr": "Tính điểm tin cậy tự phục hồi và tạo bản nháp Git PR tự động",
        "cmd_heal": "Tra cứu, học hoặc ghi nhận lỗi kiểm thử vào bộ nhớ ngữ nghĩa",
        "cmd_shard": "Phân bổ tải kiểm thử CI/CD song song cân bằng theo thời lượng",
        "cmd_sync_jira": "Đồng bộ 2 chiều với Jira / Xray / Zephyr (pull story, push tests, tạo bug tự động)",
        "cmd_trend": "Phân tích xu hướng chất lượng và độ ổn định kiểm thử theo thời gian",
        "cmd_flaky": "Phát hiện kiểm thử chập chờn (flaky) và quản lý vòng đời cách ly",
        "cmd_canary": "Chạy đánh giá chuẩn độ bền vững canary tự động",
        "cmd_watch": "Chế độ giám sát thay đổi thời gian thực & giao diện HUD (< 100ms)",
        "cmd_pinpoint_failure": "Phân tích JUnit XML và định vị chính xác dòng lỗi trong 0.1s",
        "cmd_ci_hook": "Hook tự động phục hồi trong CI/CD & tự động tạo PR sửa lỗi",
        "cmd_debt": "Thu hoạch các chú thích shortcut: vào sổ cái nợ kỹ thuật cần xử lý",
        "cmd_review": "Đánh giá chất lượng code chuẩn Senior Dev (lỗi, bảo mật, tải, test, code thừa)",
        "cmd_safety_check": "Tường lửa an toàn thao tác & khoanh vùng bán kính ảnh hưởng",
        "cmd_contract_drift": "Phát hiện sai lệch và vi phạm tương thích ngược trong OpenAPI/Swagger",
        "cmd_skillspector": "Quét bảo mật kỹ năng AI Agent & MCP (71 véc-tơ theo chuẩn NVIDIA SkillSpector)",
        "cmd_verify_author": "Xác minh tác quyền tác giả, nguồn gốc và tính toàn vẹn chống chỉnh sửa",
        "cmd_wcag_audit": "Kiểm toán độ tương phản và tuân thủ tiêu chuẩn tiếp cận WCAG 2.2",
        "cmd_impact": "Phân tích phạm vi ảnh hưởng thay đổi mã nguồn qua đồ thị tri thức AST",
        "cmd_review_spec": "Đánh giá chất lượng tài liệu đặc tả & user story theo mô hình Elephant-Goldfish",
        "cmd_drift_check": "Giám sát độ lệch giữa đặc tả và mã kiểm thử thực tế (Deficit & Scope Drift)",
        "cmd_trace_data_flow": "Theo dõi vòng đời dữ liệu test để phát hiện rò rỉ DB và thiếu sót teardown",
        "cmd_distill": "Cô đọng và tinh lọc log dài dòng giảm 95% độ nhiễu",
        "cmd_gherkin": "Biên dịch file Gherkin .feature thành ma trận kiểm thử, Universal IR và báo cáo thiếu phủ (0-token)",
        "cmd_omni_scan": "Quét toàn bộ dự án và thống kê danh mục kiểm thử đa ngôn ngữ (0-token)",
        "cmd_report_bug": "Tự động tạo phiếu báo lỗi Jira/Markdown chuyên nghiệp kèm phân tích nguyên nhân gốc",
        "cmd_mock_shield": "Tạo lá chắn chặn bắt API Route & tiêm lỗi hỗn loạn (Chaos Injection)",
        "cmd_visual_mask": "Mặt nạ thị giác thông minh & chặn hoạt ảnh chống chập chờn giao diện",
        "cmd_migrate": "Tự động chuyển đổi toàn diện bộ test cũ (Katalon/Cypress) sang Playwright hiện đại",
        "cmd_decouple_config": "Tách biệt URL, tài khoản và bí mật cứng vào các cấu hình môi trường chuẩn",
        "cmd_export_postman": "Xuất OpenAPI / Swagger / HAR sang Postman Collection v2.1.0 kèm assert tự động",
        "cmd_generate_jmx": "Tạo kịch bản Apache JMeter 5.x (.jmx) chuyên sâu với đầy đủ tính năng tải doanh nghiệp",
        "cmd_analyze_jtl": "Phân tích kết quả JMeter .jtl, đánh giá SLA P90/P95/P99 và chốt cổng CI/CD",
        "cmd_correlate_telemetry": "Đối chiếu độ trễ client JMeter với chỉ số CPU/RAM/DB máy chủ (APM Telemetry)",
        "cmd_analyze_newman": "Phân tích kết quả Newman/Postman, sàng lọc assert lỗi và chốt cổng kiểm soát CI/CD",
        "cmd_tokens": "Kiểm toán lượng token tiêu thụ và chi phí ước tính trên Antigravity, Cursor, Claude Code",
        "cmd_lookup_tc": "Tra cứu ca kiểm thử theo mã ID, nhãn tag, độ ưu tiên hoặc luồng nghiệp vụ",
        "cmd_lookup_xpath": "Tra cứu bộ định vị phần tử XPath và AOM bền vững đã ghi nhớ",
        "cmd_generate_tc": "Biên dịch tài liệu yêu cầu / user story tự nhiên thành kịch bản Clean POM chuẩn hóa",
        "cmd_api_matrix": "Tạo ma trận kiểm thử Positive, Boundary và Negative từ tài liệu OpenAPI/Swagger",
        "cmd_canvas_diff": "So sánh khác biệt giao diện đồ họa Canvas HTML5 & kiểm tra lỗi canvas trống",
        "cmd_validate_groovy": "Kiểm tra trước cú pháp đóng mở ngoặc và tính hợp lệ kịch bản Groovy",
        "cmd_mcp_serve": "Khởi chạy máy chủ giao thức Model Context Protocol (MCP) chuẩn JSON-RPC 2.0",
        "cmd_mcp_excel": "Khởi chạy máy chủ MCP Excel chuyên dụng qua luồng stdio",
        "cmd_mcp_docx": "Khởi chạy máy chủ MCP Word (.docx) chuyên dụng qua luồng stdio",
        "cmd_release": "Phát hành 1-click: nâng số phiên bản, kiểm tra 11 cổng DoD, gắn tag git và xuất bản NPM",
        "cmd_publish": "Quy trình phát hành trọn gói 1-click: đẩy nhánh main, tạo tag git, phát hành GitHub Release & NPM",
        "subcommands_help": "Danh sách các lệnh khả dụng",
        "typo_error": "❌ Lỗi: Lệnh '{choice}' không tồn tại trong Synapse-Hub.",
        "typo_suggest": "💡 Có phải ý bạn là: {suggestions} ?",
        "typo_help_hint": "👉 Thử chạy: agent-qa {first_match} --help",
        "typo_list_hint": "👉 Gõ 'agent-qa --help' để xem danh sách tất cả các lệnh khả dụng.",
    }
}


def _probe_cli_flag(cli_flag: Optional[str]) -> Optional[str]:
    """Probes the CLI flag for valid language codes ('vi', 'en')."""
    if not cli_flag:
        return None
    val = str(cli_flag).strip().lower()
    if val.startswith(("--lang=", "-l=")):
        val = val.split("=", 1)[1].strip().lower()
    if val in ("vi", "en"):
        return val
    return None


def _probe_env_lang() -> Optional[str]:
    """Probes the SYNAPSE_LANG environment variable."""
    env_lang = os.environ.get("SYNAPSE_LANG", "").strip().lower()
    if env_lang in ("vi", "en"):
        return env_lang
    return None


def persist_language_preference(lang: str, target_dir: Optional[str] = None) -> str:
    """
    Persists the chosen language code ('en' or 'vi') to configuration.
    1. If SYNAPSE_CONFIG_PATH is set in environment, persists to that file.
    2. Else if target_dir is provided, persists to target_dir/.synapse.json.
    3. Else if .synapse.json exists in CWD, updates it.
    4. Else if TARGET_PROJECT_DIR env var is set and has .synapse.json, updates it.
    5. Otherwise, persists globally to ~/.synapse.json.
    Returns the path of the file that was updated or created.
    """
    clean_lang = str(lang).strip().lower()
    if clean_lang not in ("vi", "en"):
        raise ValueError(f"Invalid language code: '{lang}'. Must be 'en' or 'vi'.")

    env_cfg = os.environ.get("SYNAPSE_CONFIG_PATH")
    if env_cfg:
        cfg_path = os.path.abspath(env_cfg)
    elif target_dir:
        cfg_path = os.path.abspath(os.path.join(target_dir, ".synapse.json"))
    elif os.path.isfile(os.path.join(os.getcwd(), ".synapse.json")):
        cfg_path = os.path.abspath(os.path.join(os.getcwd(), ".synapse.json"))
    elif os.environ.get("TARGET_PROJECT_DIR") and os.path.isfile(os.path.join(os.environ["TARGET_PROJECT_DIR"], ".synapse.json")):
        cfg_path = os.path.abspath(os.path.join(os.environ["TARGET_PROJECT_DIR"], ".synapse.json"))
    else:
        cfg_path = os.path.expanduser("~/.synapse.json")

    data: Dict[str, Any] = {}
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception as _err:
            _ = _err
            data = {}

    data["language"] = clean_lang

    parent = os.path.dirname(cfg_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return cfg_path


def _probe_config_file_lang() -> Optional[str]:
    """Probes target project config (.synapse.json) in CWD or TARGET_PROJECT_DIR."""
    try:
        candidate_dirs = [os.getcwd()]
        target_env = os.environ.get("TARGET_PROJECT_DIR")
        if target_env:
            candidate_dirs.append(target_env)
        for d in candidate_dirs:
            cfg_path = os.path.join(d, ".synapse.json")
            if os.path.isfile(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg_data = json.load(f)
                        if isinstance(cfg_data, dict):
                            cfg_lang = str(cfg_data.get("language", "")).strip().lower()
                            if cfg_lang in ("vi", "en"):
                                return cfg_lang
                except Exception as _err:
                    _ = _err
                    continue
    except Exception as _err:
        _ = _err
    return None


def _probe_global_config_lang() -> Optional[str]:
    """Probes user global config ~/.synapse.json or SYNAPSE_CONFIG_PATH."""
    try:
        env_cfg = os.environ.get("SYNAPSE_CONFIG_PATH")
        cfg_path = os.path.abspath(env_cfg) if env_cfg else os.path.expanduser("~/.synapse.json")
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
                    if isinstance(cfg_data, dict):
                        cfg_lang = str(cfg_data.get("language", "")).strip().lower()
                        if cfg_lang in ("vi", "en"):
                            return cfg_lang
            except Exception as _err:
                _ = _err
    except Exception as _err:
        _ = _err
    return None


def _probe_os_locale_lang() -> Optional[str]:
    """Probes the OS system locale environment variables and locale module."""
    try:
        for loc_key in ("LC_ALL", "LC_MESSAGES", "LANG"):
            val = (os.environ.get(loc_key) or "").lower()
            if val:
                if val.startswith("vi"):
                    return "vi"
                if val.startswith("en"):
                    return "en"
                return None
        loc_tuple = locale.getlocale() if hasattr(locale, "getlocale") else None
        if loc_tuple and loc_tuple[0]:
            code = loc_tuple[0].lower()
            if code.startswith("vi"):
                return "vi"
            if code.startswith("en"):
                return "en"
        if hasattr(locale, "getdefaultlocale"):
            raw_def = locale.getdefaultlocale()[0]
            if raw_def:
                def_loc = raw_def.lower()
                if def_loc.startswith("vi"):
                    return "vi"
                if def_loc.startswith("en"):
                    return "en"
    except Exception as _err:
        _ = _err
    return None


def resolve_language(cli_flag: Optional[str] = None) -> str:
    """
    Resolves the active interface language with precedence:
    1. CLI flag: --lang {en,vi}
    2. Environment Variable: SYNAPSE_LANG=en|vi
    3. Target Project Config: .synapse.json ("language": "en"|"vi")
    4. User Global Config: ~/.synapse.json ("language": "en"|"vi")
    5. Fallback: "en" (Strictly English default per specification)
    """
    return (
        _probe_cli_flag(cli_flag)
        or _probe_env_lang()
        or _probe_config_file_lang()
        or _probe_global_config_lang()
        or "en"
    )



def t(key: str, lang: str = "en", **kwargs: Any) -> str:
    """
    Translates a message key into target language with optional formatting.
    Falls back to English if the key is missing from the target language,
    and falls back to the key itself if not found in English.
    """
    lang_code = (lang or "en").lower()
    lang_dict = MESSAGES.get(lang_code, MESSAGES["en"])
    template = lang_dict.get(key, MESSAGES.get("en", {}).get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
