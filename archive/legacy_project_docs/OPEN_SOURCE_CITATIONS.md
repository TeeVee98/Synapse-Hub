# TÀI LIỆU THAM CHIẾU & CHÚ THÍCH MÃ NGUỒN MỞ (OPEN SOURCE CITATIONS)
### *Hệ Thống Kiểm Thử Tự Động DMIT (259 Test Cases)*

Tài liệu này ghi nhận chi tiết nguồn gốc xuất xứ, đường dẫn kho mã nguồn mở quốc tế (GitHub) và mục đích ứng dụng thực tế của **6 giải pháp công nghệ** được tích hợp vào dự án DMIT nhằm phục vụ vận hành AI Agent tự hành và tối ưu hóa quy trình kiểm thử tự động.

---

## 1. Danh Mục Các Kho Lưu Trữ Đã Tích Hợp

### 1.1. Graphify (Đồ Thị Tri Thức Mã Nguồn & Phân Tích Tác Động)
* **Kho lưu trữ:** [https://github.com/Graphify-Labs/graphify.git](https://github.com/Graphify-Labs/graphify.git)
* **Bản chất công nghệ:** Công cụ trích xuất AST Knowledge Graph cục bộ bằng `tree-sitter`, không tốn chi phí API hay Vector DB.
* **Thành phần tích hợp vào DMIT:**
  - Cơ sở dữ liệu đồ thị: `graphify-out/graph.json` (1.303 nodes, 2.229 edges, 398 communities).
  - Công cụ phân tích tác động kiểm thử: `tools/test_impact.py`.
  - Báo cáo kiến trúc trực quan: `graphify-out/graph.html` (2D/3D) và `graphify-out/callflow.html` (Mermaid Call Flow).
  - Quy tắc Agent: `.agents/rules/graphify.md` và Skill `.agents/skills/graphify-impact-analyzer/`.
* **Giá trị thực tế:** Cho phép khoanh vùng chính xác tập Test Cases bị ảnh hưởng khi sửa Page Class, tiết kiệm tới 95% thời gian chạy CI/CD.

---

### 1.2. Katalon Studio Agent Skills (Chuẩn Hóa Kỹ Năng AI Cho Katalon)
* **Kho lưu trữ:** [https://github.com/katalon-studio-samples/skills.git](https://github.com/katalon-studio-samples/skills.git)
* **Bản chất công nghệ:** Bộ kỹ năng chính thức từ Katalon Studio thiết kế riêng cho các AI Coding Agents.
* **Thành phần tích hợp vào DMIT:**
  - Chuẩn hóa định dạng XML và GUID UUID v4 cho Test Cases (`.tc`), Test Suites (`.ts`), và Execution Profiles (`.glbl`).
  - Từ điển API WebUI Built-in chuẩn: `.agents/skills/katalon-cli-runner/references/katalon-api.md`.
  - Quy chuẩn lập trình Custom Keyword Groovy: `.agents/skills/katalon-cli-runner/references/groovy-patterns.md`.
* **Lưu ý kiến trúc DMIT:** Dự án chỉ kế thừa chuẩn XML và API WebUI; **tuyệt đối giữ vững kiến trúc Clean POM phẳng (`BasePage.x()`)** của DMIT thay vì dùng Object Repository (`findTestObject`) phân mảnh.

---

### 1.3. Fugazi QA Automation Skills (Kỹ Nghệ Điều Tra Lỗi & Triage Flaky Test)
* **Kho lưu trữ:** [https://github.com/fugazi/test-automation-skills-agents.git](https://github.com/fugazi/test-automation-skills-agents.git)
* **Bản chất công nghệ:** Thư viện kỹ năng chuyên biệt cho QA Automation Engineer (Playwright, Selenium, ISTQB).
* **Thành phần tích hợp vào DMIT:**
  - Giao thức điều tra lỗi 4 pha: `.agents/skills/failure-autopsy-and-healing/references/qa_investigation_protocol.md`.
* **Giá trị thực tế:** Chuẩn hóa quy trình chẩn đoán lỗi test case có bằng chứng (Tái hiện $\rightarrow$ Thu thập log/screenshot $\rightarrow$ Lập giả thuyết $\rightarrow$ Sửa & Xác thực), phân biệt rõ lỗi Flaky do bất đồng bộ DOM vs Lỗi ứng dụng AUT backend thật sự.

---

### 1.4. Vercel Labs Agent Browser (Thu Nhỏ DOM & Tối Ưu Hóa Token)
* **Kho lưu trữ:** [https://github.com/vercel-labs/agent-browser.git](https://github.com/vercel-labs/agent-browser.git)
* **Bản chất công nghệ:** CLI tự động hóa trình duyệt hiệu năng cao bằng Rust qua Chrome DevTools Protocol (CDP).
* **Thành phần tích hợp vào DMIT:**
  - Hướng dẫn kỹ thuật Compact Accessibility Snapshots: `.agents/skills/playwright-live-interaction/references/compact_accessibility_snapshots.md`.
* **Giá trị thực tế:** Trích xuất cây ngữ nghĩa khả dụng kèm mã định danh ngắn gọn `@ref` (`@e1`, `@e2`...). Giảm dung lượng khảo sát DOM giao diện PrimeNG từ 25.000 tokens xuống dưới 500 tokens (tiết kiệm 95% token ngữ cảnh).

---

### 1.5. Obra Superpowers (Kỷ Luật Kỹ Thuật Phần Mềm & Verification-First)
* **Kho lưu trữ:** [https://github.com/obra/superpowers.git](https://github.com/obra/superpowers.git)
* **Bản chất công nghệ:** Framework phương pháp luận kỹ thuật phần mềm nghiêm ngặt dành cho AI Coding Agents.
* **Thành phần tích hợp vào DMIT:**
  - Quy tắc kỷ luật bắt buộc: `.agents/rules/systematic-debugging.md`.
* **Giá trị thực tế:**
  - **Zero Guesswork Debugging:** Nghiêm cấm Agent sửa code dựa trên suy đoán; bắt buộc phải có bằng chứng khách quan trước khi sửa.
  - **Verification-First:** Mọi nhiệm vụ chỉ được coi là hoàn thành sau khi vượt qua kiểm định chất lượng tự động `python3 tools/verify_all.py` (tất cả 6 Gates đều PASS).

---

### 1.6. Anthropic Agent Skills (Chuẩn Hóa Kiến Trúc Progressive Disclosure)
* **Kho lưu trữ:** [https://github.com/anthropics/skills.git](https://github.com/anthropics/skills.git)
* **Bản chất công nghệ:** Kho lưu trữ gốc của Anthropic định hình chuẩn `SKILL.md`.
* **Thành phần tích hợp vào DMIT:**
  - Áp dụng nguyên lý **Progressive Disclosure** trên toàn bộ hệ thống `.agents/skills/`: Giữ tệp `SKILL.md` tinh gọn làm mục lục điều hướng, chuyển toàn bộ tài liệu tra cứu chuyên sâu vào thư mục con `references/`.
* **Giá trị thực tế:** Ngăn chặn việc nạp tài liệu thừa làm tràn Context Window của AI Agent trong các phiên làm việc dài.

---

### 1.7. Context Engineering Skills (Kỹ Nghệ Quản Trị Ngữ Cảnh & Ngăn Chặn Context Rot)
* **Kho lưu trữ:** [https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering.git](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering.git)
* **Bản chất công nghệ:** Khung kỹ nghệ quản trị toàn diện Attention Budget và vòng đời ngữ cảnh của Agent (Observation Masking, Progressive Disclosure, KV-Cache Optimization).
* **Thành phần tích hợp vào DMIT:**
  - Quy tắc vận hành: `.agents/rules/context-engineering.md`.
  - Bộ kỹ năng chuyên sâu: `.agents/skills/filesystem-context/` (dùng đĩa làm bộ nhớ ngoài vĩnh cửu) và `.agents/skills/context-degradation/` (phát hiện và trị 5 bệnh suy thoái ngữ cảnh LLM).
* **Giá trị thực tế:** Giải quyết triệt để hiện tượng "Context Rot" và "Lost-in-the-Middle" khi chạy kiểm thử dài hạn trên 259 Test Cases, giúp Agent duy trì độ sắc bén lập luận 100% qua hàng chục lượt trao đổi.

---

### 1.8. Token Optimizer (Tối Ưu Hóa Token & Triệt Tiêu Ghost Tokens)
* **Kho lưu trữ:** [https://github.com/alexgreensh/token-optimizer.git](https://github.com/alexgreensh/token-optimizer.git)
* **Bản chất công nghệ:** Bộ công cụ quét và loại bỏ "Ghost Tokens" (token rác từ log thừa, dấu vết thực thi lặp lại và bản tóm tắt cũ).
* **Thành phần tích hợp vào DMIT:**
  - Kỹ thuật lọc rút gọn log (Observation Masking) tích hợp vào kịch bản kiểm định và quy tắc `.agents/rules/context-engineering.md`.
* **Giá trị thực tế:** Giảm từ 70% đến 90% lượng token rác phát sinh từ log chạy máy của Katalon KRE CLI và Gradle build.

---

### 1.9. LaVague (Large Action Model Web Agent & Code Generation)
* **Kho lưu trữ:** [https://github.com/lavague-ai/LaVague.git](https://github.com/lavague-ai/LaVague.git)
* **Bản chất công nghệ:** Khung kiến trúc Large Action Model (LAM) chuyển đổi ngôn ngữ tự nhiên thành kịch bản tự động hóa Selenium/Playwright bền vững thông qua mô hình World Model (tư duy luồng) + Action Engine (sinh mã thực thi).
* **Thành phần tích hợp vào DMIT:**
  - Bộ kỹ năng Agent: `.agents/skills/lam-script-generator/SKILL.md`.
  - Công cụ sinh kịch bản tự động: `tools/generate_tc_from_story.py`.
* **Giá trị thực tế:** Cho phép BA/QA mô tả kịch bản kiểm thử bằng ngôn ngữ tự nhiên (tiếng Việt/Anh); Action Engine tự động đối chiếu Knowledge Graph và sinh ra mã Clean POM Groovy chuẩn chỉnh, có khả năng chạy lại vô hạn lần trên CI/CD với 0 token LLM.

---

### 1.10. Antigravity Skill Vault (Bộ Kỹ Năng Mở Rộng Cho Testing & Code Health)
* **Kho lưu trữ:** [https://github.com/rmyndharis/antigravity-skills.git](https://github.com/rmyndharis/antigravity-skills.git)
* **Bản chất công nghệ:** Kho lưu trữ 300+ kỹ năng chuẩn hóa định dạng Agent Skills cho Google Antigravity (chuyển thể từ hệ sinh thái Claude Code Agents `wshobson/agents`).
* **Thành phần tích hợp vào DMIT (10 Skills chọn lọc & hợp nhất):**
  - **Testing & A11y:** `.agents/skills/e2e-testing-patterns/`, `.agents/skills/wcag-audit-patterns/`, `.agents/skills/tdd-orchestrator/`, `.agents/skills/bats-testing-patterns/`.
  - **Code Quality & Refactoring:** `.agents/skills/code-refactoring-refactor-clean/` (hợp nhất cả dọn dẹp nợ kỹ thuật), `.agents/skills/code-review-ai-ai-review/`.
  - **Multi-Agent & Architecture:** `.agents/skills/agent-orchestration-multi-agent-optimize/`, `.agents/skills/architecture-decision-records/`, `.agents/skills/c4-architecture-c4-architecture/`.
  - **CI/CD:** `.agents/skills/github-actions-templates/`.
* **Giá trị thực tế:** Mở rộng năng lực kiểm thử tiếp cận tiêu chuẩn quốc tế (WCAG 2.2 accessibility, TDD red-green-refactor, bash script unit test), hỗ trợ bóc tách dọn dẹp các Page Classes lớn và điều phối sub-agents an toàn tránh context bloat.

---

## 2. Bảng Ánh Xạ Tổng Thể (Integration Mapping Matrix)

| Repository Nguồn | Đường Dẫn Kho Lưu Trữ | Vị Trí Triển Khai Trong DMIT | Mục Đích Sử Dụng |
|---|---|---|---|
| **Graphify** | `github.com/Graphify-Labs/graphify` | `graphify-out/`<br/>`tools/test_impact.py`<br/>`.agents/rules/graphify.md` | Điều hướng kiến trúc & Test Impact Analysis |
| **Katalon Skills** | `github.com/katalon-studio-samples/skills` | `.agents/skills/katalon-cli-runner/references/` | Cấu trúc XML chuẩn & Tra cứu API WebUI Built-in |
| **Fugazi QA** | `github.com/fugazi/test-automation-skills-agents` | `.agents/skills/failure-autopsy-and-healing/references/` | Quy trình điều tra Flaky Test & Root-Cause Analysis |
| **Agent Browser** | `github.com/vercel-labs/agent-browser` | `.agents/skills/playwright-live-interaction/references/` | Rút gọn Accessibility-Tree & Tiết kiệm token live web |
| **Superpowers** | `github.com/obra/superpowers` | `.agents/rules/systematic-debugging.md` | Kỷ luật Zero Guesswork & Verification-First |
| **Anthropic Skills** | `github.com/anthropics/skills` | `.agents/skills/**/SKILL.md` | Chuẩn hóa Progressive Disclosure cho AI context |
| **Context Engineering** | `github.com/muratcankoylan/Agent-Skills-for-Context-Engineering` | `.agents/rules/context-engineering.md`<br/>`.agents/skills/filesystem-context/`<br/>`.agents/skills/context-degradation/`<br/>`.agents/skills/token-and-context-optimizer/` | Observation Masking, Progressive Disclosure, KV-Cache, External Memory & Anti-Degradation |
| **Token Optimizer** | `github.com/alexgreensh/token-optimizer` | `.agents/rules/context-engineering.md` | Triệt tiêu Ghost Tokens & Lọc gọn log thực thi |
| **LaVague (LAM)** | `github.com/lavague-ai/LaVague` | `.agents/skills/lam-script-generator/`<br/>`tools/generate_tc_from_story.py` | Sinh kịch bản Clean POM từ User Story tự nhiên (0 Token Replay) |
| **Antigravity Skills Vault** | `github.com/rmyndharis/antigravity-skills` | `.agents/skills/` (10 kỹ năng: e2e, tdd, wcag, bats, refactor, review, multi-agent, adr, c4, github-actions) | Mở rộng năng lực E2E, TDD, WCAG 2.2, Code Health và CI/CD |
| **Datafaker** | `github.com/datafaker-net/datafaker` | `build.gradle`<br/>`Keywords/dmit/helpers/DataGenerator.groovy` | Sinh dữ liệu kiểm thử tiếng Việt chuẩn nghiệp vụ Công Thương |
| **Pillow / Pixelmatch** | `github.com/python-pillow/Pillow` | `tools/visual_diff_canvas.py` | Kiểm thử trực quan (Visual Regression) đồ thị Canvas & GIS |
| **Aider** | `github.com/Aider-AI/aider` | `tools/repo_map.py`<br/>`tools/repo_map.txt` | Nén AST toàn bộ Page Classes thành bản đồ token-budgeted (<600 tokens) |
| **Meta Infer** | `github.com/facebook/infer` | `tools/infer_linter.py` | Quét tĩnh AST phát hiện Fake-Pass (0 assert) và khối catch nuốt lỗi |
| **Joern** | `github.com/joernio/joern` | `tools/trace_data_flow.py` | Phân tích Taint luồng dữ liệu kiểm thử (Source -> Propagate -> Teardown Sink) |

---

## 3. Khảo Sát & Đánh Giá Các Kho Mã Nguồn Mở Tự Động Hóa & AI Testing

Phần này ghi nhận các phân tích, khảo sát chuyên sâu đối với các kho lưu trữ tự động hóa kiểm thử và kiểm thử ứng dụng trí tuệ nhân tạo (AI-Powered Testing) phục vụ chiến lược phát triển dài hạn của dự án DMIT.

### 3.1. Các Framework Tự Động Hóa Trình Duyệt (Core Browser Automation)

#### 1. Playwright
* **Kho lưu trữ:** [https://github.com/microsoft/playwright](https://github.com/microsoft/playwright)
* **Bản chất công nghệ:** Nền tảng kiểm thử E2E hiện đại từ Microsoft, điều khiển trình duyệt qua WebSocket/CDP nội bộ. Hỗ trợ đa ngôn ngữ (TypeScript, Python, Java, C#), cơ chế tự động chờ (Auto-Wait), cách ly Browser Context và công cụ ghi nhận vết Trace Viewer.
* **Đánh giá áp dụng cho DMIT:** **Ứng cử viên số 1 cho lộ trình chuyển đổi dài hạn.** Dự án DMIT đã ứng dụng Playwright qua `real_e2e_runner.py` và Playwright MCP để cào cấu trúc DOM và tương tác trực tiếp. Nếu dự án muốn loại bỏ phụ thuộc vào bản quyền thương mại Katalon KRE trên CI/CD, Playwright là lựa chọn mã nguồn mở tối ưu nhất.

#### 2. Selenium WebDriver
* **Kho lưu trữ:** [https://github.com/SeleniumHQ/selenium](https://github.com/SeleniumHQ/selenium)
* **Bản chất công nghệ:** Tiêu chuẩn công nghiệp kiểm thử trình duyệt chuẩn hóa W3C lâu đời nhất thế giới.
* **Đánh giá áp dụng cho DMIT:** **Đang được vận hành gián tiếp.** Toàn bộ 259 ca kiểm thử trong Katalon Studio bản chất chạy trên lõi Java Selenium WebDriver. Mã nguồn tại `Keywords/dmit/pages/` tương thích 100% với các API của Selenium.

#### 3. Puppeteer
* **Kho lưu trữ:** [https://github.com/puppeteer/puppeteer](https://github.com/puppeteer/puppeteer)
* **Bản chất công nghệ:** Thư viện Node.js từ Google điều khiển trình duyệt Chromium qua Chrome DevTools Protocol (CDP).
* **Đánh giá áp dụng cho DMIT:** **Không khuyến khích làm E2E Framework.** Phù hợp cho tác vụ cào dữ liệu (scraping) và xuất PDF hơn là kiểm thử hồi quy 259 kịch bản. Các kỹ sư sáng lập Puppeteer đã phát triển Playwright với đầy đủ tính năng kiểm thử vượt trội hơn.

#### 4. Cypress
* **Kho lưu trữ:** [https://github.com/cypress-io/cypress](https://github.com/cypress-io/cypress)
* **Bản chất công nghệ:** Công cụ E2E chạy trực tiếp bên trong vòng lặp trình duyệt (in-browser context).
* **Đánh giá áp dụng cho DMIT:** **Không phù hợp.** Gặp rào cản kỹ thuật lớn khi xử lý các luồng phức tạp của DMIT như mở đa tab, xác thực đăng nhập cổng SSO ngoài domain, hoặc xử lý tệp tải về dung lượng lớn.

---

### 3.2. Công Nghệ AI-Driven Testing & Self-Healing

#### 5. Healenium
* **Kho lưu trữ:** [https://github.com/healenium/healenium](https://github.com/healenium/healenium)
* **Bản chất công nghệ:** Thư viện tự phục hồi (Self-Healing) cho Selenium khi gặp lỗi `NoSuchElementException`, so khớp cây DOM bằng thuật toán máy học.
* **Đánh giá áp dụng cho DMIT:** Tiềm năng về mặt ý tưởng nhưng đòi hỏi dựng hạ tầng Docker Backend và cơ sở dữ liệu PostgreSQL để lưu snapshot. Dự án DMIT đã giải quyết bài toán này gọn nhẹ hơn thông qua AI Agent tự động chẩn đoán ảnh lỗi và cập nhật trực tiếp tại mã nguồn Page Class.

#### 6. QA-Use (Browser Use)
* **Kho lưu trữ:** [https://github.com/browser-use/qa-use](https://github.com/browser-use/qa-use)
* **Bản chất công nghệ:** Giải pháp QA tự hành xây dựng trên nền tảng Browser Use + Playwright + LLM, cho phép định nghĩa kịch bản bằng ngôn ngữ tự nhiên không cần định danh selector.
* **Đánh giá áp dụng cho DMIT:** Rất giá trị cho kiểm thử khám phá (Exploratory Testing) và Smoke Test kiểm tra sức khỏe hệ thống sau triển khai. Không dùng để thay thế 259 test cases kiểm thử hồi quy vì chi phí API và độ trễ suy luận của mô hình ngôn ngữ lớn.

#### 7. Awesome AI Testing
* **Kho lưu trữ:** [https://github.com/tugkanboz/awesome-ai-testing](https://github.com/tugkanboz/awesome-ai-testing)
* **Bản chất công nghệ:** Danh mục bách khoa toàn thư được tuyển chọn (Curated List) về toàn bộ hệ sinh thái công cụ, nền tảng, bài nghiên cứu về AI trong kiểm thử phần mềm.
* **Đánh giá áp dụng cho DMIT:** Sử dụng làm tài liệu định hướng và tra cứu công nghệ phục vụ quá trình nâng cấp kiến trúc tự động hóa của dự án.

---

### 3.3. Các Thư Viện Được Tích Hợp Trực Tiếp Vào Dự Án

#### 8. Datafaker
* **Kho lưu trữ:** [https://github.com/datafaker-net/datafaker](https://github.com/datafaker-net/datafaker)
* **Vị trí tích hợp:** `build.gradle` & `Keywords/dmit/helpers/DataGenerator.groovy`
* **Hiệu quả mang lại:** Cung cấp bộ dữ liệu kiểm thử tiếng Việt chuẩn hóa theo nghiệp vụ Bộ Công Thương (Doanh nghiệp, Mã số thuế 10 số, Số điện thoại VN, Dự án quy hoạch, Địa chỉ). Đi kèm cơ chế `fitLength()` bảo đảm độ dài trường an toàn 100%, triệt tiêu hoàn toàn lỗi tràn trường (`maxlength`) trên giao diện PrimeNG và CSDL.

#### 9. Pillow & Visual Diff
* **Kho lưu trữ:** [https://github.com/python-pillow/Pillow](https://github.com/python-pillow/Pillow)
* **Vị trí tích hợp:** `tools/visual_diff_canvas.py`
* **Hiệu quả mang lại:** Thực hiện kiểm thử hồi quy trực quan (Visual Regression Testing) cho biểu đồ đồ thị Canvas và bản đồ GIS trong phân hệ Khai phá dữ liệu (`DataMiningPage` - TC-123 đến TC-247). Tự động phát hiện canvas trắng trơn (`check-blank`) và đối chiếu sai khác pixel với ảnh chuẩn (`compare`).

---

### 3.4. Khảo Sát & Đánh Giá Các Kho Kiến Thức & Cộng Đồng Khác

#### 10. DAIR.AI Prompt Engineering Guide
* **Kho lưu trữ:** [https://github.com/dair-ai/Prompt-Engineering-Guide](https://github.com/dair-ai/Prompt-Engineering-Guide) (và trang web [promptingguide.ai](https://www.promptingguide.ai/))
* **Bản chất công nghệ:** Giáo trình mở quy chuẩn thế giới (>50.000 ⭐) tổng hợp các kỹ thuật Prompting, CoT, ReAct (Reason + Act), Reflexion và RAG.
* **Đánh giá áp dụng cho DMIT:** Đóng vai trò là tài liệu tham khảo phương pháp luận tư duy cho Agent. Không thể tải trực tiếp file `SKILL.md` do được biên soạn dưới dạng tài liệu giáo trình và notebook. Các nguyên lý ReAct và suy luận tự sửa sai được ứng dụng trực tiếp vào `failure-autopsy-and-healing` và `lam-script-generator`.

#### 11. Cursor Community Plugins
* **Kho lưu trữ:** [https://github.com/cursor/community-plugins](https://github.com/cursor/community-plugins)
* **Bản chất công nghệ:** Mã nguồn nền tảng web Next.js + Supabase vận hành trang [cursor.directory](https://cursor.directory).
* **Đánh giá áp dụng cho DMIT:** Không tải về dự án vì toàn bộ dữ liệu rules và prompts nằm trên cơ sở dữ liệu cloud của tác giả thay vì lưu trong repository. Nếu cần tham khảo rules có thể tra cứu trực tiếp trên web `cursor.directory`.
