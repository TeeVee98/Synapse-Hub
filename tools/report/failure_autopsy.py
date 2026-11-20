#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Synapse Hub Interactive Failure Autopsy HTML Report Generator
-------------------------------------------------------------
Generates a standalone, 100% offline interactive HTML report from failed test cases.
Provides human-readable Root Cause Analysis (RCA) in Vietnamese and English,
code frame inspection around failing lines, and copy-paste remediation guidance.
"""

import os
import html as html_lib
from datetime import datetime
from typing import List, Dict, Any, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))


def classify_failure(reason: str) -> Dict[str, str]:
    """Classifies root cause and provides bilingual natural language RCA."""
    r_lower = reason.lower()

    if any(k in r_lower for k in ("assertionerror", "tobevisible", "tohavetext", "assertequals", "assert ", "expect(")):
        return {
            "category": "ASSERTION_MISMATCH",
            "badge_color": "#ef4444",
            "rca_vi": "Kỳ vọng kiểm thử không khớp với trạng thái thực tế của ứng dụng.",
            "rca_en": "Assertion failed: actual application state deviates from expected test outcome.",
            "action_vi": "Kiểm tra lại dữ liệu đầu vào hoặc xác thực lại UI có hiển thị đúng theo yêu cầu không."
        }
    elif any(k in r_lower for k in ("timeouterror", "timed out", "waitfor", "waiting for locator", "timeout")):
        return {
            "category": "LOCATOR_TIMEOUT",
            "badge_color": "#f59e0b",
            "rca_vi": "Hết thời gian chờ phần tử xuất hiện trong DOM hoặc đạt trạng thái sẵn sàng tương tác.",
            "rca_en": "Locator timed out: element did not reach ready/visible state within timeout threshold.",
            "action_vi": "Thay thế waitFor cứng bằng smart wait động hoặc kiểm tra xem selector có bị thay đổi sau bản cập nhật không."
        }
    elif any(k in r_lower for k in ("intercepted", "another element", "obscures", "not clickable")):
        return {
            "category": "CLICK_INTERCEPTED",
            "badge_color": "#ec4899",
            "rca_vi": "Thao tác click bị chặn bởi phần tử khác (như modal quảng cáo, backdrop hoặc toast notification).",
            "rca_en": "Click intercepted: another DOM overlay or animation obscured the target element.",
            "action_vi": "Đảm bảo đã đóng các modal hoặc chờ animation kết thúc trước khi tương tác."
        }
    elif any(k in r_lower for k in ("404", "500", "502", "503", "net::err", "connection refused", "econnrefused")):
        return {
            "category": "NETWORK_BACKEND_FAULT",
            "badge_color": "#8b5cf6",
            "rca_vi": "Máy chủ backend hoặc endpoint API phản hồi mã lỗi HTTP hoặc từ chối kết nối mạng.",
            "rca_en": "Network/Backend fault: target server returned an error status or connection was refused.",
            "action_vi": "Kiểm tra xem backend service / mock server đã khởi động và hoạt động bình thường chưa."
        }
    else:
        return {
            "category": "UNHANDLED_EXCEPTION",
            "badge_color": "#64748b",
            "rca_vi": "Gặp ngoại lệ không mong muốn trong quá trình thực thi kịch bản kiểm thử.",
            "rca_en": "Unhandled exception encountered during test script execution flow.",
            "action_vi": "Kiểm tra stack trace chi tiết bên dưới để xác định hàm bị lỗi."
        }


def read_code_frame(file_path: str, line_no_str: str, window: int = 3) -> Optional[List[Dict[str, Any]]]:
    """Reads lines from source file around failing line number."""
    if not file_path or file_path == "UnknownFile":
        return None

    abs_path = os.path.abspath(file_path) if os.path.isabs(file_path) else os.path.abspath(os.path.join(REPO_ROOT, file_path))
    if not os.path.isfile(abs_path):
        return None

    try:
        line_num = int(line_no_str)
    except (ValueError, TypeError):
        return None

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception:
        return None

    start = max(0, line_num - window - 1)
    end = min(len(all_lines), line_num + window)

    frame = []
    for idx in range(start, end):
        frame.append({
            "line": idx + 1,
            "text": all_lines[idx].rstrip("\r\n"),
            "is_target": (idx + 1 == line_num)
        })
    return frame


def generate_failure_autopsy_html(failures: List[Dict[str, Any]], xml_path: str = "", output_path: Optional[str] = None) -> str:
    """Generates the interactive single-file HTML Failure Autopsy report."""
    timestamp = datetime.now().isoformat()
    total_failures = len(failures)
    target_xml = xml_path or "JUnit Report"

    autopsy_cards = []
    for idx, f in enumerate(failures, 1):
        tc_name = html_lib.escape(f.get("tc", f"TestCase_{idx}"))
        tc_time = html_lib.escape(f.get("time", "0.0s"))
        reason = html_lib.escape(f.get("reason", "Unknown failure"))
        failed_locs = f.get("failed_at", [])
        loc_str = html_lib.escape(", ".join(failed_locs) if failed_locs else "Unknown")
        f_file = f.get("file", "")
        f_line = f.get("line", "")

        classification = classify_failure(f.get("reason", ""))
        badge_color = classification["badge_color"]
        category = classification["category"]

        code_frame = read_code_frame(f_file, f_line)
        code_frame_html = ""
        if code_frame:
            rows = []
            for row in code_frame:
                line_bg = "background: #ef444422; border-left: 3px solid #ef4444;" if row["is_target"] else ""
                num_color = "#ef4444" if row["is_target"] else "#64748b"
                escaped_text = html_lib.escape(row["text"])
                rows.append(f"""
                <tr style="{line_bg}">
                    <td style="color:{num_color}; width:40px; text-align:right; padding-right:12px; user-select:none; font-family:monospace;">{row['line']}</td>
                    <td style="font-family:monospace; white-space:pre;">{escaped_text}</td>
                </tr>
                """)
            code_frame_html = f"""
            <div class="code-frame-box">
                <div class="code-frame-header">📄 {html_lib.escape(f_file)}:{f_line}</div>
                <table class="code-table">
                    {''.join(rows)}
                </table>
            </div>
            """

        autopsy_cards.append(f"""
        <div class="autopsy-card">
            <div class="autopsy-header">
                <span class="tc-title">#{idx} {tc_name}</span>
                <span class="badge" style="background:{badge_color}22; color:{badge_color}; border:1px solid {badge_color}44;">{category}</span>
                <span class="tc-time">⏱️ {tc_time}</span>
            </div>

            <div class="rca-box">
                <div style="font-weight: 700; margin-bottom: 0.25rem; color: #f8fafc;">💡 Chẩn Đoán Nguyên Nhân Gốc (Root Cause Analysis):</div>
                <div style="color: #cbd5e1; font-size: 0.9rem; margin-bottom: 0.25rem;">🇻🇳 {classification['rca_vi']}</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.5rem;">🇬🇧 {classification['rca_en']}</div>
                <div style="font-size: 0.85rem; color: #38bdf8; background: #0f172a; padding: 0.5rem 0.75rem; border-radius: 6px;">
                    🛠️ <b>Hành động khắc phục:</b> {classification['action_vi']}
                </div>
            </div>

            <div class="raw-cause">
                <b>Nguyên văn lỗi:</b> <code>{reason}</code>
            </div>

            {code_frame_html}

            <div class="location-bar">
                📍 <b>Vị trí stack trace:</b> {loc_str}
            </div>
        </div>
        """)

    cards_html = "\n".join(autopsy_cards)

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Synapse Hub — Interactive Failure Autopsy Report</title>
    <style>
        :root {{
            --bg: #0b0f19;
            --card-bg: #151d2f;
            --border: #23314d;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --danger: #ef4444;
            --warning: #f59e0b;
            --primary: #38bdf8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            padding: 2rem 1.5rem;
            line-height: 1.5;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        .brand-title {{ font-size: 1.5rem; font-weight: 800; display: flex; align-items: center; gap: 0.5rem; }}
        .badge-fail {{
            background: #ef444422; color: #ef4444; font-size: 0.85rem; font-weight: 700;
            padding: 0.25rem 0.75rem; border-radius: 9999px; border: 1px solid #ef444444;
        }}
        .autopsy-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        }}
        .autopsy-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }}
        .tc-title {{ font-size: 1.15rem; font-weight: 700; color: #f8fafc; }}
        .badge {{ font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.5rem; border-radius: 4px; }}
        .tc-time {{ color: var(--text-sub); font-size: 0.85rem; margin-left: auto; }}
        .rca-box {{
            background: #1e293b;
            border-left: 4px solid var(--primary);
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .raw-cause {{
            background: #0f172a;
            padding: 0.75rem 1rem;
            border-radius: 6px;
            font-size: 0.85rem;
            margin-bottom: 1rem;
            color: #f1f5f9;
        }}
        .raw-cause code {{ color: #f87171; font-family: monospace; }}
        .code-frame-box {{
            background: #0a0f1d;
            border: 1px solid var(--border);
            border-radius: 8px;
            margin-bottom: 1rem;
            overflow-x: auto;
        }}
        .code-frame-header {{
            background: #131c31;
            padding: 0.4rem 0.8rem;
            font-size: 0.8rem;
            color: var(--text-sub);
            border-bottom: 1px solid var(--border);
        }}
        .code-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; padding: 0.5rem; }}
        .code-table td {{ padding: 0.2rem 0.5rem; }}
        .location-bar {{ font-size: 0.85rem; color: var(--text-sub); }}
        footer {{
            margin-top: 3rem;
            border-top: 1px solid var(--border);
            padding-top: 1.5rem;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-sub);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand-title">
                🔍 Failure Autopsy & RCA
                <span class="badge-fail">{total_failures} FAILED</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-sub); text-align: right;">
                <div>Target: {html_lib.escape(os.path.basename(target_xml))}</div>
                <div>{timestamp.split('T')[0]} {timestamp.split('T')[1][:8] if 'T' in timestamp else ''}</div>
            </div>
        </header>

        {cards_html}

        <footer>
            <div>Synapse Hub — Failure Autopsy & Healing Sentinel</div>
            <div style="margin-top: 0.25rem;">Tác giả: <b>Thế Vị (@TeeVee98)</b> | Giấy phép: MIT License</div>
        </footer>
    </div>
</body>
</html>
"""
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    return html_content
