# Security & Pentest Testing Invariants (5-Layer Safety Gate)

> Rule chốt chặn bắt buộc khi thực thi `security-dast-sentinel` hoặc `skillspector-security-guard` trong Synapse-Hub.
> **Runtime Enforcement Engine:** Toàn bộ Layer 1 & Layer 2 được kiểm soát và cưỡng chế qua `tools/pentest_scope_guard.py` (`PentestScopeGuard`).

## 1. Layer 1 — Scope & Production Blocklist (Allowlist Gate)
* Mọi script DAST/Fuzzing/Pentest (Burp Suite, OWASP ZAP, Nuclei, Python) bắt buộc tích hợp `PentestScopeGuard` (`tools/pentest_scope_guard.py`), đọc `TARGET_BASE_URL` và kiểm tra khớp với `ALLOWED_PENTEST_HOSTS`.
* **Cơ chế Fail-Closed / Mặc định từ chối:** Nếu `ALLOWED_PENTEST_HOSTS` trống, toàn bộ quét chủ động bị ngắt.
* **Từ chối thực thi ngay** nếu URL mục tiêu thuộc môi trường Production (`prod`, `live`, tên miền chính thức chưa nằm trong `ALLOWED_PENTEST_HOSTS`), hoặc trỏ tới AWS Metadata (`169.254.169.254`) / RFC1918 internal IPs trái phép.
* Mọi chuyển hướng (HTTP Redirect 301/302) đều phải qua `validate_redirect` để chống SSRF bounce.
* Bắt buộc có cờ xác nhận `--confirm-pentest-scope` hoặc `PENTEST_CONSENT_ACKNOWLEDGED=1` trước khi chạy quét chủ động. Mọi lần kiểm tra được ghi vào audit trail `.synapse/pentest_audit.log`.

## 2. Layer 2 — Rate-Limit & Concurrency Cap
* Thực thi qua `PentestRateLimiter`: Giới hạn cứng tốc độ gửi request: tối đa `5–10 req/s` và tối đa `3–5` luồng song song (trừ bài test Rate-Limit có xác nhận riêng).
* Bắt buộc đặt `timeout <= 10s` cho mọi HTTP request và tự động kích hoạt Circuit Breaker ngắt script nếu gặp `5xx` hoặc `429` liên tiếp vượt ngưỡng.

## 3. Layer 3 — Non-Destructive PoC & Account Isolation
* Chỉ dùng payload chứng minh lỗ hổng vô hại (SQLi đọc an toàn, canary string, time-delay nhỏ). Cấm tuyệt đối payload xóa/sửa dữ liệu (`DROP`, `DELETE`, `UPDATE` không điều kiện) hoặc gây DoS.
* Kiểm thử phân quyền chéo (BOLA/IDOR) chỉ được sử dụng cặp tài khoản test cô lập (`PENTEST_USER_A`, `PENTEST_USER_B`), không chạm dữ liệu người dùng thật.

## 4. Layer 4 — Script Secret Protection & SAST Check
* Cấm hardcode Token, Session Cookie, API Key mục tiêu trong script pentest; phải nạp từ `.env` (đã khai báo trong `.gitignore`).
* Kết hợp rà soát nhanh lỗ hổng cấu hình tĩnh (`CORS *`, thiếu CSP/HSTS, lộ secret) trên mã nguồn nếu có quyền đọc repo.

## 5. Layer 5 — Sanitized Evidence Standard
* Mọi lỗ hổng báo cáo phải kèm đủ: Severity (Critical/High/Medium/Low), cặp HTTP Request/Response (hoặc lệnh `curl`) tái hiện được ngay, và hướng dẫn vá lỗi.
* Bắt buộc che mờ (mask) JWT, Cookie, Password, PII trước khi ghi log hoặc xuất báo cáo.
