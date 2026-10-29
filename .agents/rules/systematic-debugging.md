---
trigger: always_on
description: Enforce rigorous engineering discipline, systematic debugging without guesswork, and verification before completion.
---

# Systematic Debugging & Verification Discipline (Superpowers Standard)

*(Inherited from `obra/superpowers`)*

This rule governs all AI Agents operating on the repository. It mandates strict engineering rigor, prohibiting intuitive guesswork and unverified declarations of completion.

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

## 3. Situational Tool Dispatch Matrix & Zero-Command Autonomy

> 🚀 **Zero-Command Autonomous Invariant (Người Dùng Không Cần Nhớ Lệnh):**  
> Người dùng **KHÔNG BAO GIỜ** phải nhớ cú pháp hoặc gõ tay các lệnh công cụ (`agent-qa setup`, `agent-qa analyze`, `verify_all.py`...).  
> AI Agent **BẮT BUỘC TỰ ĐỘNG nhận diện ngữ cảnh và kích hoạt ngầm** các công cụ bên dưới ngay khi phát sinh tình huống.  
>  
> 🎯 **Nguyên Tắc Kích Hoạt Đúng Lúc (On-Demand Activation — Không Chạy Tràn Lan):**  
> Toàn bộ công cụ gán cho AI và Subagent là **vũ khí theo tình huống**, **TUYỆT ĐỐI KHÔNG bắt buộc phải chạy tất cả cùng lúc**. Chỉ mở túi đồ nghề lấy đúng công cụ ra khi và chỉ khi phát sinh nhu cầu thực tế (ví dụ: test rớt mới gọi `auto_heal`, dự án mới mới gọi `setup_project`, có breaking change mới gọi `api_drift_sentinel`).

| Context / Trigger | Mandatory Tool | Specific Objective |
| :--- | :--- | :--- |
| **New project / Missing `PROJECT_AI_GUIDE.md` / Bắt đầu dự án mới** | `python3 tools/setup_project.py [target]` | Tự động hóa 100%: Nhận diện framework (Playwright/Katalon/Pytest), sinh `PROJECT_AI_GUIDE.md`, cài Git hook `pre-push`, trích xuất `repo_map.txt`, chạy audit ban đầu. |
| **User requests: "phân tích dự án" / "phân tích lại" / "project audit"** | `python3 tools/analyze_project.py [target]` | Execute comprehensive 5-in-1 health audit, sync repo_map, infer_linter, data_flow, verify_all & generate PROJECT_HEALTH_REPORT.md.<br/>**Post-Action:** Stage, commit & push updated project files (`PROJECT_HEALTH_REPORT.md`, `repo_map.txt`) to git. |
| **Starting task / Querying Page Class methods** | `tools/repo_map.txt`<br/>*(run `python3 tools/repo_map.py` if classes changed)* | Read compressed 500-token map for signatures; avoid reading 4,000-line files. |
| **Creating or updating Test Scripts** | `python3 tools/infer_linter.py` | Run AST scan for Fake-Pass (0 asserts) and empty catch blocks. |
| **Before Git Commit or Completing Task** | `python3 tools/verify_all.py` | Validate all 7 Quality Gates DoD. |
| **After modifying Page Classes** | `python3 tools/test_impact.py --git-diff` | Scope impacted test cases; avoid re-running entire test suites. |
| **When Test FAILS in CLI/KRE** | `python3 tools/pinpoint_failure.py` | Parse JUnit XML to identify exact failing line and exception in 0.1s. |
| **When CLI / Gradle logs are verbose** | `python3 tools/distill_log.py <log>` | Filter 95% noise; preserve only actionable stacktraces and pointers. |
| **Handling UI exceptions (Overlay, Stale)** | `python3 tools/cache_resolver.py query "<error>"` | Lookup 0-token solution from local SQLite memory cache before improvising. |
| **Pre-Push / Suite Acceptance** | `python3 tools/trace_data_flow.py` | Run Taint Analysis to verify no orphan database junk remains uncleaned. |
| **Canary Self-Healing Audit** | `python3 tools/agent_canary.py --run` | Inject 8 failure vectors to benchmark MTTR and autonomous recovery rate. |
| **Testing GIS Canvas / Chart without DOM** | `python3 tools/visual_diff_canvas.py` | Compare pixel / SSIM to detect visual rendering regression. |
| **Pulling code / New clone** | `python3 tools/cache_resolver.py init` | Automatically sync Central Agent Memory (`~/.agent_memory/global_cache.db`). |
