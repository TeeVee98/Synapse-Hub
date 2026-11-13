# Context-Aware Stack Router & Token-Minimal Loader

> Bổ sung vào `.agents/rules/` của Synapse-Hub để giảm tối đa tiêu thụ token và dùng chung được cho mọi dự án.

## 1. Lazy-Loading Rule & Skill (Chỉ nạp thứ dự án cần)
Khi bắt đầu phiên làm việc, AI Agent **chỉ quét thư mục gốc tối đa 2 cấp** và chỉ đọc đúng nhóm rule/skill khớp với dự án hiện tại (KHÔNG nạp toàn bộ 53 skill hay rule của nền tảng khác):

* **Web / API (`playwright.config.*`, `cypress.config.*`, `openapi.*`, `pytest`, `jest`):** Chỉ nạp `mandatory-playwright-live.md` (nếu dùng Playwright) + `clean-pom-crafter` + `api-network-mocking-interception`.
* **Mobile (`appium`, `*.xcodeproj`, `build.gradle`):** Chỉ nạp `mobile_appium_rules.md` + `clean-pom-crafter` (theo chuẩn SOM). Bỏ qua `mandatory-playwright-live.md`.
* **Performance (`k6`, `*.jmx`, `locustfile.py`):** Chỉ nạp `performance_testing_rules.md` + `backend-load-and-stress-patterns`.
* **Security (`burp`, `zap`, `nuclei`, pentest/DAST):** Chỉ nạp `security_testing_rules.md` + `security-dast-sentinel` + `skillspector-security-guard`.

## 2. Adaptive Verification (Fast Mode vs Full Gate)
* **Fast Mode (Sửa nhanh / viết 1–2 test case):** Kiểm tra tĩnh (0 sleep cứng, 0 secret, có `assert`) và chạy lệnh test gốc cho **đúng tệp vừa sửa** đạt `Exit Code 0`.
* **Full Gate (Chốt PR / Release):**
  * Nếu dự án có `tools/verify_all.py` (môi trường Synapse-Hub đầy đủ): chạy `python3 tools/verify_all.py`.
  * Nếu là dự án bên ngoài không có `tools/verify_all.py`: chạy toàn bộ test suite bằng lệnh gốc trong `package.json` / `pyproject.toml` / `Makefile` và quét rò rỉ secret.
