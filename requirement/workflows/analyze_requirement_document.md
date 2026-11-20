---
description: Requirement ambiguity, gap detection, and boundary verification.
skills:
  - rbt-manual-testing
---

# /analyze_requirement_document — Requirement Ambiguity & Gap Analysis

Scans and audits functional specifications, user stories, or PRDs to detect defects, contradictions, and missing edge cases early in the lifecycle.

---

## 4-Step Analysis Pipeline

1. **Happy Path & Flow Extraction:** Extract primary user journeys and business outcomes.
2. **Ambiguity Detection:** Identify vague phrases ("fast response", "system should handle errors", "user-friendly"), unstated timeout intervals, unhandled edge conditions, and conflicting rules.
3. **Gap Analysis:** Highlight missing alternate paths, unauthorized user flows, data volume constraints, and concurrency scenarios.
4. **Numbered Q&A Register:** Generate an actionable register of questions (`Q1, Q2, Q3...`) with context and proposed default assumptions for product owner / BA sign-off.

---

## Mandatory Shift-Left Q&A Inquiries (Forms & Payment Flows)

Whenever the analyzed specification involves input forms or checkout/payment/transaction flows, the Q&A Register (`Q1, Q2...`) MUST include the following two baseline inquiries:

1. **Whitespace & Trim Policy (Input Forms):**
   - *Inquiry:* Input text có tự động `trim()` khoảng trắng đầu/cuối trước khi kiểm tra `minlength`/`maxlength` và lưu DB không, và hệ thống có từ chối chuỗi chỉ gồm toàn khoảng trắng (`"   "`) trên các trường bắt buộc (`required`) không?
   - *Default Assumption:* Bắt buộc chặn chuỗi toàn dấu cách trên trường bắt buộc; tự động `trim()` khoảng trắng đầu/cuối trước khi lưu DB.
2. **Payment UI Latency & Redirect Interrupt Policy (Payment / Transaction Flows):**
   - *Inquiry:* Khi mạng chậm (độ trễ 3–5 giây) hoặc người dùng bấm Back / F5 / đóng tab trong lúc đang chuyển hướng sang cổng thanh toán hoặc chờ callback, nút thanh toán có khóa `disabled` ngay không, timeout sau bao lâu, và trạng thái đơn hàng được đối soát (`Pending`/`Failed`/`Success`) như thế nào để ngăn chặn trừ tiền 2 lần?
   - *Default Assumption:* Khóa nút thanh toán ngay sau lần click đầu tiên kèm `Idempotency-Key`; giữ trạng thái `Pending` khi bị gián đoạn trình duyệt để đối soát an toàn.
