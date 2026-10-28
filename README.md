# ≡ƒºá AI Agent Skills & Intelligence Hub

> **Kho l╞░u trß╗» trung t├óm c├íc Kß╗╣ n─âng (Skills), Quy tß║»c (Rules), C├┤ng cß╗Ñ (Tools) v├á Quy tr├¼nh tß╗▒ ─æß╗Öng h├│a (Workflows) cho Trß╗ú l├╜ AI (Google Antigravity / Cursor / Windsurf / Claude Code).**

---

## ≡ƒîƒ 1. Tß╗òng quan & Mß╗Ñc ─æ├¡ch Kiß║┐n tr├║c

Repository n├áy ─æ├│ng vai tr├▓ l├á **"Bß╗Ö n├úo d├╣ng chung" (Shared Intelligence Core)**, t├ích biß╗çt ho├án to├án khß╗Åi m├ú nguß╗ôn cß╗ºa tß╗½ng dß╗▒ ├ín cß╗Ñ thß╗â.

```mermaid
flowchart TD
    subgraph Hub["≡ƒºá agent-skills (Intelligence Core)"]
        Skills[".agents/skills/ (26 Skills)"]
        Rules[".agents/rules/ (7 Rules)"]
        Tools["tools/ (20+ Python Tools)"]
        Workflows[".agents/workflows/"]
    end

    subgraph ChatSession["≡ƒÆ¼ AI Agent Workspace / Chat Session"]
        Hub -->|Mount/Add Workspace| ChatSession
    end

    subgraph Projects["≡ƒôü C├íc Dß╗▒ ├ün Ri├¬ng Biß╗çt (Target Projects)"]
        DMIT["D:\\DMIT<br/>(Chß╗ë c├│ PROJECT_AI_GUIDE.md + Test Code)"]
        ODP["D:\\ODP<br/>(Chß╗ë c├│ PROJECT_AI_GUIDE.md + App Code)"]
        EDIG["D:\\vnpt-edig-automation<br/>(Chß╗ë c├│ PROJECT_AI_GUIDE.md + Test Code)"]
        Other["D:\\... (Dß╗▒ ├ín mß╗¢i)"]
    end

    DMIT -->|Mount Workspace| ChatSession
    ODP -.->|Mount Workspace| ChatSession
    EDIG -.->|Mount Workspace| ChatSession
    Other -.->|Mount Workspace| ChatSession
```

### Lß╗úi ├¡ch cß╗æt l├╡i:
1. **D├╣ng chung ─æa dß╗▒ ├ín (Cross-Project Reusability):** Mß╗Öt lß║ºn ph├ít triß╗ân skill hay tß╗æi ╞░u tool c├│ thß╗â ├íp dß╗Ñng ngay cho DMIT, ODP, eDiG, v.v.
2. **Bß║úo mß║¡t m├ú nguß╗ôn c├┤ng ty (Privacy & Clean SCM):** Repository dß╗▒ ├ín c├┤ng ty ho├án to├án sß║ích sß║╜, kh├┤ng chß╗⌐a prompt hay AI skill c├í nh├ón.
3. **Quß║ún l├╜ tß║¡p trung (Single Source of Truth):** Dß╗à d├áng n├óng cß║Ñp, th├¬m skill mß╗¢i, ─æß╗ông bß╗Ö Global Memory Cache tß║íi mß╗Öt n╞íi duy nhß║Ñt.
4. **Nhß║╣ & Tinh gß╗ìn:** Dß╗▒ ├ín mß╗Ñc ti├¬u chß╗ë cß║ºn ─æ├║ng **1 file duy nhß║Ñt** h╞░ß╗¢ng dß║½n AI (`PROJECT_AI_GUIDE.md`).

---

## ≡ƒÜÇ 2. C├ích Sß╗¡ Dß╗Ñng Trong Phi├¬n Chat (How to Mount)

### B╞░ß╗¢c 1: Mß╗ƒ phi├¬n l├ám viß╗çc ─æa th╞░ mß╗Ñc (Multi-Root Workspace)
Trong IDE (Google Antigravity / VS Code / Cursor):
1. Mß╗ƒ th╞░ mß╗Ñc dß╗▒ ├ín cß╗ºa bß║ín (v├¡ dß╗Ñ: `D:\DMIT`).
2. Th├¬m th╞░ mß╗Ñc `D:\agent-skills` v├áo Workspace (`File` -> `Add Folder to Workspace...`).
3. Trong giao diß╗çn chat cß╗ºa AI, AI sß║╜ tß╗▒ ─æß╗Öng nhß║¡n diß╗çn cß║ú 2 th╞░ mß╗Ñc:
   - **`D:\agent-skills`**: ─Éß╗ìc to├án bß╗Ö 26 Skills, 7 Rules, v├á c├íc Python Tools.
   - **Th╞░ mß╗Ñc dß╗▒ ├ín**: ─Éß╗ìc file `PROJECT_AI_GUIDE.md` ─æß╗â nß║»m r├╡ ngß╗» cß║únh nghiß╗çp vß╗Ñ cß╗ºa dß╗▒ ├ín ─æ├│.

### B╞░ß╗¢c 2: Thiß║┐t lß║¡p file h╞░ß╗¢ng dß║½n trong dß╗▒ ├ín mß╗Ñc ti├¬u
Trong mß╗ùi dß╗▒ ├ín ri├¬ng biß╗çt, tß║ío file `PROJECT_AI_GUIDE.md` (tham khß║úo mß║½u tß║íi `templates/PROJECT_AI_GUIDE_TEMPLATE.md`):
- T├¬n hß╗ç thß╗æng (AUT) & ─æ╞░ß╗¥ng dß║½n m├┤i tr╞░ß╗¥ng (URL, Test, Staging, Prod).
- T├ái khoß║ún ─æ─âng nhß║¡p kiß╗âm thß╗¡.
- Cß║Ñu tr├║c th╞░ mß╗Ñc m├ú nguß╗ôn / POM / Test Suites.
- C├íc lß╗çnh chß║íy kiß╗âm thß╗¡ ─æß║╖c th├╣ (KRE CLI, Playwright, Maven, Gradle).

---

## ≡ƒôª 3. Danh Mß╗Ñc Kß╗╣ N─âng & Quy Tß║»c (Catalog)

### 3.1. Danh mß╗Ñc 22 Kß╗╣ n─âng (.agents/skills/)

| STT | T├¬n Kß╗╣ N─âng (Skill) | Phß║ím Vi Hoß║ít ─Éß╗Öng |
|:---:|---|---|
| 1 | `clean-pom-crafter` | Chuß║⌐n h├│a Clean Page Object Model, Flat Architecture, Dynamic `uniqueCode`. |
| 2 | `playwright-live-interaction` | T╞░╞íng t├íc trß╗▒c tiß║┐p headless DOM/AOM, bypass PrimeNG overlay, x├íc thß╗▒c zero-second. |
| 3 | `self-healing-locator` | Tß╗▒ phß╗Ñc hß╗ôi locator bß║▒ng c├óy Semantic Accessibility (AOM), Role > Label > TestId. |
| 4 | `failure-autopsy-and-healing` | Kh├ím nghiß╗çm tß╗¡ thi lß╗ùi tß╗½ screenshot `FAILED_*.png` v├á Allure report, tß╗▒ v├í m├ú. |
| 5 | `antigravity-test-sentinel` | Verification-First gatekeeper, chß║╖n tuy├¬n bß╗æ ho├án th├ánh nß║┐u test ch╞░a pass exit code 0. |
| 6 | `katalon-cli-runner` | ─Éiß╗üu phß╗æi thß╗▒c thi headless KRE CLI, Community mode v├á sinh b├ío c├ío Allure. |
| 7 | `lam-script-generator` | Large Action Model, chuyß╗ân ─æß╗òi User Story sang 100% test script kh├┤ng token replay. |
| 8 | `token-and-context-optimizer` | Tß╗æi ╞░u token, lß╗ìc log r├íc, off-context memory cache v├á n├⌐n ngß╗» cß║únh. |
| 9 | `agent-orchestration-multi-agent-optimize` | ─Éiß╗üu phß╗æi multi-agent swarm, c├ón bß║▒ng tß║úi v├á gi├ím s├ít chi ph├¡ token. |
| 10 | `api-spec-to-e2e-matrix` | Chuyß╗ân ─æß╗òi OpenAPI/Swagger sang ma trß║¡n kiß╗âm thß╗¡ E2E ph├ón v├╣ng t╞░╞íng ─æ╞░╞íng. |
| 11 | `architecture-decision-records` | Soß║ín thß║úo v├á quß║ún l├╜ t├ái liß╗çu kiß║┐n tr├║c kß╗╣ thuß║¡t (ADR). |
| 12 | `bats-testing-patterns` | Thiß║┐t kß║┐ kiß╗âm thß╗¡ tß╗▒ ─æß╗Öng cho Shell Scripts v├á CI/CD pipelines. |
| 13 | `c4-architecture-c4-architecture` | Ph├ón t├¡ch v├á sinh s╞í ─æß╗ô kiß║┐n tr├║c C4 Model tß╗½ m├ú nguß╗ôn hiß╗çn hß╗»u. |
| 14 | `code-refactoring-refactor-clean` | T├íi cß║Ñu tr├║c code chuy├¬n s├óu, khß╗¡ code smells, nß╗ú kß╗╣ thuß║¡t v├á chuß║⌐n SOLID. |
| 15 | `code-review-ai-ai-review` | Kß║┐t hß╗úp ph├ón t├¡ch t─⌐nh v├á AI Review vß╗ü bß║úo mß║¡t, hiß╗çu n─âng v├á kiß║┐n tr├║c. |
| 16 | `context-degradation` | Chß║⌐n ─æo├ín v├á ph├▓ng ngß╗½a hiß╗çn t╞░ß╗úng Lost-in-the-Middle, suy tho├íi ngß╗» cß║únh. |
| 17 | `e2e-testing-patterns` | Best practices kiß╗âm thß╗¡ E2E vß╗¢i Playwright v├á Cypress. |
| 18 | `filesystem-context` | Quß║ún l├╜ scratchpad tr├¬n ß╗ò ─æ─⌐a, l╞░u trß╗» trß║íng th├íi bß╗ün vß╗»ng ngo├ái prompt. |
| 19 | `github-actions-templates` | Mß║½u pipeline CI/CD GitHub Actions chuß║⌐n sß║ún xuß║Ñt. |
| 20 | `graphify-impact-analyzer` | Ph├ón t├¡ch ─æß╗ô thß╗ï tri thß╗⌐c AST Knowledge Graph v├á khoanh v├╣ng ß║únh h╞░ß╗ƒng. |
| 21 | `tdd-orchestrator` | ─Éiß╗üu phß╗æi kß╗╖ luß║¡t TDD (Red-Green-Refactor). |
| 22 | `wcag-audit-patterns` | ─É├ính gi├í v├á kiß╗âm thß╗¡ ─æß╗Ö t╞░╞íng th├¡ch tiß║┐p cß║¡n theo ti├¬u chuß║⌐n WCAG 2.2. |

### 3.2. Danh mß╗Ñc 7 Quy tß║»c Cß╗æt l├╡i (.agents/rules/)
1. `context-engineering.md`: Giao thß╗⌐c lß╗ìc log thß╗½a, khai b├ío l╞░ß╗¥i (lazy loading) v├á tß╗æi ╞░u KV-cache.
2. `dual-remote-push-protocol.md`: Giao thß╗⌐c bß║úo mß║¡t 2 remote, c├ích ly ho├án to├án AI asset khß╗Åi SCM c├┤ng ty.
3. `graphify.md`: ─Éiß╗üu h╞░ß╗¢ng ─æß╗ô thß╗ï tri thß╗⌐c m├ú nguß╗ôn thay v├¼ ─æß╗ìc to├án v─ân m├ú nguß╗ôn lß╗¢n.
4. `lessons-learned.md`: Danh s├ích b├ái hß╗ìc kinh nghiß╗çm v├á anti-patterns ─æ├ú giß║úi quyß║┐t.
5. `mandatory-playwright-live.md`: Quy chuß║⌐n chß║íy headless 1920x1080 v├á 5 AI paradigms.
6. `skill-precedence.md`: Thß╗⌐ tß╗▒ ╞░u ti├¬n skill cß╗Ñc bß╗Ö, chß╗æng xung ─æß╗Öt vß╗¢i plugin ngo├ái.
7. `systematic-debugging.md`: Kß╗╖ luß║¡t ─æiß╗üu tra lß╗ùi c├│ c─ân cß╗⌐, cß║Ñm ─æo├ín m├▓ v├á verify-first.

---

## ≡ƒ¢á∩╕Å 4. Bß╗Ö C├┤ng Cß╗Ñ Tß╗▒ ─Éß╗Öng H├│a (tools/ & scripts/)

- `tools/verify_all.py`: Cß╗òng thß║⌐m ─æß╗ïnh 7 Gates (UTF-8, No XPaths, UniqueCode, Meta Infer, Clean POM).
- `tools/infer_linter.py`: Ph├ón t├¡ch t─⌐nh AST ph├ít hiß╗çn fake-pass (0 assertion) v├á khß╗æi try-catch rß╗ùng.
- `tools/test_impact.py`: Ph├ón t├¡ch git diff v├á khoanh v├╣ng ch├¡nh x├íc test cases bß╗ï ß║únh h╞░ß╗ƒng.
- `tools/cache_resolver.py`: Quß║ún l├╜ bß╗Ö nhß╗¢ ─æß╗çm lß╗ùi SQLite trung t├óm (`~/.agent_memory/global_cache.db`).
- `tools/distill_log.py`: Lß╗ìc bß╗Å 95% log thß╗½a tß╗½ CLI/Gradle/KRE, giß╗» lß║íi th├┤ng tin cß╗æt l├╡i.
- `tools/agent_canary.py`: Hß╗ç thß╗æng ti├¬m lß╗ùi tß╗▒ ─æß╗Öng (Canary & Mutation Testing) ─æ├ính gi├í sß╗⌐c phß╗Ñc hß╗ôi cß╗ºa Agent.
- `tools/repo_map.py`: Tr├¡ch xuß║Ñt bß║ún ─æß╗ô cß║Ñu tr├║c h├ám v├á Page Class si├¬u n├⌐n (~500 tokens).
- `tools/visual_diff_canvas.py`: So s├ính pixel/SSIM cho m├án h├¼nh GIS/Canvas kh├┤ng c├│ DOM.
- `tools/wcag_audit.py`: Qu├⌐t kiß╗âm to├ín tß╗▒ ─æß╗Öng c├íc ti├¬u ch├¡ WCAG 2.2.
- `tools/trace_data_flow.py`: Kiß╗âm tra luß╗ông dß╗» liß╗çu kiß╗âm thß╗¡, ph├ít hiß╗çn r├íc dß╗» liß╗çu DB (Orphan Data).
