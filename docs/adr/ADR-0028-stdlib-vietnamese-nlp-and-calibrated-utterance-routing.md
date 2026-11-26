<!--
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License
-->

# ADR-0028: Pure-Stdlib Vietnamese NLP Core & Calibrated Utterance Routing (v2.2)

- **Status:** Accepted (DoD Certified)
- **Date:** 2026-11-26
- **Source Plan:** `implementation_plan.md`
- **Deciders:** Synapse Hub Autonomous Agent Core & Engineering Team

---

## Context & Problem Statement

Prior to v2.2, Synapse Hub normalized bilingual Vietnamese and English prompts via a static `PHRASE_LEXICON` and a 64-word `_UNACCENTED_VI_MARKERS` table in `tools/core/bilingual_intent_normalizer.py`, while `tools/core/skill_router.py` ranked file-less Turn-1 skills with uncalibrated integer keyword heuristics (`+4/+3/+2/+1`). That design exhibited four structural limitations:

1. **Unseen Unaccented Vietnamese & Telex Blindness:** Freeform unaccented Vietnamese text outside the 64 static markers, old-vs-new Vietnamese tone-placement variants, colloquial shorthand, and Telex typos bypassed bilingual normalization.
2. **Uncalibrated Integer Skill Ranking:** Colloquial Vietnamese prompts describing a clear QA task without verbatim English keywords failed to reach the `+4` lexical cutoff, while raw integer totals could not express calibrated routing probabilities in `[0, 1]`.
3. **Deep Control-Flow Nesting:** Ad-hoc homonym `if/elif` guards inside `normalize_bilingual_intent` and `evaluate_skill_first_trigger` produced 5-level AST nesting flagged by Purple Audit.
4. **No Stratified Empirical Scorecard:** Accuracy across accented, unaccented, Telex, teencode, mixed VI-EN, hard-negative abstention, and homonym-trap prompts lacked an automated benchmark gate.

---

## Empirical Audit of 8 Reference Repositories (Adopted vs Rejected)

Source-code inspection of eight open-source repositories guided our pure-stdlib distillation:

1. **`aurelio-labs/semantic-router`** (`route.py`, `encoders/bm25.py`, `routers/indexed.py`, `calibration.py`):
   - *Adopted:* Immutable `SkillRouteSpec(skill_id, domain, utterances_en, utterances_vi, confidence_threshold)` routes; ATIRE smoothed IDF `log((N + 1) / (df + 0.5))` with L1 query-weight normalization and `1 / (k1 + 1)` TF scaling bounding BM25 strictly to `[0, 1]`; top-k (`max`/`mean`) per-route aggregation; Platt Newton-Raphson and Pool-Adjacent-Violators (`isotonic`) probability calibration plus Expected Calibration Error (`ECE`).
   - *Rejected:* `pydantic`, `numpy`, external vector databases, and background `asyncio` loops.
2. **`undertheseanlp/underthesea`** (`restore_diacritics/restorer.py`, `text_normalize/token_normalize.py`, `utils/vietnamese_ipa_rules.py`):
   - *Adopted:* Viterbi syllable bigram diacritics restorer (`lambda_bigram = 0.8` interpolated bigram + Laplace unigram, `<num>` numeric context token, URL/path/code chain-breakers) over an embedded QA corpus; `len(token) <= 6` shorthand normalization; exact Vietnamese phonotactic syllable validation (`onset + glide + nucleus + coda` with stop-coda tone constraints).
   - *Rejected:* Compiled Rust `FastText` binaries and `joblib`/CRF `.bin` pickle models.
3. **`vncorenlp/VnCoreNLP`** (`WordSegmenter.java`, `Utils.java`):
   - *Adopted:* Old-to-new tone-placement canonicalizer (`oa/oe/uy`), 4-to-5-syllable Longest-Match compound segmentation, and declarative Ripple-Down Rules (`RDRExceptionRuleDTO`) contextual exception resolution.
   - *Rejected:* JVM `.jar` runtime and general-domain dictionary memory footprint.
4. **`trungtv/pyvi`** (`ViTokenizer.py`, `ViDiac.py`):
   - *Adopted:* Guarded Telex vowel/tone decomposition (`dd, aa, aw, ee, oo, ow, uw` + `s, f, r, x, j`) protected by an English tech safelist (`owasp`, `aws`, `root`, `seed`, `loop`, `hook`, `pool`, `tool`, `food`, `good`, `bool`, and English plural guards).
   - *Rejected:* `sklearn_crfsuite` binary pickle artifacts.
5. **`MinishLab/model2vec`** (`distill/inference.py`):
   - *Adopted:* Smooth Inverse Frequency (`SIF`) Zipf token weighting `w = sif_coeff / (sif_coeff + p_rank)` (`sif_coeff = 1e-4`) smoothly downweighting high-frequency generic verbs.
   - *Rejected:* `torch`, `transformers`, and Rust extensions.
6. **`huggingface/setfit` + Neural Diacritics Repositories:**
   - *Adopted:* Contrastive positive and hard-negative utterance pair stratification for `bilingual_vi_intent_bench.py`.
   - *Rejected:* TensorFlow and PyTorch Seq2Seq weights that violate `< 5ms` offline CLI latency.

---

## Architectural Decision (Selected Branch B: Pure-Stdlib Distillation)

1. **Pure-Stdlib Vietnamese NLP Core (`tools/core/vietnamese_nlp_utils.py`):**
   - Exposes `SyllabicAnalysisDTO`, `RDRExceptionRuleDTO`, `is_valid_vietnamese_syllable`, `canonicalize_vietnamese_orthography`, `restore_qa_vietnamese_diacritics`, and `resolve_longest_match_rdr` with zero third-party dependencies and AST control-flow nesting `<= 3`.
2. **Normalizer RDR Refactor (`tools/core/bilingual_intent_normalizer.py`):**
   - Replaces nested `if/elif` homonym branches with declarative `RDR_HOMONYM_RULES` and Longest-Match consumption, detects unseen unaccented Vietnamese text via phonotactic syllable ratio, preserves 100% of `NormalizedIntentDTO` fields, and caches immutable results via `@lru_cache(maxsize=256)`.
3. **Bounded `[0, 1]` ATIRE BM25, Calibrator & 60-Skill Registry (`tools/core/bm25_retriever.py`, `tools/core/skill_utterances_registry.py`):**
   - Extends `BM25Index` with `score_bounded()` alongside untouched legacy `search()` and `hybrid_search()`, adds `ScoreCalibrator` (`isotonic`, `platt`) and `compute_expected_calibration_error()`, and registers all 57 indexed skills plus 3 local `.agent/skills` (`solo`, `super-plan`, `review`) with bilingual utterances.
4. **Calibrated Hybrid Skill Router (`tools/core/skill_router.py`):**
   - Lazily builds a thread-safe (`threading.Lock` double-checked) `CalibratedUtteranceRouterIndex` singleton fusing lexical triggers with top-k bounded BM25 + char-ngram utterance scores, exposing `calibrated_confidence` and `matched_utterances` while keeping all 15 legacy return keys backward-compatible and flattening AST nesting to `<= 3`.
5. **Stratified Benchmark Gate (`benchmarks/qa_eval/bilingual_vi_intent_bench.py`):**
   - Evaluates 132 stratified Vietnamese and mixed VI-EN prompts enforcing `--gate` thresholds: Top-1 Accuracy `>= 90.0%`, Homonym FPR `<= 2.0%`, and p95 latency `< 5.0ms`.

---

## Vulnerability Mitigations

- **Concurrency & Thread Safety:** Double-checked `threading.Lock()` guards singleton index construction; all route specs, lexicons, and RDR rules use immutable `tuple` / `MappingProxyType` structures; `@lru_cache(maxsize=256)` caches frozen `NormalizedIntentDTO` objects.
- **Boundary & Resource Exhaustion:** Prompts clip at `MAX_INPUT_CHARS = 8192`; Viterbi chains cap at `64` tokens (`K <= 6` candidates per syllable -> sub-millisecond worst case); the 60-route utterance index holds ~480 short utterances (`< 512KB` RAM).
- **Backward Compatibility:** Every existing field on `NormalizedIntentDTO`, method on `BM25Index`, and key returned by `evaluate_skill_first_trigger()` remains intact across all 43 transitive dependents.

---

## Consequences & Quality Gates

- **Positive:** Zero external dependencies, sub-5ms p95 routing latency, flattened AST control flow (`<= 3`), high-precision bilingual utterance routing across all 60 skills, and monotonic benchmark/mutation gates (`>= 80%` live mutation kill score across all core modules).
- **Constraints:** New skills added to `skills_index.json` or `.agent/skills/` should receive a matching `SkillRouteSpec` entry in `tools/core/skill_utterances_registry.py` (mechanically verified by `tests/test_vietnamese_nlp_and_hybrid_router.py`).
