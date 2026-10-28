---
trigger: always_on
description: Mandatory Dual Remote and Privacy Push Protocol strictly enforcing private assets isolation between personal GitHub and company SCM.
---

# DUAL REMOTE & PRIVACY PUSH PROTOCOL (MANDATORY RULE)

> **Mục đích:** Bảo vệ 100% bí quyết trí tuệ (AI Agents, Skills, Workflows, Prompts) thuộc quyền sở hữu riêng của tác giả. Tuyệt đối không để lộ lên SCM công ty.

---

## 1. Bản Đồ Phân Định Remotes

| Remote | Mục đích | URL | Nội dung được phép |
| :--- | :--- | :--- | :--- |
| `github` | **Kho lưu trữ cá nhân (Tác giả)** | `https://github.com/TeeVee998/VNPT-DMIT.git` | **FULL (100%)**: Toàn bộ `.agents/`, tất cả các file markdown AI (`AGENTS.md`, `AI_REPLICATION_GUIDE.md`, `PROJECT_STATE.md`, v.v.), `tools/`, toàn bộ lịch sử commit chi tiết. |
| `origin` | **SCM Công ty (VNPT DevOps)** | `https://scm-devops.vnpt.vn/it.mds/autotest/dmit.git` | **CLEAN ONLY**: Mã nguồn kiểm thử thuần túy (259 Test Cases, 30 Test Suites, Keywords POM). **TUYỆT ĐỐI CẤM** `.agents/`, mọi file `.md` liên quan đến Agent/AI, lịch sử commit AI. |

---

## 2. Danh Sách Tài Liệu Markdown Hợp Chuẩn (Documentation Whitelist)

Để bảo mật tuyệt đối, chỉ có đúng **7 tài liệu kỹ thuật nghiệp vụ chuẩn** sau đây được phép đẩy lên SCM công ty:
1. `README.md` (Tổng quan dự án & cách chạy)
2. `HDSD.md` (Hướng dẫn sử dụng & xử lý giao diện Katalon)
3. `FINAL_REPORT.md` (Báo cáo nghiệm thu 259 ca kiểm thử - đã chuẩn hóa văn phong QA)
4. `POM_REFACTORING_PLAN.md` (Tài liệu kiến trúc Clean POM)
5. `CICD_GUIDE.md` (Cẩm nang vận hành CI/CD pipeline)
6. `ONBOARDING.md` (Hướng dẫn thiết lập môi trường)
7. `KNOWN_ISSUES.md` (Sổ tay quản lý lỗi AUT)

> 🚫 **MỌI FILE `.md` KHÁC** (bao gồm `AGENTS.md`, `OPEN_SOURCE_CITATIONS.md`, `AI_*.md`, `FUTURE_*.md`, `PROJECT_STATE.md`, toàn bộ file `.md` trong `.agents/`, các file nháp/prompt/báo cáo tạm) đều được coi là **Private Asset** và **TỰ ĐỘNG BỊ LOẠI BỎ** khỏi nhánh đẩy lên SCM công ty!

---

## 2. Kích Hoạt Tự Động (Trigger Words)

Khi người dùng ra bất kỳ lệnh nào như:
- *"push lên"*, *"push code"*, *"đẩy code"*, *"push git"*, *"push đi"*, *"đẩy lên"*...

AI Agent **TỰ ĐỘNG THỰC HIỆN** quy trình Dual Push 3 bước:

### Bước 1: Commit & Push lên GitHub Cá Nhân (`github`)
```powershell
git add -A
git commit -m "<conventional-commit-message>"
git push github main
```
*Đảm bảo kho cá nhân luôn lưu trữ đầy đủ toàn bộ kỹ năng, prompt và công việc mới nhất.*

### Bước 2: Đồng Bộ Nhánh Sạch & Push lên SCM Công Ty (`origin`)
```powershell
# 1. Chuyển sang nhánh sạch
git checkout scm-clean

# 2. Đồng bộ các file code test từ main (loại bỏ hoàn toàn .agents và AI docs)
git checkout main -- "Test Cases" Scripts "Test Suites" Keywords Profiles Data\ Files Include settings .env.example .gitlab-ci.yml .github CICD_GUIDE.md HDSD.md ONBOARDING.md POM_REFACTORING_PLAN.md README.md FINAL_REPORT.md KNOWN_ISSUES.md DMIT.prj build.gradle

# 3. Tạo commit sạch kế thừa trực tiếp từ origin/main (không lưu lịch sử commit AI)
$tree = (git write-tree).Trim()
$parent = (git rev-parse origin/main).Trim()
$cleanCommit = (git commit-tree $tree -p $parent -m "feat: sync latest DMIT automation test suite (259 Test Cases, 30 Test Suites)").Trim()
git reset --hard $cleanCommit

# 4. Push lên SCM công ty
git push origin scm-clean:main
```

### Bước 3: Quay Về Nhánh `main` Cục Bộ
```powershell
git checkout main
```
*Giữ nguyên môi trường làm việc đầy đủ kỹ năng cho tác giả trên máy cục bộ.*

---

## 3. Kỷ Luật Sắt Đối Với SCM Công Ty
1. **KHÔNG BAO GIỜ** gõ `git push origin main` từ nhánh `main` chứa `.agents/`.
2. **KHÔNG BAO GIỜ** để lọt file `.agents/` hay nhắc tới Agent/Swarm/Skill trong tài liệu đẩy lên SCM công ty.
3. Nếu người dùng chỉ định rõ:
   - *"chỉ push lên github"* -> Chỉ chạy Bước 1.
   - *"chỉ push lên scm"* -> Chỉ chạy Bước 2 & 3.
   - *"push lên / đẩy lên"* (mặc định) -> Tự động chạy cả 3 bước.
