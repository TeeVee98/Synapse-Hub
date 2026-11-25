# Implementation Plan: Extract & Integrate Lauren Tan (`@poteto`) Ecosystem Patterns into Synapse Hub

> **Risk Tier:** Tier 1 (`STANDARD`, `RiskScore = 0.52`) — Cross-boundary skill & tooling enhancement across 5 domains (`01-web-automation`, `04-performance-and-load`, `08-code-quality`, `10-agent-orchestration`, `11-ai-and-prompting`), extending existing skills rather than creating colliding duplicates.
> **Execution Mode:** Sequential Single-Agent `/solo` (`M1-DECISION-TRAIL` -> `M2-VERIFY-FEATURE-MAP` -> `M3-BENCHMARK-VETTING` -> `M4-BRAIN-REFLECT-LOOP` -> `M5-HOW-CRITIQUE-GATE` -> `M6-PREEXEC-CONTEXT-CONTRACT`).
> **Reference Clones:** `reference_repos/poteto/{brainmaxxing,noodle,how,verification-skill-example,cursor-plugins/pstack}` (gitignored).
> **Changelog:** `2026-11-25` — Added `M6-PREEXEC-CONTEXT-CONTRACT` (Pre-Execution 3-Line Contract & Context-Dump Kickoff Template from `in-your-own-words` / `arena` / `poteto-mode`).

---

## Evaluation Matrix: Lauren Tan (`@poteto`) Repos vs. Synapse Hub

| Source Repo / Skill | Core Mechanism | Synapse Hub Existing Coverage | Gap & Extraction Decision |
|---|---|---|---|
| `pstack/show-me-your-work` | Append-only `decisions.tsv` (`ts, phase, decision, why, evidence, result`), formula-injection escaping (`=+-@`), transcript-vs-log self-audit, cross-model Attention section | `persistent-planning-files` (markdown `task.md`/`progress.md`), `event-stream-qa-orchestrator` | **ADOPT (M1):** Add lightweight cross-platform `tools/core/decision_log.py` + integrate into `persistent-planning-files` for `/goal` & `/solo` runs |
| `pstack/create-verification-skill` & `verification-skill-example` (`verify-atlas`) | Repo interview -> User-POV Feature Map (`Sub-features`, `How to get to it`, `Driving it`, `Gotchas`), `doctor` preflight, checkout isolation, evidence-preserving `cleanup` | `playwright-webapp-testing`, `playwright-live-interaction` | **ADOPT (M2):** Add Feature Map template & `Doctor`/Evidence-preserving Cleanup protocol to `playwright-webapp-testing` |
| `pstack/benchmark-checklist` & `principle-explain-the-number` | 7-question empirical perf vetting (limiter, tuning, physical limits, error count, 5x interleaved A/B, E2E relevance, work-actually-ran) | `web-vitals-and-performance-profiler`, `backend-load-and-stress-patterns` | **ADOPT (M3):** Embed 7-Question Benchmark Vetting Gate into both performance skills |
| `brainmaxxing` (`/reflect`, `/meditate`, `/ruminate`, `brain/`) | Human-browsable Markdown/Obsidian vault (`brain/index.md` + `[[wikilinks]]`), structural-enforcement-first routing, principle distillation | `qa-memory-os` (3-tier SQLite for locators/sessions) | **ADOPT (M4):** Add Markdown Brain Vault & `/reflect`->`/meditate` loop to `qa-memory-os` + `tools/core/brain_indexer.py` |
| `poteto/how` (`Explain` + `Critique`) | Senior-engineer 5-section subsystem explainer + 3-critic panel with Lead Verdict (`Act on / Consider / Noted / Dismissed`) | `senior-code-review`, `graphify-impact-analyzer` | **ADOPT (M5):** Add 4-tier Lead Verdict & 5-section Onboarding Explainer mode to `senior-code-review` |
| `pstack/in-your-own-words` & `arena` Context-Dump | Restate Goal / Non-Goals (`Won't Do`) / Done Criteria before coding; full context-dump kickoff (Goal, Data/Schema, 1 Good Example, Constraints) | `surgical-coding-principles`, `meta-prompt-crafter` | **ADOPT (M6):** Add Pre-Execution 3-Line Contract to `surgical-coding-principles` & 4-part Context-Dump Template to `meta-prompt-crafter` |
| `pstack/poteto-mode` & `noodle` | `worker.md` kickoff pointer, self-read citation discipline, `block-sleep.sh` | Already enforced by `AGENTS.md` Invariant 3, 7, 14, `infer_linter.py` | **SKIP:** Already natively enforced with stronger deterministic gates in Synapse Hub |

---

## 1. Affected Files & Blast Radius

- `skills/10-agent-orchestration/persistent-planning-files/SKILL.md` (L1-L50) — Add `decisions.tsv` append-only audit trail & transcript self-audit section.
- `tools/core/decision_log.py` (New) — Cross-platform Python stdlib TSV decision logger with formula-injection sanitization and transcript audit helper.
- `tests/test_decision_log.py` (New) — Unit tests for `decision_log.py` (Positive, Negative, Boundary, CLI flags).
- `skills/01-web-automation/playwright-webapp-testing/SKILL.md` (L1-L60) — Add `Doctor` preflight, User-POV Feature Map reference, and evidence-preserving `Cleanup`.
- `templates/verification/FEATURE_MAP_TEMPLATE.md` (New) — 4-H2 User-POV feature map template (`Sub-features`, `How to get to it (user POV)`, `Driving it`, `Gotchas`).
- `skills/04-performance-and-load/web-vitals-and-performance-profiler/SKILL.md` (L1-L50) — Add 7-Question Benchmark Vetting Gate.
- `skills/04-performance-and-load/backend-load-and-stress-patterns/SKILL.md` (L1-L50) — Add 7-Question Benchmark Vetting Gate.
- `skills/10-agent-orchestration/qa-memory-os/SKILL.md` (L1-L70) — Add Markdown Brain Vault (`brain/index.md`) + `/reflect` structural-first routing & `/meditate` pruning loop.
- `tools/core/brain_indexer.py` (New) — Lightweight Python stdlib indexer generating `brain/index.md` `[[wikilinks]]` without shell/bash dependency.
- `tests/test_brain_indexer.py` (New) — Unit tests for `brain_indexer.py`.
- `skills/08-code-quality/senior-code-review/SKILL.md` (L1-L50) — Add `Explain` 5-section onboarding mode & 4-tier Lead Verdict (`Act on / Consider / Noted / Dismissed`).
- `docs/adr/ADR-0020-poteto-ecosystem-extraction.md` (New) — Architectural Decision Record documenting extracted patterns and skipped redundancies.
- `skills/08-code-quality/surgical-coding-principles/SKILL.md` (L43-L70) — Add Pre-Execution 3-Line Contract (`Goal` / `Won't Do` / `Done When`).
- `skills/11-ai-and-prompting/meta-prompt-crafter/SKILL.md` (L1-L50) — Add 4-Part Context-Dump Kickoff Template (Goal, Data/Schema, 1 Good Example, Constraints).

---

## 2. Data Flow & Interface Signatures

```python
# tools/core/decision_log.py::DecisionRowDTO (New)
@dataclass(frozen=True)
class DecisionRowDTO:
    ts: str
    phase: str
    decision: str
    why: str
    evidence: str
    result: str

def sanitize_tsv_cell(value: str) -> str: ...
def append_decision_row(log_path: str, row: DecisionRowDTO) -> bool: ...
def audit_decision_log(log_path: str) -> Dict[str, Any]: ...
```

```python
# tools/core/brain_indexer.py::BrainIndexReportDTO (New)
@dataclass(frozen=True)
class BrainIndexReportDTO:
    brain_dir: str
    indexed_files: int
    index_path: str
    broken_links: List[str]

def build_brain_index(brain_dir: str, dry_run: bool = False) -> BrainIndexReportDTO: ...
```

### Tri-Vulnerability Red-Teaming
1. **Race Condition & Concurrency:** Multiple subagents writing to `decisions.tsv` or `brain/index.md` concurrently could interleave lines; `append_decision_row` uses atomic single-line `os.write` / file lock (`fcntl`/`msvcrt` or single-process sequential `/solo` ownership), and `build_brain_index` writes via temp-file + `os.replace`.
2. **Boundary & Resource Limits:** TSV cells containing tabs, newlines, or spreadsheet formula prefixes (`=`, `+`, `-`, `@`) are sanitized in `sanitize_tsv_cell` (strip `\t\r\n`, prefix leading `=+-@` with `'`). Empty `brain/` directories return `indexed_files=0` without crashing.
3. **Backward Compatibility & Blast Radius:** All additions extend existing `SKILL.md` files and add standalone stdlib tools (`decision_log.py`, `brain_indexer.py`) with zero breaking changes to `skills_index.json` IDs, `tools/tools_schema.json` existing commands, or `qa-memory-os` SQLite schemas.

---

## 3. Atomic Milestones (Execution DAG)

### Milestone 1: Decision Trail & Evidence Logger
- **Node ID:** `M1-DECISION-TRAIL`
- **depends_on:** `[]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High]`
- **Files (3):**
  1. `tools/core/decision_log.py` (New)
  2. `tests/test_decision_log.py` (New)
  3. `skills/10-agent-orchestration/persistent-planning-files/SKILL.md` (L1-L50)
- **consumes:** `[]`
- **produces:** `["DecisionRowDTO", "sanitize_tsv_cell", "append_decision_row", "audit_decision_log"]`
- **Circuit Breaker:** `Max Fix Attempts: 2` | `Scope Guard: <= 3 files`
- **Rollback Hook:** `git restore skills/10-agent-orchestration/persistent-planning-files/SKILL.md`

### Milestone 2: User-POV Feature Map & Verification Preflight
- **Node ID:** `M2-VERIFY-FEATURE-MAP`
- **depends_on:** `["M1-DECISION-TRAIL"]`
- **Compute Tier:** `[Model: Flash | Thinking: Off]`
- **Files (2):**
  1. `templates/verification/FEATURE_MAP_TEMPLATE.md` (New)
  2. `skills/01-web-automation/playwright-webapp-testing/SKILL.md` (L1-L60)
- **consumes:** `["DecisionRowDTO"]`
- **produces:** `["FEATURE_MAP_TEMPLATE"]`
- **Circuit Breaker:** `Max Fix Attempts: 2` | `Scope Guard: <= 2 files`
- **Rollback Hook:** `git restore skills/01-web-automation/playwright-webapp-testing/SKILL.md`

### Milestone 3: 7-Question Empirical Benchmark Vetting Gate
- **Node ID:** `M3-BENCHMARK-VETTING`
- **depends_on:** `["M2-VERIFY-FEATURE-MAP"]`
- **Compute Tier:** `[Model: Flash | Thinking: Off]`
- **Files (2):**
  1. `skills/04-performance-and-load/web-vitals-and-performance-profiler/SKILL.md` (L1-L50)
  2. `skills/04-performance-and-load/backend-load-and-stress-patterns/SKILL.md` (L1-L50)
- **consumes:** `["FEATURE_MAP_TEMPLATE"]`
- **produces:** `["BENCHMARK_VETTING_GATE"]`
- **Circuit Breaker:** `Max Fix Attempts: 2` | `Scope Guard: <= 2 files`
- **Rollback Hook:** `git restore skills/04-performance-and-load/web-vitals-and-performance-profiler/SKILL.md skills/04-performance-and-load/backend-load-and-stress-patterns/SKILL.md`

### Milestone 4: Markdown Brain Vault & Reflect/Meditate Loop
- **Node ID:** `M4-BRAIN-REFLECT-LOOP`
- **depends_on:** `["M3-BENCHMARK-VETTING"]`
- **Compute Tier:** `[Model: Pro / Reasoning | Thinking: High]`
- **Files (3):**
  1. `tools/core/brain_indexer.py` (New)
  2. `tests/test_brain_indexer.py` (New)
  3. `skills/10-agent-orchestration/qa-memory-os/SKILL.md` (L1-L70)
- **consumes:** `["BENCHMARK_VETTING_GATE"]`
- **produces:** `["BrainIndexReportDTO", "build_brain_index"]`
- **Circuit Breaker:** `Max Fix Attempts: 2` | `Scope Guard: <= 3 files`
- **Rollback Hook:** `git restore skills/10-agent-orchestration/qa-memory-os/SKILL.md`

### Milestone 5: Senior Explainer/Critique Verdict & ADR Finalization
- **Node ID:** `M5-HOW-CRITIQUE-GATE`
- **depends_on:** `["M4-BRAIN-REFLECT-LOOP"]`
- **Compute Tier:** `[Model: Flash | Thinking: Off]`
- **Files (2):**
  1. `skills/08-code-quality/senior-code-review/SKILL.md` (L1-L50)
  2. `docs/adr/ADR-0020-poteto-ecosystem-extraction.md` (New)
- **consumes:** `["BrainIndexReportDTO", "build_brain_index"]`
- **produces:** `["ADR_0020_POTETO_EXTRACTION"]`
- **Circuit Breaker:** `Max Fix Attempts: 2` | `Scope Guard: <= 2 files`
- **Rollback Hook:** `git restore skills/08-code-quality/senior-code-review/SKILL.md`

### Milestone 6: Pre-Execution 3-Line Contract & Context-Dump Template
- **Node ID:** `M6-PREEXEC-CONTEXT-CONTRACT`
- **depends_on:** `["M5-HOW-CRITIQUE-GATE"]`
- **Compute Tier:** `[Model: Flash | Thinking: Off]`
- **Files (2):**
  1. `skills/08-code-quality/surgical-coding-principles/SKILL.md` (L43-L70)
  2. `skills/11-ai-and-prompting/meta-prompt-crafter/SKILL.md` (L1-L50)
- **consumes:** `["ADR_0020_POTETO_EXTRACTION"]`
- **produces:** `["PREEXEC_3LINE_CONTRACT", "CONTEXT_DUMP_TEMPLATE"]`
- **Circuit Breaker:** `Max Fix Attempts: 2` | `Scope Guard: <= 2 files`
- **Rollback Hook:** `git restore skills/08-code-quality/surgical-coding-principles/SKILL.md skills/11-ai-and-prompting/meta-prompt-crafter/SKILL.md`

---

## 4. Verification Matrix ("Define the Exam in the Plan")

| Milestone | Verification Command | Positive / Negative / Boundary / CLI Checks |
|---|---|---|
| `M1-DECISION-TRAIL` | `pytest tests/test_decision_log.py -v` | Positive: append valid row; Negative: reject missing log/invalid phase; Boundary: sanitize `\t\n` & `=+-@` formula prefix; CLI: `--json` output |
| `M2-VERIFY-FEATURE-MAP` | `python tools/lint/validate_skills_schema.py` | Validates 5-section Synapse skill policy & link integrity for `playwright-webapp-testing` |
| `M3-BENCHMARK-VETTING` | `python tools/lint/validate_skills_schema.py` | Validates 7-question vetting gate formatting & schema compliance in both perf skills |
| `M4-BRAIN-REFLECT-LOOP` | `pytest tests/test_brain_indexer.py -v` | Positive: index `.md` vault with `[[wikilinks]]`; Negative: non-existent dir error; Boundary: empty dir -> 0 files; CLI: `--dry-run --json` |
| `M5-HOW-CRITIQUE-GATE` | `python tools/lint/validate_skills_schema.py` | Validates `senior-code-review` schema & `ADR-0020` link integrity |
| `M6-PREEXEC-CONTEXT-CONTRACT` | `python tools/core/verify_all.py --mode hub --tier impact` | Full impact-tier DoD gates (UTF-8, Infer Linter, Skill Schema, AI Docs Lint, Collision Guard, Micro-Mutator >= 80%) |

---

## Recommended Execution Model & Thinking Level

- **Primary Executor Model & Thinking Level (Single-Session Default):** `Gemini 4 Hydrogen (Medium)` (sufficient for all 6 sequential `/solo` milestones; escalate to `Gemini 4 Hydrogen (High)` if `micro_mutator` requires deeper test hardening in M1/M4).
- **Milestone Escalation Overrides (Optional / `/teamwork` Only):** None required; all milestones are sequential (`M1 -> M2 -> M3 -> M4 -> M5 -> M6`) with `<= 3` files per milestone.
- **Rationale:** The plan extends existing Markdown skills and adds two small, isolated Python stdlib utilities with unit tests, keeping blast radius low and deterministic gate coverage high.
