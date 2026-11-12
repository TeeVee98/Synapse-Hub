# Hướng Dẫn Tích Hợp CI/CD — Synapse-Hub Enterprise QA

[🇻🇳 Tiếng Việt](CI_CD_INTEGRATION.md) | [🇬🇧 English Edition](CI_CD_INTEGRATION.en.md)

Tài liệu này hướng dẫn cách đưa các cổng kiểm định chất lượng của Synapse Hub (`verify_all.py`, `infer_linter`, bộ micro-mutation và kiểm tra Clean POM) trực tiếp vào đường ống CI/CD của dự án test mà không phụ thuộc vào môi trường máy cá nhân.

---

## 1. Tích Hợp Chạy Ngay Qua Lệnh NPX (Khuyên Dùng)

Do `synapse-hub` được phát hành sẵn trên NPM Registry và GitHub Packages, pipeline CI của dự án không cần clone repo Hub về máy. Lệnh `npx` sẽ tự động tải và kích hoạt CLI tức thì.

### Đường Ống GitHub Actions (`.github/workflows/synapse_qa.yml`)

```yaml
name: Synapse QA Quality Gate

on:
  push:
    branches: [ main, develop, master ]
  pull_request:
    branches: [ main, develop, master ]

jobs:
  quality-gate:
    name: Kiểm Định 10 Cổng Chất Lượng DoD
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Mã Nguồn Dự Án
        uses: actions/checkout@v4

      - name: Cài Đặt Node.js & Python
        uses: actions/setup-node@v4
        with:
          node-version: 20
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Chạy Kiểm Định 10 Cổng Chất Lượng
        run: npx synapse-hub verify
```

### Đường Ống GitLab CI (`.gitlab-ci.yml`)

```yaml
synapse-qa-gate:
  stage: test
  image: node:20-bookworm
  before_script:
    - apt-get update && apt-get install -y python3 python3-pip
  script:
    - npx synapse-hub verify
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

---

## 2. Tích Hợp Bằng Docker All-in-One Container (Dành Cho Doanh Nghiệp)

Với các môi trường runner cô lập, Kubernetes, OpenShift, GitLab Runner hoặc Jenkins không muốn cài đặt công cụ lên máy chủ host, hãy sử dụng **Synapse-Hub All-in-One Container Image** chính thức:

- **Địa chỉ Registry**: `ghcr.io/teevee98/synapse-hub:latest`
- **Môi trường tích hợp sẵn**: Python 3.12, Node.js 20, OpenJDK Headless, Chromium Headless và toàn bộ thư viện Playwright, Git, Bash.

### A. Chạy Trực Tiếp 1 Dòng Lệnh Với Docker

Gắn thư mục dự án test của bạn vào `/workspace` và gọi trực tiếp các cổng kiểm định chất lượng:

```bash
# Kiểm định 10 Cổng Chất Lượng DoD
docker run --rm -v $(pwd):/workspace ghcr.io/teevee98/synapse-hub verify

# Quét lỗi tĩnh Meta Infer-style và test pass ảo
docker run --rm -v $(pwd):/workspace ghcr.io/teevee98/synapse-hub lint

# Báo cáo kiểm toán sức khỏe dự án 5-trong-1
docker run --rm -v $(pwd):/workspace ghcr.io/teevee98/synapse-hub analyze
```

### B. Đường Ống GitLab CI (`.gitlab-ci.yml`) Dùng Docker

```yaml
synapse-docker-gate:
  stage: test
  image:
    name: ghcr.io/teevee98/synapse-hub:latest
    entrypoint: [""]
  script:
    - synapse-hub verify
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

### C. Jenkins Declarative Pipeline (`Jenkinsfile`)

```groovy
pipeline {
    agent {
        docker {
            image 'ghcr.io/teevee98/synapse-hub:latest'
            args '-v ${WORKSPACE}:/workspace'
        }
    }
    stages {
        stage('Quality Gate DoD') {
            steps {
                sh 'synapse-hub verify'
            }
        }
    }
}
```

### D. Khởi Chạy Nhanh Cho Developer Với Docker Compose

Gắn thư mục dự án test vào `./target` và chạy kiểm tra tức thì:

```bash
# Chạy kiểm định 10 Cổng Chất Lượng DoD
docker compose run --rm verify

# Chạy linter kiểm tra lỗi tĩnh
docker compose run --rm lint

# Mở shell tương tác trong container để debug
docker compose run --rm shell
```

---

## 3. Tích Hợp Dạng Git Submodule (Dành Cho Mạng Nội Bộ / Không Có Internet)

Nếu hệ thống mạng nội bộ công ty bị chặn truy cập ra ngoài internet hoặc NPM registry công khai, bạn có thể gắn `Synapse-Hub` như một Git Submodule bên trong repo của dự án test:

```bash
# Thêm submodule vào thư mục dự án test
git submodule add https://github.com/TeeVee98/Synapse-Hub.git .synapse-hub
```

Trong file cấu hình pipeline CI:
```bash
git submodule update --init --recursive
python .synapse-hub/tools/verify_all.py
```

---

## 4. Cài Đặt Trực Tiếp Bằng Pip Từ Git

Với các runner CI đã có sẵn môi trường Python 3.10+, bạn có thể cài đặt `synapse-hub` trực tiếp từ Git repository:

```bash
pip install git+https://github.com/TeeVee98/Synapse-Hub.git
agent-qa verify
```

---

## 5. Các Lệnh Thường Dùng Trên CI

| Lệnh NPX | Lệnh Docker Container | Mục Đích | Điều Kiện Vượt Qua / Mã Thoát |
| :--- | :--- | :--- | :--- |
| `npx synapse-hub verify` | `docker run --rm -v $(pwd):/workspace ghcr.io/teevee98/synapse-hub verify` | Chạy toàn diện 10 Cổng Chất Lượng DoD | Trả về `0` nếu toàn bộ PASS; báo lỗi khác 0 nếu có bất kỳ cổng nào FAIL. |
| `npx synapse-hub lint` | `docker run --rm -v $(pwd):/workspace ghcr.io/teevee98/synapse-hub lint` | Bắt lỗi tĩnh Meta Infer-style và test pass ảo | Fail ngay nếu có test 0 câu assert hoặc try-catch nuốt lỗi. |
| `npx synapse-hub mutate --min-score 80` | `docker run --rm -v $(pwd):/workspace ghcr.io/teevee98/synapse-hub mutate --min-score 80` | Kiểm tra độ nhạy của các câu assert bằng Micro-Mutation | Fail nếu điểm diệt đột biến của test < 80%. |
| `npx synapse-hub analyze` | `docker run --rm -v $(pwd):/workspace ghcr.io/teevee98/synapse-hub analyze` | Báo cáo kiểm toán sức khỏe dự án 5-trong-1 | Xuất điểm đánh giá và file báo cáo JSON/Markdown cho team. |
