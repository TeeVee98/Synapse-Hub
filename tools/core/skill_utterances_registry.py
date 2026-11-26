#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/core/skill_utterances_registry.py — 60-Skill Bilingual Utterance Registry
-------------------------------------------------------------------------------
Immutable semantic-router style Route specifications covering all 57 indexed skills
in skills_index.json plus 3 local .agent/skills workflows (solo, super-plan, review)
with curated English and natural Vietnamese utterances and calibrated thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional, Tuple


@dataclass(frozen=True)
class SkillRouteSpec:
    """Bilingual utterance route definition modeled on semantic-router Route."""

    skill_id: str
    domain: str
    utterances_en: Tuple[str, ...]
    utterances_vi: Tuple[str, ...]
    confidence_threshold: float = 0.42


SKILL_ROUTE_SPECS: Tuple[SkillRouteSpec, ...] = (
    # --- 01-web-automation (11) ---
    SkillRouteSpec(
        skill_id="auth-session-and-cookie-manager",
        domain="01-web-automation",
        utterances_en=(
            "manage browser authentication storageState cookies and JWT refresh tokens",
            "fix users getting logged out when session cookie expires across multi-role tests",
            "reuse authenticated login state and bearer token fixtures in Playwright",
            "debug session expiration and multi-role auth cookie isolation",
        ),
        utterances_vi=(
            "quản lý phiên đăng nhập cookie storageState và làm mới JWT token",
            "người dùng cứ bị văng ra khỏi phiên đăng nhập khi hết hạn token",
            "lưu trạng thái đăng nhập nhiều vai trò và xử lý cookie xác thực",
            "sửa lỗi rớt phiên đăng nhập và cấp lại token xác thực trình duyệt",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="bats-testing-patterns",
        domain="01-web-automation",
        utterances_en=(
            "write Bats unit tests for bash shell scripts and CLI exit codes",
            "test shell script stdout stderr flags and CI bash hooks with Bats",
            "automate bash CLI integration assertions using Bats helper fixtures",
            "verify posix sh script error handling and arguments in Bats",
        ),
        utterances_vi=(
            "viết kiểm thử Bats cho kịch bản bash shell và công cụ dòng lệnh CLI",
            "kiểm tra mã thoát và đầu ra của script bash bằng Bats",
            "tự động test file sh và các tham số dòng lệnh với Bats",
            "xây dựng bộ test bash script trong pipeline CI dùng Bats",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="clean-pom-crafter",
        domain="01-web-automation",
        utterances_en=(
            "build Clean POM Page Object class extending BasePage with flat architecture",
            "refactor raw CSS and XPath selectors into reusable Page Object methods",
            "enforce single-level BasePage inheritance for Playwright and Cypress POM",
            "craft modular Page Class encapsulating UI workflows without raw locators",
        ),
        utterances_vi=(
            "xây dựng lớp trang Clean POM kế thừa BasePage theo kiến trúc phẳng",
            "tái cấu trúc bộ chọn CSS XPath rời rạc vào mô hình trang Page Object",
            "tạo Page Class chuẩn hóa thao tác giao diện không dùng raw selector",
            "chuẩn hóa mô hình trang POM cho kịch bản Playwright và Cypress",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="e2e-testing-patterns",
        domain="01-web-automation",
        utterances_en=(
            "design multi-browser end-to-end test architecture with parallel sharding",
            "configure E2E browser matrix retry governance and worker isolation",
            "architect scalable cross-browser Playwright and Cypress E2E test suites",
            "structure end-to-end checkout flow automation across Chromium WebKit Firefox",
        ),
        utterances_vi=(
            "thiết kế kiến trúc kiểm thử E2E đa trình duyệt và chia mảnh chạy song song",
            "cấu hình bộ kiểm thử end-to-end chạy trên nhiều trình duyệt với cơ chế thử lại",
            "xây dựng kịch bản kiểm thử tự động E2E cho luồng thanh toán và đặt hàng",
            "tổ chức bộ test Playwright Cypress quy mô lớn có phân mảnh song song",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="katalon-cli-runner",
        domain="01-web-automation",
        utterances_en=(
            "run headless Katalon Studio and Gradle test suites from CLI with driver cleanup",
            "execute Katalon Runtime Engine KRE command line suite collection",
            "configure Katalon Groovy execution profiles and automatic WebDriver teardown",
            "automate headless Katalon CLI runner and JUnit report generation",
        ),
        utterances_vi=(
            "chạy bộ test Katalon Studio headless qua dòng lệnh CLI và Gradle",
            "thực thi Katalon KRE tự động và dọn dẹp WebDriver sau khi chạy",
            "cấu hình lệnh chạy Katalon Groovy và xuất báo cáo kết quả kiểm thử",
            "tự động hóa chạy kịch bản Katalon không giao diện trên máy chủ",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="lam-script-generator",
        domain="01-web-automation",
        utterances_en=(
            "transform user stories and acceptance criteria into Clean POM automation scripts",
            "generate Playwright automation code from acceptance criteria and test scenarios",
            "convert business requirements into executable Clean POM test scripts",
            "author automated UI test scripts from Jira user stories",
        ),
        utterances_vi=(
            "chuyển đổi user story và tiêu chí nghiệm thu thành kịch bản tự động Clean POM",
            "sinh mã kiểm thử tự động từ yêu cầu nghiệp vụ và kịch bản chấp nhận",
            "biến đặc tả câu chuyện người dùng thành script test giao diện tự động",
            "tạo kịch bản automation theo chuẩn POM từ tài liệu nghiệm thu",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="mobile-appium-som",
        domain="01-web-automation",
        utterances_en=(
            "build mobile Screen Object Model SOM tests with Appium for iOS and Android",
            "automate native Android XCUITest and UiAutomator2 flows using Appium",
            "design Appium mobile screen classes gestures and device capability fixtures",
            "refactor mobile UI locators into Appium Screen Object Model architecture",
        ),
        utterances_vi=(
            "xây dựng kiểm thử di động Screen Object Model SOM với Appium cho iOS Android",
            "tự động hóa ứng dụng di động Android và iOS bằng Appium",
            "thiết kế lớp màn hình SOM và thao tác chạm vuốt trên thiết bị di động",
            "cấu trúc mã kiểm thử mobile Appium chuẩn hóa cho cả hai hệ điều hành",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="mobile-maestro-detox-patterns",
        domain="01-web-automation",
        utterances_en=(
            "write declarative YAML mobile flows in Maestro and gray-box Detox tests",
            "automate React Native mobile app screens with Detox synchronization and Maestro",
            "build Maestro mobile UI flow assertions and Detox testID selectors",
            "configure React Native end-to-end mobile testing with Maestro or Detox",
        ),
        utterances_vi=(
            "viết luồng kiểm thử di động YAML bằng Maestro và kiểm thử Detox cho React Native",
            "tự động hóa ứng dụng React Native bằng Maestro và kiểm thử hộp xám Detox",
            "tạo kịch bản test giao diện mobile khai báo bằng Maestro flow",
            "cấu hình testID và đồng bộ hóa kiểm thử di động với Detox",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="playwright-live-interaction",
        domain="01-web-automation",
        utterances_en=(
            "probe live web DOM accessibility tree AOM and verify selectors under 200ms",
            "inspect live browser page elements with headless Playwright selector probe",
            "check real DOM locators and ARIA roles on a running web page",
            "verify Playwright getByRole and getByTestId locators against live DOM",
        ),
        utterances_vi=(
            "kiểm tra nhanh DOM và cây trợ năng AOM trực tiếp trên trình duyệt bằng Playwright",
            "dò tìm và xác minh bộ chọn selector thực tế trên trang web đang chạy",
            "kiểm chứng locator getByRole trên giao diện web trực tiếp dưới 200ms",
            "khảo sát cấu trúc phần tử DOM thật bằng Playwright headless",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="playwright-webapp-testing",
        domain="01-web-automation",
        utterances_en=(
            "run Playwright tests against local webapp with managed dev server lifecycle",
            "verify local frontend web application using Playwright smart waits",
            "start local server and execute headless Playwright UI verification checks",
            "test local web app routes forms and hydration with Playwright",
        ),
        utterances_vi=(
            "chạy kiểm thử Playwright trên ứng dụng web nội bộ có quản lý vòng đời server",
            "khởi chạy server local và kiểm tra giao diện web bằng Playwright với smart wait",
            "kiểm thử ứng dụng web cục bộ bằng Playwright không dùng sleep tĩnh",
            "xác minh các trang và biểu mẫu trên localhost bằng Playwright",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="web-agent-gym-benchmarking",
        domain="01-web-automation",
        utterances_en=(
            "benchmark web automation agents and Page Classes on Web Agent Gym fixtures",
            "evaluate autonomous web agent task completion accuracy and latency metrics",
            "run empirical web agent gym evaluation harness against enterprise fixtures",
            "compare web agent selector resilience and success rate benchmarks",
        ),
        utterances_vi=(
            "đánh giá hiệu quả web agent và lớp trang trên bộ chuẩn Web Agent Gym",
            "chạy benchmark đo tỷ lệ hoàn thành và độ trễ của tác tử tự động hóa web",
            "so sánh độ chính xác bộ kiểm thử agent trên các trang mẫu doanh nghiệp",
            "kiểm chuẩn khả năng tương tác web tự động bằng harness benchmark",
        ),
        confidence_threshold=0.42,
    ),
    # --- 02-test-design (6) ---
    SkillRouteSpec(
        skill_id="architecture-decision-records",
        domain="02-test-design",
        utterances_en=(
            "write and maintain technical Architecture Decision Record ADR markdown",
            "document architectural trade-offs context consequences and rejected alternatives in ADR",
            "create numbered ADR document recording system design decision",
            "record architecture decision rationale and migration implications",
        ),
        utterances_vi=(
            "viết tài liệu ghi nhận quyết định kiến trúc ADR theo chuẩn markdown",
            "ghi lại bối cảnh phương án đánh đổi và hệ quả thiết kế vào file ADR",
            "tạo tài liệu ADR đánh số để lưu trữ quyết định kỹ thuật hệ thống",
            "tài liệu hóa lý do chọn kiến trúc và các phương án bị loại bỏ",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="gherkin-to-suite",
        domain="02-test-design",
        utterances_en=(
            "compile Gherkin BDD feature files into expanded test matrix and coverage gaps",
            "transform Given When Then scenario outlines into Universal IR test suites",
            "parse Cucumber .feature files and detect missing boundary test coverage",
            "convert BDD Gherkin specifications into structured automated test matrices",
        ),
        utterances_vi=(
            "chuyển file feature Gherkin BDD thành ma trận kiểm thử và báo cáo thiếu hụt",
            "biên dịch kịch bản Given When Then thành bộ kiểm thử mở rộng",
            "phân tích file .feature Cucumber để sinh ma trận kiểm thử đầy đủ",
            "chuyển đổi đặc tả BDD Gherkin sang danh sách ca kiểm thử có cấu trúc",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="manual-qa-and-rtm-bridge",
        domain="02-test-design",
        utterances_en=(
            "execute ISO 29119 manual QA test cases bug reports and traceability matrix RTM",
            "build requirements traceability matrix linking manual test cases to release gates",
            "triage manual QA bug reports and select automation candidates",
            "create structured manual QA execution checklist and sign-off report",
        ),
        utterances_vi=(
            "thực hiện kiểm thử thủ công theo chuẩn ISO 29119 báo cáo lỗi và ma trận truy vết RTM",
            "lập bảng truy vết yêu cầu RTM và chọn ca kiểm thử phù hợp để tự động hóa",
            "viết báo cáo lỗi thủ công đầy đủ bước tái hiện và đánh giá cổng phát hành",
            "quản lý quy trình kiểm thử manual QA và liên kết yêu cầu nghiệm thu",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="rbt-manual-testing",
        domain="02-test-design",
        utterances_en=(
            "design risk-based manual testing matrix with ambiguity Q&A and Excel export",
            "generate 25-field risk-based test cases prioritized by impact and likelihood",
            "export manual risk-based testing workbook to Excel spreadsheet",
            "run AI-RBT risk scoring and requirement ambiguity analysis for manual QA",
        ),
        utterances_vi=(
            "thiết kế ma trận kiểm thử thủ công theo rủi ro RBT và xuất file Excel",
            "tạo bộ test case 25 trường theo mức độ rủi ro và phân tích điểm mơ hồ",
            "xuất danh sách ca kiểm thử theo rủi ro ra bảng tính Excel",
            "phân tích rủi ro nghiệp vụ và ưu tiên ca kiểm thử thủ công RBT",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="review-spec",
        domain="02-test-design",
        utterances_en=(
            "stress-test product specifications BRD user stories and BDD feature files",
            "audit requirement specification for contradictions missing edge cases and ambiguities",
            "review functional spec and acceptance criteria with zero-context rigor before coding",
            "find gaps and untestable clauses in BRD or user story specification",
        ),
        utterances_vi=(
            "rà soát và phản biện tài liệu đặc tả yêu cầu BRD user story trước khi lập trình",
            "kiểm tra mâu thuẫn và lỗ hổng biên trong bản đặc tả nghiệp vụ",
            "đánh giá tính đầy đủ và khả năng kiểm thử của đặc tả tính năng",
            "phát hiện điểm mơ hồ và thiếu sót trong tài liệu yêu cầu sản phẩm",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="tot-exploratory-testing",
        domain="02-test-design",
        utterances_en=(
            "run Tree-of-Thoughts exploratory testing covering happy path boundary and state chaos",
            "explore race conditions edge states and unexpected user journeys non-linearly",
            "design exploratory test charters probing state transitions and boundary chaos",
            "generate graph-of-thoughts exploratory scenarios for complex workflows",
        ),
        utterances_vi=(
            "thực hiện kiểm thử thăm dò theo cây tư duy bao phủ luồng chính biên và hỗn loạn trạng thái",
            "khám phá các tình huống ngoại lệ chuyển trạng thái bất ngờ và điều kiện tranh chấp",
            "lập phiên kiểm thử thăm dò tìm lỗi ẩn ngoài kịch bản tiêu chuẩn",
            "thiết kế kịch bản exploratory testing phi tuyến cho luồng nghiệp vụ phức tạp",
        ),
        confidence_threshold=0.42,
    ),
    # --- 03-api-and-contracts (3) ---
    SkillRouteSpec(
        skill_id="api-network-mocking-interception",
        domain="03-api-and-contracts",
        utterances_en=(
            "intercept HTTP and GraphQL network traffic stub routes and inject 500 or 503 chaos errors",
            "mock backend API responses timeouts and rate limit 429 failures in browser tests",
            "stub GraphQL mutation and REST endpoint payloads without hitting live backend",
            "simulate flaky network latency dropped packets and server 500 error responses",
        ),
        utterances_vi=(
            "giả lập phản hồi lỗi 500 cho truy vấn GraphQL và chặn yêu cầu mạng HTTP",
            "chặn lưu lượng mạng giả lập API trả về lỗi 503 hoặc hết thời gian chờ",
            "tạo stub cho endpoint REST và GraphQL để test giao diện khi backend lỗi",
            "mô phỏng sự cố mạng mất gói và phản hồi lỗi máy chủ trong kiểm thử",
        ),
        confidence_threshold=0.38,
    ),
    SkillRouteSpec(
        skill_id="api-spec-to-e2e-matrix",
        domain="03-api-and-contracts",
        utterances_en=(
            "generate automated positive boundary and negative API test matrix from OpenAPI Swagger spec",
            "build REST endpoint schema validation and boundary payload matrix from OpenAPI YAML",
            "derive API test cases covering required fields types and status codes from Swagger",
            "create comprehensive API contract test suite from OpenAPI specification",
        ),
        utterances_vi=(
            "tạo ma trận kiểm thử API biên tích cực và tiêu cực từ đặc tả OpenAPI Swagger",
            "sinh bộ test case kiểm tra endpoint và schema dữ liệu từ file OpenAPI",
            "xây dựng ma trận kiểm thử API tự động dựa trên đặc tả Swagger YAML",
            "tạo kịch bản kiểm thử các mã trạng thái và tham số biên của REST API",
        ),
        confidence_threshold=0.38,
    ),
    SkillRouteSpec(
        skill_id="consumer-driven-contract-testing",
        domain="03-api-and-contracts",
        utterances_en=(
            "implement consumer-driven contract testing with Pact and bidirectional OpenAPI verification",
            "verify microservice provider compatibility against consumer Pact contract files",
            "detect breaking API schema drift between frontend consumer and backend provider",
            "publish and verify Pact broker contracts in CI microservice pipelines",
        ),
        utterances_vi=(
            "triển khai kiểm thử hợp đồng dịch vụ CDC với Pact và xác minh hai chiều OpenAPI",
            "kiểm tra tương thích giữa dịch vụ consumer và provider bằng hợp đồng Pact",
            "phát hiện sớm sai lệch lược đồ hợp đồng API giữa các microservice",
            "xác minh hợp đồng API giữa frontend và backend qua Pact broker",
        ),
        confidence_threshold=0.40,
    ),
    # --- 04-performance-and-load (2) ---
    SkillRouteSpec(
        skill_id="backend-load-and-stress-patterns",
        domain="04-performance-and-load",
        utterances_en=(
            "orchestrate k6 Locust and JMeter backend load stress and SLA endurance test suites",
            "simulate high concurrency traffic spikes throughput bottlenecks and p95 latency SLA",
            "design soak stress and ramp-up load tests measuring server saturation and backpressure",
            "benchmark backend API throughput under thousands of virtual users with k6 or JMeter",
        ),
        utterances_vi=(
            "chạy kiểm thử chịu tải áp lực và độ bền SLA cho backend bằng k6 Locust JMeter",
            "mô phỏng lưu lượng truy cập đồng thời cao để tìm điểm nghẽn cổ chai và quá tải",
            "đo thông lượng p95 latency và giới hạn chịu tải máy chủ khi tăng tải đột biến",
            "thiết kế kịch bản load test và stress test bằng k6 hoặc JMeter",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="web-vitals-and-performance-profiler",
        domain="04-performance-and-load",
        utterances_en=(
            "measure Core Web Vitals LCP CLS INP TTFB and network waterfalls via Chrome CDP",
            "profile slow webpage loading layout shift CLS and largest contentful paint LCP",
            "diagnose frontend rendering bottlenecks long main-thread tasks and web vitals",
            "audit browser page load speed and Core Web Vitals performance budgets",
        ),
        utterances_vi=(
            "đo chỉ số hiệu năng Core Web Vitals LCP CLS INP và biểu đồ mạng qua CDP",
            "kiểm tra vì sao trang web tải chậm bị giật bố cục CLS và LCP quá cao",
            "phân tích hiệu năng tải trang frontend và tối ưu các chỉ số Web Vitals",
            "đo tốc độ hiển thị nội dung chính và độ trễ tương tác trang web",
        ),
        confidence_threshold=0.38,
    ),
    # --- 05-security-and-compliance (3) ---
    SkillRouteSpec(
        skill_id="security-dast-sentinel",
        domain="05-security-and-compliance",
        utterances_en=(
            "run dynamic security audit OWASP Top 10 security headers BOLA IDOR and token leakage",
            "scan endpoints for SQL injection XSS CSRF broken authorization and sensitive exposure",
            "verify HTTP CSP HSTS security headers and privilege escalation vulnerabilities",
            "perform DAST penetration checks for authentication bypass and IDOR access flaws",
        ),
        utterances_vi=(
            "chạy kiểm tra bảo mật động OWASP Top 10 header bảo mật BOLA IDOR và rò rỉ token",
            "quét lỗ hổng tiêm mã SQL injection XSS và lỗi phân quyền truy cập trái phép",
            "rà soát bảo mật API phát hiện lỗ hổng leo thang đặc quyền và lộ mật khẩu",
            "kiểm định các tiêu đề bảo mật HTTP và lỗ hổng ứng dụng web DAST",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="skillspector-security-guard",
        domain="05-security-and-compliance",
        utterances_en=(
            "audit AI agent skills prompts and MCP server configurations against vulnerability vectors",
            "scan SKILL.md prompt injection unsafe shell commands and MCP tool permissions",
            "verify agent skill security policies sandboxing and prompt supply-chain safety",
            "run SkillSpector AST security guard over skill directories and MCP configs",
        ),
        utterances_vi=(
            "kiểm tra bảo mật các skill AI agent prompt và cấu hình MCP server khỏi lỗ hổng",
            "quét nguy cơ prompt injection và lệnh shell nguy hiểm trong các file SKILL.md",
            "rà soát chính sách sandbox và an toàn chuỗi cung ứng cho công cụ AI agent",
            "đánh giá rủi ro bảo mật cấu hình MCP và kỹ năng tác tử bằng SkillSpector",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="wcag-audit-patterns",
        domain="05-security-and-compliance",
        utterances_en=(
            "audit WCAG 2.2 accessibility A AA keyboard navigation color contrast and ARIA roles",
            "check broken ARIA screen-reader labels focus traps and tab order accessibility",
            "verify accessible form labels semantic HTML landmarks and contrast ratios",
            "run automated axe-core accessibility compliance audit for WCAG 2.2",
        ),
        utterances_vi=(
            "kiểm tra trợ năng WCAG 2.2 nhãn ARIA cho trình đọc màn hình và điều hướng bàn phím",
            "rà soát lỗi thiếu nhãn ARIA bị hỏng độ tương phản màu sắc và thứ tự phím Tab",
            "đánh giá khả năng tiếp cận accessibility cho người dùng trình đọc màn hình",
            "kiểm định chuẩn trợ năng giao diện web WCAG và thẻ HTML ngữ nghĩa",
        ),
        confidence_threshold=0.38,
    ),
    # --- 06-healing-and-resilience (9) ---
    SkillRouteSpec(
        skill_id="agentless-qa-repair",
        domain="06-healing-and-resilience",
        utterances_en=(
            "repair broken test scripts and Page Classes using localization patch and validation",
            "fix failing automated test suite with 3-phase agentless fault localization",
            "generate candidate repair patches for broken QA test files and validate fixes",
            "localize root fault line in broken test script and apply verified minimal patch",
        ),
        utterances_vi=(
            "sửa kịch bản kiểm thử và lớp trang bị hỏng theo 3 bước định vị vá lỗi và xác minh",
            "tự động khoanh vùng dòng lỗi trong bài test và tạo bản vá sửa lỗi chính xác",
            "khôi phục bộ kiểm thử tự động đang gãy mà không làm hỏng ca test khác",
            "định vị nguyên nhân hỏng test script và kiểm chứng lại bản sửa lỗi",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="antigravity-test-sentinel",
        domain="06-healing-and-resilience",
        utterances_en=(
            "enforce verification-first discipline blocking task completion until quality gates pass",
            "guard against fake passes skipped assertions and unverified done claims",
            "run mandatory test sentinel verification gate before claiming completion",
            "enforce truth anchor policy rejecting empty tests and swallowed exceptions",
        ),
        utterances_vi=(
            "thực thi kỷ luật kiểm chứng trước khi hoàn thành và chặn báo cáo xong giả",
            "ngăn chặn test rỗng bỏ qua assertion và nuốt ngoại lệ trong mã kiểm thử",
            "chạy cổng kiểm soát chất lượng bắt buộc trước khi xác nhận hoàn tất tác vụ",
            "đảm bảo mọi thay đổi đều vượt qua kiểm tra tự động trung thực",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="failure-autopsy-and-healing",
        domain="06-healing-and-resilience",
        utterances_en=(
            "triage test failures from JUnit XML stack traces screenshots and heal broken selectors",
            "perform failure autopsy distinguishing product bugs from stale UI locators",
            "analyze CI failure artifacts logs and screenshots to pinpoint root cause",
            "inspect JUnit XML failure reports and auto-triage broken automation runs",
        ),
        utterances_vi=(
            "khám nghiệm lỗi kiểm thử từ JUnit XML ảnh chụp màn hình và phân loại nguyên nhân",
            "phân tích log lỗi CI phân biệt lỗi sản phẩm thật với lỗi hỏng bộ chọn giao diện",
            "truy vết báo cáo thất bại tự động từ XML và ảnh chụp lỗi để khắc phục",
            "tổng hợp và chẩn đoán nguyên nhân các ca kiểm thử bị fail trên pipeline",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="flaky-test-sentinel-and-quarantine",
        domain="06-healing-and-resilience",
        utterances_en=(
            "detect non-deterministic flaky tests calculate flakiness scores and manage quarantine",
            "investigate why tests pass sometimes and fail randomly across CI retries",
            "eliminate static sleeps race conditions and intermittent UI test failures",
            "quarantine unstable flaky test specs and track flake rate recovery",
        ),
        utterances_vi=(
            "phát hiện bài test chập chờn lúc pass lúc fail tính điểm flaky và đưa vào cách ly",
            "điều tra nguyên nhân kịch bản kiểm thử chạy không ổn định lúc được lúc không",
            "loại bỏ chờ tĩnh ngủ tĩnh gây test hay bị fail ngẫu nhiên trên CI",
            "quản lý danh sách cách ly các ca kiểm thử chập chờn và theo dõi độ ổn định",
        ),
        confidence_threshold=0.38,
    ),
    SkillRouteSpec(
        skill_id="self-healing-locator",
        domain="06-healing-and-resilience",
        utterances_en=(
            "heal broken UI locators using semantic AOM diffing with Role Label and TestId hierarchy",
            "repair Playwright or Selenium element not found selector errors automatically",
            "upgrade fragile CSS XPath selectors to resilient getByRole and data-testid locators",
            "auto-heal broken button locator after frontend DOM attribute changes",
        ),
        utterances_vi=(
            "tự sửa bộ chọn locator bị hỏng bằng so sánh ngữ nghĩa AOM ưu tiên Role Label TestId",
            "khắc phục lỗi không tìm thấy nút hoặc phần tử trên giao diện sau khi đổi DOM",
            "thay thế CSS XPath dễ gãy sang bộ chọn bền vững theo ngữ nghĩa vai trò",
            "tự phục hồi selector bị lỗi trong kịch bản Playwright và Selenium",
        ),
        confidence_threshold=0.38,
    ),
    SkillRouteSpec(
        skill_id="systematic-debugging",
        domain="06-healing-and-resilience",
        utterances_en=(
            "investigate root cause systematically through four disciplined phases before patching",
            "debug complex production bug with hypothesis testing reproduction and evidence logs",
            "trace root cause analysis RCA systematically instead of guessing random fixes",
            "isolate intermittent defect cause with minimal reproducible test case",
        ),
        utterances_vi=(
            "điều tra nguyên nhân gốc một cách bài bản qua bốn giai đoạn trước khi sửa mã",
            "gỡ lỗi sự cố phức tạp bằng cách tái hiện lập giả thuyết và kiểm chứng bằng chứng",
            "phân tích nguyên nhân gốc RCA có hệ thống thay vì sửa mò theo cảm tính",
            "khoanh vùng chính xác nguồn gốc lỗi bằng kịch bản tái hiện tối giản",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="test-driven-development",
        domain="06-healing-and-resilience",
        utterances_en=(
            "follow strict RED GREEN REFACTOR test-driven development cycle before production code",
            "write failing unit test first verify red failure then implement minimal green code",
            "practice TDD discipline ensuring every new behavior starts with a failing test",
            "refactor implementation safely under green unit test coverage",
        ),
        utterances_vi=(
            "áp dụng chu trình phát triển hướng kiểm thử TDD đỏ xanh tái cấu trúc nghiêm ngặt",
            "viết bài test thất bại trước để xác nhận đỏ rồi mới cài đặt mã tối thiểu cho xanh",
            "thực hành TDD đảm bảo mọi tính năng mới đều có test bảo vệ ngay từ đầu",
            "tái cấu trúc mã nguồn an toàn dưới sự kiểm chứng liên tục của bộ unit test",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="verification-before-completion",
        domain="06-healing-and-resilience",
        utterances_en=(
            "require fresh terminal verification evidence before claiming task success or completion",
            "run final tests linter and quality gates to prove zero regressions empirically",
            "verify actual command output and exit code 0 before reporting done",
            "prevent premature completion claims without fresh empirical test proof",
        ),
        utterances_vi=(
            "yêu cầu bằng chứng chạy lệnh thực tế mới nhất trước khi tuyên bố hoàn thành",
            "chạy lại toàn bộ test linter và cổng kiểm định để chứng minh không có lỗi hồi quy",
            "xác minh mã thoát 0 và đầu ra terminal trước khi báo cáo xong tác vụ",
            "chặn việc kết luận hoàn tất sớm khi chưa có kết quả kiểm chứng thực nghiệm",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="visual-regression-sentinel",
        domain="06-healing-and-resilience",
        utterances_en=(
            "run pixel diff and layout shift visual regression testing with dynamic masking",
            "compare UI screenshots against golden baselines masking timestamps and animations",
            "detect unintended CSS styling regressions overlap and visual layout breakage",
            "automate visual snapshot comparison with anti-flake region masks",
        ),
        utterances_vi=(
            "chạy kiểm thử hồi quy hình ảnh so sánh pixel ảnh chụp giao diện với mặt nạ che vùng động",
            "phát hiện lỗi lệch bố cục CSS vỡ giao diện so với ảnh chuẩn baseline",
            "che vùng thời gian và hiệu ứng động để so sánh screenshot không bị báo lỗi giả",
            "tự động kiểm tra sai khác hình ảnh giao diện người dùng sau khi sửa CSS",
        ),
        confidence_threshold=0.40,
    ),
    # --- 07-data-and-state (3) ---
    SkillRouteSpec(
        skill_id="db-state-verifier-and-seeder",
        domain="07-data-and-state",
        utterances_en=(
            "seed isolated SQL and NoSQL database test fixtures and verify row state mutations",
            "assert database transaction integrity and run automated teardown cleanup after tests",
            "verify PostgreSQL MySQL SQLite or MongoDB records created during E2E flows",
            "prepare idempotent database seed data and clean up test rows cleanly",
        ),
        utterances_vi=(
            "nạp dữ liệu mẫu cơ sở dữ liệu SQL NoSQL kiểm tra trạng thái bản ghi và dọn dẹp sau khi test",
            "xác minh dữ liệu thay đổi trong database và thực hiện teardown dọn fixture tự động",
            "kiểm tra tính toàn vẹn giao dịch bảng cơ sở dữ liệu sau khi chạy luồng kiểm thử",
            "khởi tạo dữ liệu seed cô lập trong DB và xóa sạch sau khi kết thúc bài test",
        ),
        confidence_threshold=0.38,
    ),
    SkillRouteSpec(
        skill_id="file-and-report-validator",
        domain="07-data-and-state",
        utterances_en=(
            "validate downloaded and uploaded Excel XLSX CSV and PDF file schemas and tabular integrity",
            "verify exported report columns headers row counts and numeric totals in Excel or CSV",
            "check PDF report text structure and downloaded spreadsheet formatting accuracy",
            "automate assertions on exported CSV XLSX and PDF business documents",
        ),
        utterances_vi=(
            "kiểm tra cấu trúc schema và tính toàn vẹn dữ liệu bảng trong file Excel CSV PDF tải về",
            "xác minh cột tiêu đề số dòng và tổng tiền trong báo cáo xuất Excel và CSV",
            "xuất báo cáo Excel và CSV và kiểm định định dạng bảng tính",
            "đối chiếu nội dung file PDF tải xuống và kiểm tra định dạng bảng tính xuất ra",
        ),
        confidence_threshold=0.38,
    ),
    SkillRouteSpec(
        skill_id="synthetic-test-data-generator",
        domain="07-data-and-state",
        utterances_en=(
            "generate idempotent boundary-value synthetic test data with unique runtime timestamps",
            "create randomized unique entity codes fake emails and edge-case payloads for QA",
            "build deterministic synthetic datasets avoiding database collision errors",
            "produce boundary strings unicode edge inputs and unique AUTO_ test records",
        ),
        utterances_vi=(
            "tạo dữ liệu giả kiểm thử tổng hợp có mã duy nhất theo thời gian tránh trùng lặp DB",
            "sinh dữ liệu đầu vào giá trị biên và mã thực thể ngẫu nhiên cho bộ test tự động",
            "tạo bộ dữ liệu mẫu giả lập email số điện thoại và chuỗi biên cho QA",
            "sinh dữ liệu kiểm thử idempotent không bị va chạm khóa chính trong cơ sở dữ liệu",
        ),
        confidence_threshold=0.40,
    ),
    # --- 08-code-quality (8) ---
    SkillRouteSpec(
        skill_id="code-refactoring-refactor-clean",
        domain="08-code-quality",
        utterances_en=(
            "refactor legacy technical debt and deeply nested functions using SOLID clean code",
            "simplify complex control flow extract clean helpers and remove duplicate logic",
            "clean up bloated modules preserving behavior under existing test coverage",
            "apply SOLID design principles to decompose god functions into cohesive units",
        ),
        utterances_vi=(
            "tái cấu trúc mã nguồn loại bỏ nợ kỹ thuật và làm phẳng hàm lồng nhau sâu theo chuẩn SOLID",
            "đơn giản hóa luồng điều khiển tách hàm gọn gàng và xóa mã trùng lặp",
            "dọn dẹp module phình to mà vẫn giữ nguyên hành vi theo bộ test hiện có",
            "áp dụng nguyên lý Clean Code tách nhỏ hàm phức tạp cho dễ bảo trì",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="graphify-impact-analyzer",
        domain="08-code-quality",
        utterances_en=(
            "analyze AST code change blast radius call graph fan-in and impacted test cases",
            "trace downstream callers and transitive dependents across the codebase graph",
            "scope impacted unit tests from modified Python or TypeScript AST symbols",
            "compute architectural blast radius and dependency edges before editing",
        ),
        utterances_vi=(
            "phân tích bán kính ảnh hưởng blast radius bằng đồ thị gọi hàm AST và chọn test liên quan",
            "truy vết các hàm gọi xuôi dòng và phụ thuộc bắc cầu trong mã nguồn",
            "xác định phạm vi ca kiểm thử bị tác động khi sửa một hàm hoặc module",
            "đo mức độ ảnh hưởng kiến trúc dựa trên phân tích cây cú pháp AST",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="lean-code-ladder",
        domain="08-code-quality",
        utterances_en=(
            "apply 7-rung reuse-first lean code ladder choosing stdlib over heavy dependencies",
            "minimize new code surface by reusing existing repo helpers and Python stdlib first",
            "evaluate lean implementation trade-offs before adding third-party packages",
            "write the smallest complete maintainable change without unnecessary abstractions",
        ),
        utterances_vi=(
            "áp dụng thang mã tinh gọn 7 bậc ưu tiên tái sử dụng thư viện chuẩn thay vì cài thêm gói nặng",
            "tối giản lượng mã viết mới bằng cách tận dụng helper sẵn có và Python stdlib",
            "đánh giá giải pháp gọn nhất hoàn chỉnh nhất trước khi thêm thư viện ngoài",
            "tránh trừu tượng hóa thừa và giữ thay đổi mã ở mức tinh gọn nhất",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="lean-impact-scoreboard",
        domain="08-code-quality",
        utterances_en=(
            "display empirical impact scoreboard tracking code reduction token savings and mutation rigor",
            "generate metrics dashboard summarizing lines removed latency gains and test scores",
            "report lean engineering impact measurements and verification telemetry",
            "compare before-and-after token budget and mutation score improvements",
        ),
        utterances_vi=(
            "hiển thị bảng điểm tác động thực nghiệm đo mức giảm mã tiết kiệm token và điểm đột biến",
            "tổng hợp báo cáo chỉ số hiệu quả kỹ thuật trước và sau khi tối ưu",
            "theo dõi số liệu đo lường độ tinh gọn mã nguồn và chất lượng kiểm thử",
            "xuất bảng thống kê tiết kiệm ngữ cảnh và tỷ lệ tiêu diệt đột biến",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="repo-quality-audit",
        domain="08-code-quality",
        utterances_en=(
            "run comprehensive repository quality audit checking bugs bottlenecks bloat and compliance",
            "audit entire codebase architecture invariants lint health and dead code debt",
            "perform full hub diagnostic inspection covering quality gates and maintainability",
            "scan repository for structural smells performance bottlenecks and rule drift",
        ),
        utterances_vi=(
            "kiểm toán chất lượng toàn bộ kho mã nguồn tìm lỗi điểm nghẽn phình mã và vi phạm chuẩn",
            "rà soát tổng thể kiến trúc dự án kiểm tra bất biến linter và mã chết",
            "đánh giá sức khỏe mã nguồn và mức độ tuân thủ quy chuẩn kỹ thuật toàn repo",
            "quét toàn diện repo để phát hiện nợ kỹ thuật và điểm yếu bảo trì",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="senior-code-review",
        domain="08-code-quality",
        utterances_en=(
            "review pull request diff across logic security concurrency edge cases and test coverage",
            "conduct senior developer adversarial code review before merging changes",
            "inspect modified source lines for subtle bugs race conditions and missing tests",
            "audit code quality security risks and backward compatibility in git diff",
        ),
        utterances_vi=(
            "đánh giá mã nguồn pull request về logic bảo mật đồng thời trường hợp biên và độ phủ test",
            "thực hiện phản biện mã nguồn như kỹ sư trưởng trước khi hợp nhất nhánh",
            "rà soát diff mã nguồn tìm lỗi tinh vi xung đột luồng và thiếu kiểm thử",
            "kiểm tra chất lượng code rủi ro bảo mật và tính tương thích ngược của bản sửa",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="surgical-coding-principles",
        domain="08-code-quality",
        utterances_en=(
            "apply surgical minimal diff edits thinking before coding with strict scope discipline",
            "make targeted surgical code modifications without touching unrelated lines",
            "enforce simplicity first and goal-driven coding principles on edits",
            "keep git diffs minimal clean and strictly scoped to the task contract",
        ),
        utterances_vi=(
            "áp dụng nguyên tắc sửa mã phẫu thuật tối giản suy nghĩ trước khi code và giữ chặt phạm vi",
            "chỉnh sửa đúng vùng mã mục tiêu không động chạm các dòng không liên quan",
            "ưu tiên sự đơn giản và hướng mục tiêu rõ ràng trong mọi thao tác sửa code",
            "giữ git diff gọn sạch tuyệt đối theo đúng phạm vi yêu cầu",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="technical-debt-harvester",
        domain="08-code-quality",
        utterances_en=(
            "harvest shortcut annotations TODO FIXME comments into tracked technical debt ledger",
            "scan repository for shortcut upgrade markers and build debt triage backlog",
            "collect technical debt tags across modules for engineering prioritization",
            "audit inline shortcut annotations and export debt register",
        ),
        utterances_vi=(
            "thu thập các chú thích shortcut và nợ kỹ thuật trong mã nguồn vào sổ theo dõi",
            "quét toàn bộ dự án tìm các đánh dấu giải pháp tạm để lập danh mục xử lý nợ kỹ thuật",
            "tổng hợp thẻ nợ kỹ thuật theo từng module phục vụ ưu tiên bảo trì",
            "rà soát các ghi chú nâng cấp trong mã nguồn và xuất báo cáo nợ kỹ thuật",
        ),
        confidence_threshold=0.42,
    ),
    # --- 09-ci-and-devops (3) ---
    SkillRouteSpec(
        skill_id="github-actions-templates",
        domain="09-ci-and-devops",
        utterances_en=(
            "create production GitHub Actions YAML workflows for automated test suites and CI CD",
            "configure GitHub Actions matrix sharding caching and artifact upload for Playwright Pytest",
            "build GitHub Actions pull request quality gate workflow pipeline",
            "set up automated CI verification jobs in .github/workflows YAML",
        ),
        utterances_vi=(
            "tạo quy trình GitHub Actions YAML cho bộ kiểm thử tự động và CI CD",
            "cấu hình ma trận chạy song song bộ nhớ đệm và lưu báo cáo trên GitHub Actions",
            "xây dựng pipeline cổng kiểm định chất lượng pull request trên GitHub",
            "thiết lập job kiểm thử tự động Playwright và Pytest trong .github/workflows",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="gitlab-ci-templates",
        domain="09-ci-and-devops",
        utterances_en=(
            "create GitLab CI CD .gitlab-ci.yml pipeline blueprints for Playwright Katalon and Pytest",
            "configure GitLab Runner parallel matrix sharding artifacts and JUnit reports",
            "set up GitLab CI merge request test stages and docker runner caching",
            "author multi-stage GitLab CI automation pipelines for QA suites",
        ),
        utterances_vi=(
            "tạo bản thiết kế pipeline GitLab CI CD trong .gitlab-ci.yml cho Playwright Katalon Pytest",
            "cấu hình GitLab Runner chạy phân mảnh song song và xuất báo cáo JUnit",
            "thiết lập các giai đoạn kiểm thử tự động cho merge request trên GitLab CI",
            "xây dựng pipeline kiểm thử nhiều tầng chạy trên Docker của GitLab",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="jenkins-pipeline-templates",
        domain="09-ci-and-devops",
        utterances_en=(
            "create Jenkins Declarative Pipeline Jenkinsfile for parallel test stages and Katalon KRE",
            "configure Jenkins post-build JUnit Allure archival and agent label execution",
            "author Groovy Jenkinsfile orchestrating parallel QA automation stages",
            "set up Jenkins CI pipeline triggering headless tests with timeout and cleanup",
        ),
        utterances_vi=(
            "tạo Jenkins Declarative Pipeline Jenkinsfile cho các giai đoạn kiểm thử song song và Katalon KRE",
            "cấu hình Jenkins lưu báo cáo JUnit Allure và chạy trên các node agent",
            "viết Jenkinsfile bằng Groovy điều phối các tầng kiểm thử tự động",
            "thiết lập pipeline Jenkins chạy test tự động có giới hạn thời gian và dọn dẹp",
        ),
        confidence_threshold=0.40,
    ),
    # --- 10-agent-orchestration (5) ---
    SkillRouteSpec(
        skill_id="actor-qa-swarm",
        domain="10-agent-orchestration",
        utterances_en=(
            "orchestrate asynchronous Actor Model message broker and matrix sharding QA swarm",
            "coordinate multi-agent parallel test shards using actor queues and worktrees",
            "distribute QA test workloads across independent swarm worker actors",
            "manage actor swarm mailbox routing and LPT shard bin-packing",
        ),
        utterances_vi=(
            "điều phối đàn tác tử kiểm thử theo mô hình Actor bất đồng bộ và phân mảnh ma trận",
            "phối hợp nhiều agent chạy song song trên các mảnh kiểm thử độc lập",
            "phân bổ tải kiểm thử qua hàng đợi thông điệp Actor cho các worker swarm",
            "quản lý chia mảnh kiểm thử tối ưu LPT trong hệ thống đa tác tử",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="agent-orchestration-multi-agent-optimize",
        domain="10-agent-orchestration",
        utterances_en=(
            "profile benchmark and optimize multi-agent test workloads and token throughput",
            "tune agent routing cost latency and parallel worker utilization metrics",
            "reduce multi-agent orchestration token overhead and scheduling bottlenecks",
            "benchmark agent swarm throughput and compute tier allocation",
        ),
        utterances_vi=(
            "đo lường tối ưu hóa tải công việc đa tác tử và thông lượng sử dụng token",
            "tinh chỉnh chi phí độ trễ và phân bổ tài nguyên giữa các agent",
            "giảm hao phí token và điểm nghẽn điều phối trong luồng đa tác tử",
            "đánh giá hiệu suất điều phối agent theo từng bậc mô hình tính toán",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="event-stream-qa-orchestrator",
        domain="10-agent-orchestration",
        utterances_en=(
            "record immutable EventStream action observation timelines with SHA-256 hash chaining",
            "audit deterministic cryptographic event stream logs for QA agent runs",
            "replay append-only SHA-256 chained agent observation events",
            "verify tamper-evident event stream timeline integrity across stages",
        ),
        utterances_vi=(
            "ghi nhận dòng sự kiện bất biến EventStream nối chuỗi băm SHA-256 cho hành động và quan sát",
            "kiểm toán nhật ký dòng sự kiện mật mã xác định của các phiên chạy agent",
            "phát lại chuỗi sự kiện chỉ ghi thêm để truy vết toàn bộ quá trình kiểm thử",
            "xác minh tính toàn vẹn chống chỉnh sửa của dòng sự kiện thực thi",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="persistent-planning-files",
        domain="10-agent-orchestration",
        utterances_en=(
            "persist task plans findings and milestone progress to structured markdown across resets",
            "maintain PROJECT_STATE.md and persistent planning checkpoints across long sessions",
            "sync multi-step execution progress and design notes to durable planning files",
            "resume interrupted engineering work from persistent markdown plan state",
        ),
        utterances_vi=(
            "lưu bền vững kế hoạch nhiệm vụ phát hiện và tiến độ cột mốc vào file markdown qua các phiên",
            "đồng bộ trạng thái dự án và điểm kiểm tra kế hoạch để không mất ngữ cảnh",
            "cập nhật tiến độ thực thi nhiều bước vào tệp kế hoạch bền vững",
            "tiếp tục công việc bị gián đoạn dựa trên file trạng thái kế hoạch đã lưu",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="qa-memory-os",
        domain="10-agent-orchestration",
        utterances_en=(
            "manage hierarchical 3-tier memory OS with Core blocks Recall logs and Archival storage",
            "store and retrieve long-term QA lessons learned in hierarchical agent memory",
            "compact recall memory blocks into archival knowledge index for agents",
            "query persistent Core Recall and Archival QA memory tiers",
        ),
        utterances_vi=(
            "quản lý hệ điều hành bộ nhớ 3 tầng gồm khối cốt lõi nhật ký hồi tưởng và kho lưu trữ",
            "lưu và truy xuất bài học kinh nghiệm kiểm thử dài hạn trong bộ nhớ phân tầng",
            "nén lịch sử hội thoại vào bộ nhớ lưu trữ lâu dài cho AI agent",
            "truy vấn tri thức kiểm thử từ các tầng bộ nhớ Core Recall Archival",
        ),
        confidence_threshold=0.42,
    ),
    # --- 11-ai-and-prompting (4) ---
    SkillRouteSpec(
        skill_id="meta-prompt-crafter",
        domain="11-ai-and-prompting",
        utterances_en=(
            "transform rough human instructions into structured production-grade meta-prompts",
            "craft clear role constraints output schemas and guardrails for LLM prompts",
            "rewrite vague user requests into deterministic structured system prompts",
            "design reusable prompt templates with explicit verification criteria",
        ),
        utterances_vi=(
            "biến yêu cầu thô thành meta-prompt có cấu trúc đạt chuẩn sản xuất",
            "thiết kế câu lệnh prompt rõ vai trò ràng buộc định dạng đầu ra và hàng rào an toàn",
            "viết lại yêu cầu mơ hồ thành system prompt chặt chẽ dễ kiểm chứng cho LLM",
            "xây dựng mẫu prompt tái sử dụng có tiêu chí đánh giá rõ ràng",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="mipro-prompt-compiler",
        domain="11-ai-and-prompting",
        utterances_en=(
            "optimize prompt instructions and few-shot demos with MIPROv2 Bayesian teleprompter",
            "compile and tune LLM prompt pipelines against automated evaluation datasets",
            "run Bayesian prompt optimization maximizing eval accuracy metrics",
            "search optimal prompt instruction candidates and bootstrapped demonstrations",
        ),
        utterances_vi=(
            "tối ưu hóa câu lệnh prompt và ví dụ mẫu bằng bộ biên dịch Bayes MIPROv2",
            "tinh chỉnh tự động hướng dẫn prompt dựa trên tập dữ liệu chấm điểm",
            "chạy tối ưu hóa prompt để nâng cao độ chính xác đầu ra của mô hình",
            "tìm tổ hợp chỉ dẫn và ví dụ few-shot tối ưu bằng đánh giá tự động",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="qa-aci-interface",
        domain="11-ai-and-prompting",
        utterances_en=(
            "inspect bounded code windows and perform surgical pre-linted Agent-Computer Interface edits",
            "use safe ACI file viewer and syntax-checked line range patching",
            "apply bounded AST-validated code edits preventing indentation and syntax breaks",
            "navigate large source files via windowed ACI slicing before editing",
        ),
        utterances_vi=(
            "xem cửa sổ mã nguồn giới hạn và thực hiện chỉnh sửa an toàn kiểm tra cú pháp trước qua ACI",
            "sử dụng giao diện Agent-Computer Interface để vá mã có kiểm tra lint tự động",
            "đọc lát cắt mã nguồn theo vùng dòng chính xác tránh tràn ngữ cảnh",
            "chỉnh sửa mã an toàn có xác thực cú pháp trước khi ghi xuống đĩa",
        ),
        confidence_threshold=0.42,
    ),
    SkillRouteSpec(
        skill_id="token-and-context-optimizer",
        domain="11-ai-and-prompting",
        utterances_en=(
            "optimize prompt token budget distill verbose terminal logs and prevent context rot",
            "compress long stack traces and compact conversation history to save LLM tokens",
            "reduce prompt context bloat and preserve KV cache prefix stability",
            "trim noisy build logs into concise diagnostic summaries for context efficiency",
        ),
        utterances_vi=(
            "tối ưu ngân sách token ngữ cảnh chắt lọc log terminal dài và chống thối ngữ cảnh",
            "nén lịch sử hội thoại và dấu vết lỗi dài để tiết kiệm token LLM",
            "giảm phình ngữ cảnh prompt và giữ ổn định tiền tố KV cache",
            "rút gọn đầu ra build và test rườm rà thành tóm tắt chẩn đoán súc tích",
        ),
        confidence_threshold=0.40,
    ),
    # --- Local .agent/skills Meta-Workflows (3) ---
    SkillRouteSpec(
        skill_id="super-plan",
        domain="10-agent-orchestration",
        utterances_en=(
            "create deep spec-driven implementation plan with blast radius DAG and verification matrix",
            "run /super-plan architectural planning risk routing ambiguity gate and milestones",
            "design atomic execution DAG with typed interface contracts and rollback hooks",
            "build implementation_plan.md blueprint and red-team plan mutations",
        ),
        utterances_vi=(
            "lập kế hoạch triển khai chi tiết theo đặc tả kèm đồ thị cột mốc DAG và ma trận kiểm thử",
            "chạy /super-plan phân tích bán kính ảnh hưởng rủi ro và cổng xử lý mơ hồ",
            "thiết kế bản vẽ kiến trúc implementation_plan.md với hợp đồng giao diện rõ ràng",
            "lên kế hoạch kỹ thuật phân rã các cột mốc nguyên tử có cơ chế hoàn tác",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="solo",
        domain="10-agent-orchestration",
        utterances_en=(
            "execute implementation plan milestones sequentially in single-agent /solo TDD loop",
            "run /solo Red Green Mutation Purple verification workflow without swarm workers",
            "certify HMAC Red Green receipts and live mutation score above 80 percent",
            "execute --from-plan DAG milestones sequentially with adversarial self-audit",
        ),
        utterances_vi=(
            "thực thi tuần tự các cột mốc trong implementation_plan.md bằng /solo không dùng swarm",
            "chạy vòng lặp kiểm chứng đơn tác tử Red Green Mutation Purple với biên lai HMAC",
            "thực hiện lập trình hướng test đơn luồng và kiểm thử đột biến đạt trên 80 phần trăm",
            "triển khai kế hoạch từng bước tuần tự bằng solo_runner và tự kiểm toán phản biện",
        ),
        confidence_threshold=0.40,
    ),
    SkillRouteSpec(
        skill_id="review",
        domain="08-code-quality",
        utterances_en=(
            "run post-code adversarial /review reconciling diffs and HMAC receipts against plan",
            "audit completed /solo implementation for plan compliance bugs and simplify lenses",
            "perform strict read-only code review verifying receipts and downstream callers",
            "execute closed-loop /review producing signed code_review_receipt.json verdict",
        ),
        utterances_vi=(
            "chạy /review phản biện sau khi code đối chiếu diff và biên lai HMAC với kế hoạch",
            "rà soát kết quả thực thi /solo tìm lỗi sai lệch hợp đồng và cơ hội đơn giản hóa mã",
            "thực hiện đánh giá mã nguồn chỉ đọc nghiêm ngặt kiểm tra biên lai và hàm gọi xuôi dòng",
            "kiểm duyệt khép kín sau lập trình và xuất biên lai đánh giá có chữ ký",
        ),
        confidence_threshold=0.40,
    ),
)

_SKILL_SPEC_BY_ID: Mapping[str, SkillRouteSpec] = MappingProxyType(
    {spec.skill_id: spec for spec in SKILL_ROUTE_SPECS}
)


def get_skill_route_spec(skill_id: str) -> Optional[SkillRouteSpec]:
    """Looks up an immutable SkillRouteSpec by skill_id in O(1) time."""
    if not skill_id:
        return None
    return _SKILL_SPEC_BY_ID.get(skill_id.lower())
