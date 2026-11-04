# 🧠 Synapse Hub — AI Test Quality Linter & Guardrails

### *Bộ Linter & Chốt Chặn Chất Lượng Test Dành Cho Thời Đại AI Viết Code*

[🇻🇳 Tiếng Việt](README.md) | [🇬🇧 English Edition](README.en.md)

> **Định vị cốt lõi:** Bộ Linter & Guardrails độc lập (zero external dependencies cho core engine & DoD gates) bảo vệ độ tin cậy của test suite khi AI viết code — Tự động bắt test "pass ảo" (0 assert, tautology), loại bỏ hoàn toàn sleep cố định, nén 95% log CI/CD, và chuẩn hóa cấu trúc Clean POM.  
> **Tác giả:** Thế Vị ([@TeeVee998](https://github.com/TeeVee998)) | **Giấy phép:** MIT License  
> **Phiên bản:** `v3.0.0` | **Quy mô:** 51 Kỹ năng QA, 6 Vai trò AI Agent, 10 Cổng kiểm định DoD.

[![npm version](https://img.shields.io/npm/v/synapse-hub.svg?style=flat-square&color=blue)](https://www.npmjs.com/package/synapse-hub)
[![node version](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen.svg?style=flat-square)](https://nodejs.org)
[![python version](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg?style=flat-square)](https://python.org)
[![license](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](https://github.com/TeeVee998/Synapse-Hub/blob/main/LICENSE)
[![Ecosystem](https://img.shields.io/badge/AI%20Ecosystem-Antigravity%20%7C%20Cursor%20%7C%20Claude%20%7C%20Copilot%20%7C%20Windsurf-orange.svg?style=flat-square)](#)

---

## 💡 Synapse Hub Giải Quyết Vấn Đề Gì?

Khi lập trình viên và QA dùng AI (Cursor, Copilot, Claude Code, Antigravity) để viết test tự động, AI thường sinh ra mã kiểm thử có vấn đề:

| Khi để AI tự viết test (Chưa có Synapse) | Khi có Synapse Hub gác cổng 🛡️ |
| :--- | :--- |
| ❌ **Test "pass ảo":** Chạy xanh nhưng có **0 câu lệnh assert**, không kiểm tra gì cả. | ✅ **Phát hiện trong 0.1s:** Báo lỗi test rỗng, bắt buộc assertion có ý nghĩa. |
| ❌ **Dùng sleep cứng:** Chèn `sleep(5000)` bừa bãi làm test chậm và flaky trên CI. | ✅ **Ép dùng Smart Wait:** Tự động phát hiện và hướng dẫn thay thế smart wait. |
| ❌ **Tràn context AI:** Log CI dài 20.000 dòng làm AI quá tải, tốn token vô ích. | ✅ **Nén sạch 95% log:** Cô đọng còn ~30 dòng stacktrace nguyên nhân gốc. |
| ❌ **Thủng bảo mật:** AI vô tình commit mật khẩu hoặc API token dạng plaintext. | ✅ **Chốt chặn Gate 6:** Quét và chặn đứng chuỗi nhạy cảm trước khi commit. |

---

## ⚡ Bắt Đầu Nhanh Trong 60 Giây (1 Lệnh Khởi Chạy 🚀)

Bạn **không cần học hay ghi nhớ** 51 kỹ năng hay các công cụ bên trong. Synapse Hub hoạt động tự động khi cần:

```bash
# 1. Chẩn đoán môi trường hệ thống (Node, Python, Chrome, Git):
npx synapse-hub doctor

# 2. Kích hoạt bảo vệ dự án kiểm thử của bạn (Playwright, Pytest, Cypress, Katalon):
npx synapse-hub setup --target /duong-dan/toi/du-an-test

# 3. Quét lỗi test pass ảo & sleep cứng ngay lập tức:
npx synapse-hub lint ./tests

# 4. Kiểm định 10 Cổng Chất Lượng DoD trước khi đẩy code:
npx synapse-hub verify
```

> 💡 **Mẹo:** Cài đặt toàn cục để gõ trực tiếp `synapse-hub <lệnh>` không cần tiền tố `npx`:  
> `npm install -g synapse-hub` (hoặc qua Python: `pip install agent-qa`)

---

## 🛠️ Các Lệnh CLI Cốt Lõi Hàng Ngày

```bash
# Bắt test pass ảo, sleep cố định, try-catch nuốt lỗi (đa ngôn ngữ TS/JS, Python, Groovy):
synapse-hub lint ./tests

# Chạy toàn diện 10 Cổng Kiểm Định DoD (Definition of Done):
synapse-hub verify

# Chẩn đoán và xuất báo cáo sức khỏe dự án (PROJECT_HEALTH_REPORT.md):
synapse-hub analyze

# Nén 95% log CI thừa — lọc đúng nguyên nhân gốc rễ và stacktrace:
synapse-hub distill path/to/ci.log

# Xuất User Story thành file Excel chuẩn 12 cột kèm ma trận rủi ro:
synapse-hub export-excel

# Đo độ nhạy của các câu lệnh assert (Micro-Mutation testing ~0.1s):
synapse-hub mutate ./tests
```

---

## 🛡️ 10 Cổng Kiểm Định Chất Lượng (DoD Gates)

Mọi thay đổi mã nguồn kiểm thử đều được kiểm chứng qua 10 Cổng Chất Lượng trước khi merge PR:

- **Gate 0:** Bảo Toàn Tác Quyền & MIT License Provenance
- **Gate 1:** Mã Hóa Chuẩn 100% UTF-8 No BOM (Zero byte rác)
- **Gate 2:** Đường Dẫn Linh Hoạt (Zero hardcoded absolute paths)
- **Gate 3:** Kiến Trúc Clean POM Phẳng (Zero locator trong test script)
- **Gate 4:** Chống Lệch Tài Liệu AI (Zero hallucinated PageClasses)
- **Gate 5:** Danh Sách Đen File Tạm (Zero `.tmp`, heap dump làm bẩn git)
- **Gate 6:** Bảo Vệ Bí Mật & Mật Khẩu (Zero hardcoded credentials)
- **Gate 7:** Quét Lỗi Tĩnh & Bắt Test Pass Ảo (Zero 0-assert, zero sleep)
- **Gate 8:** Đo Độ Nhạy Assert Micro-Mutation (Mutation Score $\ge 80\%$)
- **Gate 9:** Điều Phối Kỹ Năng & Ngăn Xung Đột (Similarity $< 0.75$)

*(Xem chi tiết tiêu chuẩn, mã lỗi và cách khắc phục tại [docs/QUALITY_GATES.md](docs/QUALITY_GATES.md)).*

---

## 🔄 Tích Hợp CI/CD & Pre-commit Hook

```yaml
# GitHub Actions (.github/workflows/verify.yml):
- name: Run Synapse Hub Quality Gates
  uses: TeeVee998/Synapse-Hub@v2
  with:
    mode: 'target'

# Hoặc chạy trực tiếp trên bất kỳ CI nào (GitLab, Bitbucket, Jenkins):
- name: Run Synapse Hub Quality Gates
  run: npx synapse-hub verify
```

```yaml
# Pre-commit hook (.pre-commit-config.yaml):
repos:
  - repo: https://github.com/TeeVee998/Synapse-Hub
    rev: v3.0.0
    hooks:
      - id: synapse-lint
      - id: synapse-verify
```

---

## 📚 Tài Liệu Kỹ Thuật Chuyên Sâu

- 🏛️ **Kiến Trúc & Bảng So Sánh Chi Tiết:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 🛡️ **Đặc Tả 10 Cổng Chất Lượng (DoD):** [docs/QUALITY_GATES.md](docs/QUALITY_GATES.md)
- 📖 **Cẩm Nang Tra Cứu Lệnh CLI:** [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md)
- 🚀 **Hướng Dẫn Tích Hợp CI/CD:** [docs/CI_CD_INTEGRATION.md](docs/CI_CD_INTEGRATION.md)
- 🤝 **Hướng Dẫn Đóng Góp:** [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
