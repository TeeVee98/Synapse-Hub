---
trigger: always_on
description: Enforce rigorous engineering discipline, systematic debugging without guesswork, and verification before completion.
---

# Systematic Debugging & Verification Discipline (Superpowers Standard)

*(Inherited from `obra/superpowers`)*

This rule governs all AI Agents operating on the DMIT repository. It mandates strict engineering rigor, prohibiting intuitive guesswork and unverified declarations of completion.

---

## 1. Iron Discipline: Zero Guesswork Debugging

1. **Evidence Before Action:**
   - Never modify code based on a hunch or assumption.
   - Every bug fix or locator update must be preceded by concrete ground-truth evidence:
     - Log excerpt showing the exact failing line and exception.
     - Visual inspection of `Screenshots/FAILED_*.png`.
     - Live DOM element state verified via Playwright Live Interaction.
2. **Preserve Working Code:**
   - When fixing an issue in a Page Class or script, touch only the minimal lines required. Never rewrite working methods speculatively.

---

## 2. Verification-First & Zero False Completion

1. **Never Declare Complete Without Running Verification:**
   - Any agent claiming a fix or refactoring is finished MUST run:
     ```bash
     python3 tools/verify_all.py
     ```
   - All 7 Gates must return `PASS`. If any gate fails, the task is NOT complete.
2. **Targeted Re-Test:**
   - After modifying Page Classes, check impacted Test Cases with:
     ```bash
     python3 tools/test_impact.py --git-diff
     ```
   - Verify the affected test cases pass before handoff.
3. **Synchronize Knowledge Graph & Repo Map:**
   - Run `graphify update .` to keep the AST knowledge graph updated.
   - Run `python3 tools/repo_map.py` if any Page Class or Helper was modified.

---

## 3. Situational Tool Dispatch Matrix (Kích Hoạt Tool Tự Động Theo Tình Huống)

AI Agent **BẮT BUỘC** tự động kích hoạt các script đặc chủng tại `tools/` tùy theo ngữ cảnh thực thi:

| Tình Huống Thực Tế | Tool Phải Chạy Tự Động | Mục Đích Cụ Thể |
| :--- | :--- | :--- |
| **Bắt đầu task / Tra cứu hàm Page Class** | `tools/repo_map.txt`<br/>*(chạy `python3 tools/repo_map.py` nếu sửa class)* | Đọc bản đồ nén 500 tokens để lấy signature, cấm đọc tràn lan file 4.000 dòng. |
| **Sửa hoặc sinh mới Test Script** | `python3 tools/infer_linter.py` | Quét tĩnh AST phát hiện Fake-Pass (0 assert) và khối catch nuốt lỗi. |
| **Trước mỗi Git Commit hoặc Hoàn Thành Task** | `python3 tools/verify_all.py` | Kiểm tra toàn bộ 7 Cổng Chất Lượng DoD. |
| **Sau khi sửa đổi Page Class** | `python3 tools/test_impact.py --git-diff` | Khoanh vùng chính xác tập test case bị ảnh hưởng, không chạy lại toàn bộ 259 ca. |
| **Gặp lỗi Test Case (FAIL) khi chạy KRE** | `python3 tools/pinpoint_failure.py` | Phân tích JUnit XML xác định dòng và Exception trong 0.1s. |
| **Khi có log CLI / Gradle dài nghìn dòng** | `python3 tools/distill_log.py <log>` | Lọc bỏ 95% log rác, chỉ giữ exception và pointer (Observation Masking). |
| **Khi xử lý ngoại lệ giao diện (Overlay, Stale)** | `python3 tools/cache_resolver.py query "<error>"` | Tra cứu giải pháp 0-token từ SQLite cục bộ trước khi thử cách khác. |
| **Nghiệm thu Batch / Trước khi push CI/CD** | `python3 tools/trace_data_flow.py` | Kiểm tra Taint Analysis xem kịch bản có tạo rác dữ liệu DB (Orphan Data) không. |
| **Sát hạch năng lực tự chữa lành (Audit)** | `python3 tools/agent_canary.py --run` | Tiêm 8 failure vectors để chấm điểm MTTR và tỷ lệ tự phục hồi. |
| **Kiểm thử màn hình GIS / Canvas không có DOM** | `python3 tools/visual_diff_canvas.py` | So sánh ảnh pixel / SSIM phát hiện vẽ lệch bản đồ hoặc biểu đồ. |
| **Khi kéo code mới (`git pull` / clone mới)** | `python3 tools/cache_resolver.py init`<br/>*(Hook `post-merge` tự kích hoạt)* | Tự động đồng bộ/khởi tạo Central Agent Memory (`~/.agent_memory/global_cache.db`). |
