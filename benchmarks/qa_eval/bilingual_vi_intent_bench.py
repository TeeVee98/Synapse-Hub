#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
benchmarks/qa_eval/bilingual_vi_intent_bench.py — Stratified Vietnamese & Mixed VI-EN Routing Benchmark
-------------------------------------------------------------------------------------------------------
Deterministic CLI benchmark evaluating >= 120 stratified prompts across:
  1. Accented Vietnamese
  2. Unaccented Vietnamese
  3. Telex Vietnamese
  4. Teencode / Shorthand Vietnamese
  5. Mixed VI-EN Code-Switched Prompts
  6. SetFit-Style Contrastive Hard-Negative & Abstention Pairs
  7. Homonym Traps (crypto/LLM token, Excel+CSV batch, app form validation)

Produces empirical Top-1 Accuracy, Macro Precision/Recall, Abstention Accuracy,
Homonym FPR, Expected Calibration Error (ECE), and p95 latency (ms).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.core.bilingual_intent_normalizer import normalize_bilingual_intent
from tools.core.bm25_retriever import compute_expected_calibration_error
from tools.core.skill_router import evaluate_skill_first_trigger, get_utterance_router_index


@dataclass(frozen=True)
class BilingualBenchReportDTO:
    """Empirical benchmark metrics across stratified Vietnamese and mixed VI-EN prompts."""

    total_cases: int
    top1_accuracy_pct: float
    macro_precision_pct: float
    macro_recall_pct: float
    abstention_accuracy_pct: float
    homonym_fpr_pct: float
    expected_calibration_error: float
    p95_latency_ms: float
    passed_gate: bool


@dataclass(frozen=True)
class BenchCase:
    """Single stratified evaluation prompt with expected skill or abstention/homonym guard."""

    case_id: str
    stratum: str
    prompt: str
    expected_skill: Optional[str]
    forbidden_tokens: Tuple[str, ...] = ()
    forbidden_skills: Tuple[str, ...] = ()


# 132 Stratified Vietnamese & Mixed VI-EN Evaluation Cases
BENCHMARK_CASES: Tuple[BenchCase, ...] = (
    # --- Stratum 1: Accented Vietnamese (32) ---
    BenchCase("ACC-01", "accented_vi", "Tạo ma trận kiểm thử API biên từ đặc tả OpenAPI Swagger", "api-spec-to-e2e-matrix"),
    BenchCase("ACC-02", "accented_vi", "Sinh bộ test case kiểm tra endpoint và schema từ file OpenAPI", "api-spec-to-e2e-matrix"),
    BenchCase("ACC-03", "accented_vi", "Giả lập phản hồi lỗi 500 cho truy vấn GraphQL và chặn yêu cầu mạng HTTP", "api-network-mocking-interception"),
    BenchCase("ACC-04", "accented_vi", "Chặn lưu lượng mạng giả lập API trả về lỗi 503 khi test giao diện", "api-network-mocking-interception"),
    BenchCase("ACC-05", "accented_vi", "Triển khai kiểm thử hợp đồng dịch vụ CDC với Pact giữa consumer và provider", "consumer-driven-contract-testing"),
    BenchCase("ACC-06", "accented_vi", "Đo chỉ số hiệu năng Core Web Vitals LCP CLS INP qua CDP", "web-vitals-and-performance-profiler"),
    BenchCase("ACC-07", "accented_vi", "Kiểm tra vì sao trang web tải chậm bị giật bố cục CLS và LCP quá cao", "web-vitals-and-performance-profiler"),
    BenchCase("ACC-08", "accented_vi", "Chạy kiểm thử chịu tải áp lực SLA cho backend bằng k6 và JMeter", "backend-load-and-stress-patterns"),
    BenchCase("ACC-09", "accented_vi", "Thiết kế kịch bản load test và stress test bằng Locust cho API", "backend-load-and-stress-patterns"),
    BenchCase("ACC-10", "accented_vi", "Chạy kiểm tra bảo mật động OWASP Top 10 BOLA IDOR và rò rỉ token", "security-dast-sentinel"),
    BenchCase("ACC-11", "accented_vi", "Quét lỗ hổng tiêm mã SQL injection và lỗi phân quyền bảo mật API", "security-dast-sentinel"),
    BenchCase("ACC-12", "accented_vi", "Kiểm tra trợ năng WCAG 2.2 nhãn ARIA cho trình đọc màn hình và điều hướng bàn phím", "wcag-audit-patterns"),
    BenchCase("ACC-13", "accented_vi", "Rà soát lỗi thiếu nhãn ARIA độ tương phản màu sắc và thứ tự phím Tab", "wcag-audit-patterns"),
    BenchCase("ACC-14", "accented_vi", "Quản lý phiên đăng nhập cookie storageState và làm mới JWT token", "auth-session-and-cookie-manager"),
    BenchCase("ACC-15", "accented_vi", "Sửa lỗi người dùng cứ bị văng ra khỏi phiên đăng nhập khi hết hạn cookie", "auth-session-and-cookie-manager"),
    BenchCase("ACC-16", "accented_vi", "Xây dựng lớp trang Clean POM kế thừa BasePage theo kiến trúc phẳng", "clean-pom-crafter"),
    BenchCase("ACC-17", "accented_vi", "Chạy bộ test Katalon Studio headless qua dòng lệnh CLI và Gradle", "katalon-cli-runner"),
    BenchCase("ACC-18", "accented_vi", "Xây dựng kiểm thử di động Screen Object Model SOM với Appium cho iOS Android", "mobile-appium-som"),
    BenchCase("ACC-19", "accented_vi", "Viết luồng kiểm thử di động YAML bằng Maestro và Detox cho React Native", "mobile-maestro-detox-patterns"),
    BenchCase("ACC-20", "accented_vi", "Chuyển file feature Gherkin BDD thành ma trận kiểm thử và báo cáo thiếu hụt", "gherkin-to-suite"),
    BenchCase("ACC-21", "accented_vi", "Thiết kế ma trận kiểm thử thủ công theo rủi ro RBT và xuất file Excel", "rbt-manual-testing"),
    BenchCase("ACC-22", "accented_vi", "Rà soát và phản biện tài liệu đặc tả yêu cầu BRD user story trước khi lập trình", "review-spec"),
    BenchCase("ACC-23", "accented_vi", "Phát hiện bài test chập chờn lúc pass lúc fail tính điểm flaky và đưa vào cách ly", "flaky-test-sentinel-and-quarantine"),
    BenchCase("ACC-24", "accented_vi", "Điều tra nguyên nhân kịch bản kiểm thử chạy không ổn định lúc được lúc không", "flaky-test-sentinel-and-quarantine"),
    BenchCase("ACC-25", "accented_vi", "Tự sửa bộ chọn locator bị hỏng bằng so sánh ngữ nghĩa AOM ưu tiên Role và TestId", "self-healing-locator"),
    BenchCase("ACC-26", "accented_vi", "Khám nghiệm lỗi kiểm thử từ JUnit XML ảnh chụp màn hình và phân loại nguyên nhân", "failure-autopsy-and-healing"),
    BenchCase("ACC-27", "accented_vi", "Chạy kiểm thử hồi quy hình ảnh so sánh pixel screenshot với mặt nạ che vùng động", "visual-regression-sentinel"),
    BenchCase("ACC-28", "accented_vi", "Kiểm tra dữ liệu database SQL và dọn dẹp fixture teardown sau khi test", "db-state-verifier-and-seeder"),
    BenchCase("ACC-29", "accented_vi", "Kiểm tra cấu trúc schema file Excel CSV và PDF tải về đúng định dạng", "file-and-report-validator"),
    BenchCase("ACC-30", "accented_vi", "Tạo dữ liệu giả kiểm thử tổng hợp có mã duy nhất theo thời gian cho QA", "synthetic-test-data-generator"),
    BenchCase("ACC-31", "accented_vi", "Tạo quy trình GitHub Actions YAML cho bộ kiểm thử tự động và CI CD", "github-actions-templates"),
    BenchCase("ACC-32", "accented_vi", "Tạo bản thiết kế pipeline GitLab CI trong .gitlab-ci.yml cho Playwright và Pytest", "gitlab-ci-templates"),

    # --- Stratum 2: Unaccented Vietnamese (24) ---
    BenchCase("UNACC-01", "unaccented_vi", "Tao ma tran kiem thu api tu dac ta OpenAPI", "api-spec-to-e2e-matrix"),
    BenchCase("UNACC-02", "unaccented_vi", "Gia lap phan hoi loi 500 cho truy van GraphQL va chan mang HTTP", "api-network-mocking-interception"),
    BenchCase("UNACC-03", "unaccented_vi", "Kiem tra vi sao trang web tai cham bi giat bo cuc cls va lcp qua cao", "web-vitals-and-performance-profiler"),
    BenchCase("UNACC-04", "unaccented_vi", "Do chi so hieu nang Core Web Vitals LCP CLS INP qua CDP", "web-vitals-and-performance-profiler"),
    BenchCase("UNACC-05", "unaccented_vi", "Chay kiem thu chiu tai SLA cho backend bang k6 va JMeter", "backend-load-and-stress-patterns"),
    BenchCase("UNACC-06", "unaccented_vi", "Chay kiem tra bao mat dong OWASP Top 10 BOLA IDOR va ro ri token", "security-dast-sentinel"),
    BenchCase("UNACC-07", "unaccented_vi", "Ra soat loi thieu nhan ARIA cho trinh doc man hinh va phim Tab WCAG", "wcag-audit-patterns"),
    BenchCase("UNACC-08", "unaccented_vi", "Sua loi rot phien dang nhap cookie storageState va lam moi JWT token", "auth-session-and-cookie-manager"),
    BenchCase("UNACC-09", "unaccented_vi", "Chuyen file feature Gherkin BDD thanh ma tran kiem thu", "gherkin-to-suite"),
    BenchCase("UNACC-10", "unaccented_vi", "Thiet ke ma tran kiem thu thu cong theo rui ro RBT va xuat Excel", "rbt-manual-testing"),
    BenchCase("UNACC-11", "unaccented_vi", "Phat hien bai test chap chon luc pass luc fail va dua vao cach ly flaky", "flaky-test-sentinel-and-quarantine"),
    BenchCase("UNACC-12", "unaccented_vi", "Tu sua bo chon locator bi hong bang so sanh ngu nghia AOM", "self-healing-locator"),
    BenchCase("UNACC-13", "unaccented_vi", "Kham nghiem loi kiem thu tu JUnit XML va anh chup man hinh", "failure-autopsy-and-healing"),
    BenchCase("UNACC-14", "unaccented_vi", "Kiem tra du lieu database va don dep fixture sau khi test", "db-state-verifier-and-seeder"),
    BenchCase("UNACC-15", "unaccented_vi", "Kiem tra cau truc file Excel va CSV tai ve", "file-and-report-validator"),
    BenchCase("UNACC-16", "unaccented_vi", "Tao du lieu gia kiem thu tong hop tranh trung lap DB cho QA", "synthetic-test-data-generator"),
    BenchCase("UNACC-17", "unaccented_vi", "Xay dung lop trang Clean POM ke thua BasePage cho Playwright", "clean-pom-crafter"),
    BenchCase("UNACC-18", "unaccented_vi", "Chay bo test Katalon Studio headless qua CLI va Gradle", "katalon-cli-runner"),
    BenchCase("UNACC-19", "unaccented_vi", "Viet kiem thu Bats cho kich ban bash shell va CLI", "bats-testing-patterns"),
    BenchCase("UNACC-20", "unaccented_vi", "Xay dung kiem thu di dong Screen Object Model SOM voi Appium", "mobile-appium-som"),
    BenchCase("UNACC-21", "unaccented_vi", "Viet luong kiem thu di dong YAML bang Maestro va Detox", "mobile-maestro-detox-patterns"),
    BenchCase("UNACC-22", "unaccented_vi", "Tao Jenkins Declarative Pipeline Jenkinsfile cho kiem thu song song", "jenkins-pipeline-templates"),
    BenchCase("UNACC-23", "unaccented_vi", "Phan tich ban kinh anh huong blast radius bang do thi goi ham AST", "graphify-impact-analyzer"),
    BenchCase("UNACC-24", "unaccented_vi", "Toi uu ngan sach token ngu canh va nen log terminal dai", "token-and-context-optimizer"),

    # --- Stratum 3: Telex Vietnamese (16) ---
    BenchCase("TELEX-01", "telex_vi", "ddawng nhaapj bi rot phien cookie het han", "auth-session-and-cookie-manager"),
    BenchCase("TELEX-02", "telex_vi", "kieemr tra bao mat OWASP Top 10 va BOLA IDOR", "security-dast-sentinel"),
    BenchCase("TELEX-03", "telex_vi", "taoj ma tran kiem thu API tu dac ta OpenAPI Swagger", "api-spec-to-e2e-matrix"),
    BenchCase("TELEX-04", "telex_vi", "gia lap mang va chan phan hoi loi 500 GraphQL", "api-network-mocking-interception"),
    BenchCase("TELEX-05", "telex_vi", "ddo chi so Core Web Vitals LCP CLS INP qua CDP", "web-vitals-and-performance-profiler"),
    BenchCase("TELEX-06", "telex_vi", "kieemr tra tro nang WCAG 2.2 va nhan ARIA cho ban phim", "wcag-audit-patterns"),
    BenchCase("TELEX-07", "telex_vi", "phat hieenj test chap chon luc pass luc fail va cach ly flaky", "flaky-test-sentinel-and-quarantine"),
    BenchCase("TELEX-08", "telex_vi", "tu suwar locator bi hong bang so sanh ngu nghia AOM", "self-healing-locator"),
    BenchCase("TELEX-09", "telex_vi", "kieemr tra duwx lieeuj database va don dep fixture sau khi test", "db-state-verifier-and-seeder"),
    BenchCase("TELEX-10", "telex_vi", "kieemr tra cau truc file Excel CSV PDF tai ve", "file-and-report-validator"),
    BenchCase("TELEX-11", "telex_vi", "chuyeenr file feature Gherkin BDD thanh ma tran kiem thu", "gherkin-to-suite"),
    BenchCase("TELEX-12", "telex_vi", "thieets ke ma tran kiem thu thu cong RBT va xuaats Excel", "rbt-manual-testing"),
    BenchCase("TELEX-13", "telex_vi", "chayj kiem thu chiu tai backend bang k6 va JMeter", "backend-load-and-stress-patterns"),
    BenchCase("TELEX-14", "telex_vi", "taoj pipeline GitHub Actions YAML cho bo test Playwright", "github-actions-templates"),
    BenchCase("TELEX-15", "telex_vi", "taoj duwx lieeuj gia kiem thu tong hop idempotent cho QA", "synthetic-test-data-generator"),
    BenchCase("TELEX-16", "telex_vi", "kham nghieemj looxi kiem thu tu JUnit XML va screenshot", "failure-autopsy-and-healing"),

    # --- Stratum 4: Teencode / Shorthand Vietnamese (14) ---
    BenchCase("SHORT-01", "shorthand_vi", "ktra chi so Core Web Vitals LCP CLS trang web cham qua", "web-vitals-and-performance-profiler"),
    BenchCase("SHORT-02", "shorthand_vi", "ktra loi thieu nhan ARIA WCAG va ban phim Tab", "wcag-audit-patterns"),
    BenchCase("SHORT-03", "shorthand_vi", "ktra du lieu database va don dep fixture sau khi test", "db-state-verifier-and-seeder"),
    BenchCase("SHORT-04", "shorthand_vi", "ktra cau truc file Excel CSV tai ve co dung ko", "file-and-report-validator"),
    BenchCase("SHORT-05", "shorthand_vi", "ktra bao mat OWASP DAST va lo hong IDOR", "security-dast-sentinel"),
    BenchCase("SHORT-06", "shorthand_vi", "ktra test flaky luc pass luc fail ko on dinh nhu trc", "flaky-test-sentinel-and-quarantine"),
    BenchCase("SHORT-07", "shorthand_vi", "ktra phien dang nhap cookie storageState bi rot ko dc", "auth-session-and-cookie-manager"),
    BenchCase("SHORT-08", "shorthand_vi", "ktra hop dong Pact CDC giua consumer va provider", "consumer-driven-contract-testing"),
    BenchCase("SHORT-09", "shorthand_vi", "ktra visual regression pixel diff screenshot co bi lech ko", "visual-regression-sentinel"),
    BenchCase("SHORT-10", "shorthand_vi", "ktra ma tran API tu dac ta OpenAPI Swagger", "api-spec-to-e2e-matrix"),
    BenchCase("SHORT-11", "shorthand_vi", "ktra gia lap mang HTTP GraphQL tra loi 500", "api-network-mocking-interception"),
    BenchCase("SHORT-12", "shorthand_vi", "ktra chiu tai backend bang k6 JMeter co bi qua tai ko", "backend-load-and-stress-patterns"),
    BenchCase("SHORT-13", "shorthand_vi", "ktra bo chon locator AOM bi hong ko tim thay nut", "self-healing-locator"),
    BenchCase("SHORT-14", "shorthand_vi", "ktra bao mat skill AI agent va cau hinh MCP SkillSpector", "skillspector-security-guard"),

    # --- Stratum 5: Mixed VI-EN Code-Switched & Meta-Workflows (20) ---
    BenchCase("MIX-01", "mixed_vi_en", "Generate ma trận API test boundary từ OpenAPI spec", "api-spec-to-e2e-matrix"),
    BenchCase("MIX-02", "mixed_vi_en", "Mock HTTP GraphQL routes và inject 503 chaos faults", "api-network-mocking-interception"),
    BenchCase("MIX-03", "mixed_vi_en", "Heal broken Playwright locator dùng semantic AOM diffing", "self-healing-locator"),
    BenchCase("MIX-04", "mixed_vi_en", "Audit WCAG 2.2 accessibility ARIA labels và keyboard navigation", "wcag-audit-patterns"),
    BenchCase("MIX-05", "mixed_vi_en", "Profile Core Web Vitals LCP CLS INP bằng Chrome CDP", "web-vitals-and-performance-profiler"),
    BenchCase("MIX-06", "mixed_vi_en", "Run k6 và JMeter backend load stress test đo p95 SLA", "backend-load-and-stress-patterns"),
    BenchCase("MIX-07", "mixed_vi_en", "Scan OWASP Top 10 DAST BOLA IDOR và security headers", "security-dast-sentinel"),
    BenchCase("MIX-08", "mixed_vi_en", "Refactor raw selectors thành Clean POM Page Class kế thừa BasePage", "clean-pom-crafter"),
    BenchCase("MIX-09", "mixed_vi_en", "Verify Pact consumer-driven contract giữa frontend và backend", "consumer-driven-contract-testing"),
    BenchCase("MIX-10", "mixed_vi_en", "Seed SQL database test fixtures và chạy teardown cleanup", "db-state-verifier-and-seeder"),
    BenchCase("MIX-11", "mixed_vi_en", "Validate downloaded Excel XLSX CSV PDF report schema", "file-and-report-validator"),
    BenchCase("MIX-12", "mixed_vi_en", "Quarantine flaky tests chạy non-deterministic trên CI", "flaky-test-sentinel-and-quarantine"),
    BenchCase("MIX-13", "mixed_vi_en", "Triage JUnit XML failure autopsy và screenshots trên CI", "failure-autopsy-and-healing"),
    BenchCase("MIX-14", "mixed_vi_en", "Run visual regression pixel diff masking timestamps", "visual-regression-sentinel"),
    BenchCase("MIX-15", "mixed_vi_en", "Write Bats unit tests cho bash shell CLI scripts", "bats-testing-patterns"),
    BenchCase("MIX-16", "mixed_vi_en", "Configure GitHub Actions YAML matrix sharding cho Pytest", "github-actions-templates"),
    BenchCase("MIX-17", "mixed_vi_en", "Configure GitLab CI .gitlab-ci.yml runner cho Playwright", "gitlab-ci-templates"),
    BenchCase("MIX-18", "mixed_vi_en", "/super-plan Thiết kế kiến trúc bộ định tuyến có hiệu chuẩn", "super-plan"),
    BenchCase("MIX-19", "mixed_vi_en", "/solo Thực thi tuần tự các cột mốc trong implementation_plan.md", "solo"),
    BenchCase("MIX-20", "mixed_vi_en", "/review Đối chiếu diff và biên lai HMAC sau khi chạy /solo", "review"),

    # --- Stratum 6: SetFit Contrastive Hard-Negative & Abstention Pairs (16) ---
    BenchCase("NEG-01", "hard_negative", "Update copyright year in footer banner", None),
    BenchCase("NEG-02", "hard_negative", "Rename local variable foo to bar in helper", None),
    BenchCase("NEG-03", "hard_negative", "How does Clean POM work?", None),
    BenchCase("NEG-04", "hard_negative", "Phần xử lý hôm qua là gì vậy?", None),
    BenchCase("NEG-05", "hard_negative", "Chức năng này hoạt động sao?", None),
    BenchCase("NEG-06", "hard_negative", "Clean POM la gi?", None),
    BenchCase("NEG-07", "hard_negative", "Tai sao test bi cham?", None),
    BenchCase("NEG-08", "hard_negative", "Làm lại giùm chỗ xử lý hôm qua cho mượt hơn đi", None),
    BenchCase("NEG-09", "hard_negative", "Nó cứ giật giật khó chịu quá", None),
    BenchCase("NEG-10", "hard_negative", "No cu giat giat kho chiu qua", None),
    BenchCase("NEG-11", "hard_negative", "Chỉnh giúp phần giỏ hàng bị đơ với", None),
    BenchCase("NEG-12", "hard_negative", "Don dep giao dien cho sach se hon", None),
    BenchCase("NEG-13", "hard_negative", "May in bi ket giay hoai luon", None),
    BenchCase("NEG-14", "hard_negative", "Redo that broken part from yesterday to make it smoother", None),
    BenchCase("NEG-15", "hard_negative", "It keeps glitching and acting weird", None),
    BenchCase("NEG-16", "hard_negative", "Make the whole thing faster and cleaner please", None),

    # --- Stratum 7: Homonym Traps (10) ---
    BenchCase(
        "HOM-01", "homonym_trap",
        "Sửa lỗi hiển thị giá token crypto trên bảng giá",
        None,
        forbidden_tokens=("auth", "security", "jwt"),
        forbidden_skills=("auth-session-and-cookie-manager", "security-dast-sentinel"),
    ),
    BenchCase(
        "HOM-02", "homonym_trap",
        "Cap nhat bang gia coin va token crypto tren giao dien",
        None,
        forbidden_tokens=("auth", "security", "jwt"),
        forbidden_skills=("auth-session-and-cookie-manager", "security-dast-sentinel"),
    ),
    BenchCase(
        "HOM-03", "homonym_trap",
        "Sửa hàm kiểm tra dữ liệu đầu vào form đăng ký",
        None,
        forbidden_skills=("synthetic-test-data-generator", "db-state-verifier-and-seeder"),
    ),
    BenchCase(
        "HOM-04", "homonym_trap",
        "Sua ham validate dau vao form dang ky nguoi dung",
        None,
        forbidden_skills=("synthetic-test-data-generator", "db-state-verifier-and-seeder"),
    ),
    BenchCase(
        "HOM-05", "homonym_trap",
        "Xuất báo cáo Excel và CSV cùng lúc",
        "file-and-report-validator",
        forbidden_tokens=("race", "concurrency", "deadlock"),
    ),
    BenchCase(
        "HOM-06", "homonym_trap",
        "Xuat bao cao Excel va CSV cung luc cho ke toan",
        "file-and-report-validator",
        forbidden_tokens=("race", "concurrency", "deadlock"),
    ),
    BenchCase(
        "HOM-07", "homonym_trap",
        "Chỉnh màu design token CSS trên thanh tiêu đề",
        None,
        forbidden_tokens=("auth", "security", "jwt"),
        forbidden_skills=("auth-session-and-cookie-manager", "security-dast-sentinel"),
    ),
    BenchCase(
        "HOM-08", "homonym_trap",
        "Dọn dẹp khoảng trắng thừa trên giao diện trang chủ",
        None,
        forbidden_tokens=("teardown", "cleanup"),
        forbidden_skills=("db-state-verifier-and-seeder",),
    ),
    BenchCase(
        "HOM-09", "homonym_trap",
        "Hiển thị số lượng token crypto trong ví wallet trading",
        None,
        forbidden_tokens=("auth", "security", "jwt"),
        forbidden_skills=("auth-session-and-cookie-manager", "security-dast-sentinel"),
    ),
    BenchCase(
        "HOM-10", "homonym_trap",
        "Sửa lỗi kiểm tra dữ liệu đầu vào form đăng ký tài khoản",
        None,
        forbidden_skills=("synthetic-test-data-generator", "db-state-verifier-and-seeder"),
    ),
)


def _compute_macro_pr(
    tp: Dict[str, int], fp: Dict[str, int], fn: Dict[str, int]
) -> Tuple[float, float]:
    """Computes macro-averaged precision and recall percentages across positive classes."""
    classes = sorted(set(tp.keys()) | set(fn.keys()))
    if not classes:
        return 100.0, 100.0
    precisions = [
        (tp[c] / (tp[c] + fp[c])) if (tp[c] + fp[c]) > 0 else 0.0 for c in classes
    ]
    recalls = [
        (tp[c] / (tp[c] + fn[c])) if (tp[c] + fn[c]) > 0 else 0.0 for c in classes
    ]
    return round((sum(precisions) / len(classes)) * 100.0, 2), round(
        (sum(recalls) / len(classes)) * 100.0, 2
    )


def _evaluate_homonym_trap(case: BenchCase, pred_skill: Optional[str]) -> bool:
    """Returns True if a homonym trap suffered a false-positive hijack or forbidden token leak."""
    if case.forbidden_skills and pred_skill in case.forbidden_skills:
        return True
    if case.forbidden_tokens:
        norm = normalize_bilingual_intent(case.prompt)
        matched_set = set(norm.matched_domain_tokens) | set(norm.canonical_tokens)
        if any(tok in matched_set for tok in case.forbidden_tokens):
            return True
    return False


def run_benchmark(
    cases: Sequence[BenchCase] = BENCHMARK_CASES,
    min_accuracy: float = 90.0,
    repo_root: str = _REPO_ROOT,
) -> Tuple[BilingualBenchReportDTO, List[Dict[str, Any]]]:
    """Executes the stratified bilingual benchmark and returns metrics DTO plus failure details."""
    # Warm singleton index once so steady-state p95 latency reflects real runtime routing
    get_utterance_router_index()

    tp: Dict[str, int] = defaultdict(int)
    fp: Dict[str, int] = defaultdict(int)
    fn: Dict[str, int] = defaultdict(int)

    correct_total = 0
    abstention_total = 0
    abstention_correct = 0
    homonym_total = 0
    homonym_fp = 0
    cal_probs: List[float] = []
    cal_labels: List[int] = []
    latencies_ms: List[float] = []
    failures: List[Dict[str, Any]] = []

    for case in cases:
        t0 = time.perf_counter()
        res = evaluate_skill_first_trigger(prompt=case.prompt, target_files=[], repo_root=repo_root)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        pred = res.get("recommended_skill")
        conf = float(res.get("calibrated_confidence", 0.0))
        is_hit = pred == case.expected_skill
        if is_hit:
            correct_total += 1
        else:
            failures.append({
                "case_id": case.case_id,
                "stratum": case.stratum,
                "prompt": case.prompt,
                "expected": case.expected_skill,
                "predicted": pred,
                "calibrated_confidence": conf,
            })

        if case.expected_skill is None:
            abstention_total += 1
            if pred is None:
                abstention_correct += 1
        else:
            if pred == case.expected_skill:
                tp[case.expected_skill] += 1
            else:
                fn[case.expected_skill] += 1
                if pred is not None:
                    fp[pred] += 1
            cal_probs.append(conf)
            cal_labels.append(1 if is_hit else 0)

        if case.stratum == "homonym_trap":
            homonym_total += 1
            if _evaluate_homonym_trap(case, pred):
                homonym_fp += 1

    total = len(cases)
    top1_acc = round((correct_total / total) * 100.0, 2) if total > 0 else 0.0
    macro_p, macro_r = _compute_macro_pr(tp, fp, fn)
    abs_acc = round((abstention_correct / abstention_total) * 100.0, 2) if abstention_total > 0 else 100.0
    hom_fpr = round((homonym_fp / homonym_total) * 100.0, 2) if homonym_total > 0 else 0.0
    ece = compute_expected_calibration_error(cal_probs, cal_labels, bins=10)

    latencies_ms.sort()
    p95_idx = min(int(len(latencies_ms) * 0.95), max(len(latencies_ms) - 1, 0))
    p95_ms = round(latencies_ms[p95_idx], 3) if latencies_ms else 0.0

    passed_gate = bool(
        total >= 120
        and top1_acc >= float(min_accuracy)
        and hom_fpr <= 2.0
        and p95_ms < 5.0
    )

    report = BilingualBenchReportDTO(
        total_cases=total,
        top1_accuracy_pct=top1_acc,
        macro_precision_pct=macro_p,
        macro_recall_pct=macro_r,
        abstention_accuracy_pct=abs_acc,
        homonym_fpr_pct=hom_fpr,
        expected_calibration_error=ece,
        p95_latency_ms=p95_ms,
        passed_gate=passed_gate,
    )
    return report, failures


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stratified 120+ Vietnamese & Mixed VI-EN Skill Routing Benchmark"
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--gate", action="store_true", help="Exit 1 if quality gate fails")
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=90.0,
        help="Minimum Top-1 accuracy percentage required to pass gate (default: 90.0)",
    )
    parser.add_argument("--output", type=str, default=None, help="Optional JSON report output file")
    args = parser.parse_args(argv)

    report, failures = run_benchmark(min_accuracy=args.min_accuracy)
    payload: Dict[str, Any] = {
        **asdict(report),
        "min_accuracy_threshold": args.min_accuracy,
        "failure_count": len(failures),
        "failures": failures[:15],
    }

    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=2, ensure_ascii=False)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"Total Cases      : {report.total_cases}")
        print(f"Top-1 Accuracy   : {report.top1_accuracy_pct}% (min {args.min_accuracy}%)")
        print(f"Macro P / R      : {report.macro_precision_pct}% / {report.macro_recall_pct}%")
        print(f"Abstention Acc   : {report.abstention_accuracy_pct}%")
        print(f"Homonym FPR      : {report.homonym_fpr_pct}% (max 2.0%)")
        print(f"Calibration ECE  : {report.expected_calibration_error}")
        print(f"p95 Latency      : {report.p95_latency_ms} ms (max 5.0 ms)")
        print(f"Gate Status      : {'PASS' if report.passed_gate else 'FAIL'}")

    if args.gate and not report.passed_gate:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
