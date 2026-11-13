#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Pocock Grilling Primitive & Requirements Interrogation Engine (Matt Pocock Pattern)
-----------------------------------------------------------------------------------
Calculates the prerequisite decision frontier for ambiguous user stories.
Batches structured multiple-choice questions with explicit (Recommended) defaults,
strictly adhering to the Fact/Decision boundary (never asking for facts ascertainable
directly from the codebase).

Reference:
  - Matt Pocock (The Grilling Primitive: Frontier Decision Interrogation).
  - Synapse-Hub Subsystem 6: Section 6.7 of agent_skill_training_analysis.md.
"""

import sys
import re
import json
import argparse
from typing import List, Dict, Any

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


class PocockGriller:
    """Interrogates user stories along the prerequisite decision frontier."""

    def __init__(self, target_framework: str = "Playwright_TS"):
        self.target_framework = target_framework

    def generate_frontier_questions(self, story_text: str, grill_me: bool = False) -> List[Dict[str, Any]]:
        """
        Analyzes requirements text and returns batched questions for ask_question.
        Only generates questions for true decision forks, never for discoverable codebase facts.
        In grill_me mode (Matt Pocock pattern), aggressively probes boundary, race, and failure forks.
        """
        questions = []

        # 1. Scope & Execution Boundary
        questions.append({
            "question": "Phạm vi kiểm thử tự động (Execution Scope): Cấp độ kiểm thử mong muốn cho user story này là gì?",
            "is_multi_select": False,
            "options": [
                "(Recommended) End-to-End (E2E) UI Automation kết hợp Clean POM và xác thực API payload",
                "API Functional Testing độc lập (không tương tác giao diện browser)",
                "Smoke Test kiểm tra luồng chính (Happy Path) tối giản"
            ]
        })

        # 2. Test Data Lifecycle & Idempotency
        if not re.search(r"\b(?:mock|stub|seed)\b", story_text, re.IGNORECASE):
            questions.append({
                "question": "Quản lý dữ liệu kiểm thử (Test Data Strategy): Chiến lược sinh và dọn dẹp dữ liệu nào được áp dụng?",
                "is_multi_select": False,
                "options": [
                    "(Recommended) Tự động sinh mã duy nhất (BasePage.uniqueCode('AUTO_')) kèm Teardown Cleanup tự động",
                    "Dùng tài khoản / dữ liệu tĩnh cấu hình sẵn trong Profile / .env",
                    "Network Mocking: Giả lập API response (không tạo dữ liệu thật trên DB)"
                ]
            })

        # 3. Assertion Boundary & Negative Scenarios
        questions.append({
            "question": "Bao phủ kịch bản biên & bất biến (Assertion Frontier): Cần kiểm thử các trường hợp nào ngoài Happy Path?",
            "is_multi_select": True,
            "options": [
                "(Recommended) Kiểm tra validation form khi bỏ trống các trường bắt buộc",
                "(Recommended) Kiểm tra trạng thái nút Submit / Save khi form chưa hợp lệ (Disabled State)",
                "Kiểm tra timeout hoặc mạng chập chờn (Chaos network fault injection)",
                "Kiểm tra quyền truy cập trái phép (Unauthorized / Forbidden 403)"
            ]
        })

        # 4. Matt Pocock Grilling Mode (Aggressive Boundary & Race Probing)
        if grill_me:
            questions.append({
                "question": "Xung đột đồng thời & Thao tác kép (Pocock Concurrency Frontier): Xử lý ra sao khi xảy ra Double-Submit hoặc 2 user cùng sửa 1 bản ghi?",
                "is_multi_select": False,
                "options": [
                    "(Recommended) Idempotency Token / Khóa nút thao tác và trả về thông báo lỗi lạc quan (Optimistic Lock 409)",
                    "Cho phép ghi đè tự do theo thứ tự thời gian (Last Write Wins)",
                    "Xếp hàng đợi tuần tự (Queue sequential execution)"
                ]
            })
            questions.append({
                "question": "Dữ liệu dị dạng & Biên tải (Pocock Fuzzing Frontier): Hành vi mong đợi khi nhận payload rỗng, quá giới hạn byte, hoặc chứa ký tự đặc biệt?",
                "is_multi_select": False,
                "options": [
                    "(Recommended) Chặn tại Client Validation kèm Schema Rejection 400 Bad Request",
                    "Cắt ngắn dữ liệu tự động (Silent Truncation) và lưu phần hợp lệ",
                    "Cho phép lưu nguyên vẹn vào DB mà không áp dụng bộ lọc ký tự"
                ]
            })

        return questions


def main():
    parser = argparse.ArgumentParser(description="Pocock Grilling Primitive Engine")
    parser.add_argument("story", nargs="?", default="", help="User story or requirement text")
    parser.add_argument("--grill-me", action="store_true", help="Explicit grill-me mode (Matt Pocock pattern)")
    parser.add_argument("--json", action="store_true", help="Output questions in JSON format")
    args = parser.parse_args()

    story_text = args.story or "User Story: As a registered user, I want to approve invoices with attached receipts."

    griller = PocockGriller()
    questions = griller.generate_frontier_questions(story_text, grill_me=args.grill_me)

    if args.json:
        print(json.dumps({"story": story_text, "questions": questions}, indent=2))
        return 0

    print("\n" + "=" * 70)
    print("  POCOCK GRILLING PRIMITIVE (PREREQUISITE DECISION FRONTIER)")
    print("=" * 70)
    print(f"Target Requirement: {story_text}\n")
    print(f"Generated {len(questions)} batched decision questions with recommended defaults:\n")

    for idx, q in enumerate(questions, 1):
        print(f"Q{idx}: {q['question']}")
        for opt in q["options"]:
            print(f"   • {opt}")
        print()
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
