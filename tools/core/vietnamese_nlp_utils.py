#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)
# Author: Thế Vị (@TeeVee98) | MIT License

"""
tools/core/vietnamese_nlp_utils.py — Pure-Stdlib Vietnamese NLP Core (v1.0)
---------------------------------------------------------------------------
Zero-dependency algorithmic distillation of Vietnamese NLP primitives:
  1. VnCoreNLP tone-placement canonicalizer (oa/oe/uy) + Unicode NFC.
  2. Underthesea phonotactic syllable validator (onset + glide + nucleus + coda).
  3. Pyvi/Underthesea guarded Telex & shorthand normalizer with English tech safelist.
  4. Underthesea Viterbi syllable bigram diacritics restorer (LAMBDA=0.8, <num> token,
     code/URL/path chain-breakers, 64-token chain cap) over an embedded QA/Dev corpus.
  5. VnCoreNLP Longest-Match compound segmenter + Ripple-Down Rules (RDR) context resolver.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
import re
from typing import Dict, List, Mapping, Optional, Sequence, Tuple
import unicodedata

MAX_INPUT_CHARS: int = 8192
MAX_VITERBI_CHAIN: int = 64
MAX_CANDIDATES_PER_SYLLABLE: int = 6


@dataclass(frozen=True)
class SyllabicAnalysisDTO:
    """Phonotactic and orthographic analysis of a normalized prompt."""

    canonical_nfc_text: str
    restored_diacritics_text: str
    valid_vi_syllable_count: int
    total_alpha_tokens: int
    vi_syllable_ratio: float
    had_telex_or_shorthand: bool


@dataclass(frozen=True)
class RDRExceptionRuleDTO:
    """Ripple-Down Rule contextual override for polysemous n-grams."""

    ngram: str
    default_tokens: Tuple[str, ...]
    positive_context_pattern: Optional[str]
    negative_context_pattern: Optional[str]
    override_tokens: Tuple[str, ...]
    conflict_tag: Optional[str] = None


# ------------------------------------------------------------------------------
# 1. VnCoreNLP Tone-Placement Canonicalizer (Old Style -> New Canonical Style)
# ------------------------------------------------------------------------------

_TONE_CANONICAL_MAP: Tuple[Tuple[str, str], ...] = (
    ("òa", "oà"), ("óa", "oá"), ("ỏa", "oả"), ("õa", "oã"), ("ọa", "oạ"),
    ("òe", "oè"), ("óe", "oé"), ("ỏe", "oẻ"), ("õe", "oẽ"), ("ọe", "oẹ"),
    ("ùy", "uỳ"), ("úy", "uý"), ("ủy", "uỷ"), ("ũy", "uỹ"), ("ụy", "uỵ"),
    ("Òa", "Oà"), ("Óa", "Oá"), ("Ỏa", "Oả"), ("Õa", "Oã"), ("Ọa", "Oạ"),
    ("Òe", "Oè"), ("Óe", "Oé"), ("Ỏe", "Oẻ"), ("Õe", "Oẽ"), ("Ọe", "Oẹ"),
    ("Ùy", "Uỳ"), ("Úy", "Uý"), ("Ủy", "Uỷ"), ("Ũy", "Uỹ"), ("Ụy", "Uỵ"),
)

_VI_DIACRITIC_RE = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)

# Combining tone marks (NFD Mn category excluding circumflex/breve/horn)
_TONE_ACUTE = "\u0301"
_TONE_GRAVE = "\u0300"
_TONE_HOOK = "\u0309"
_TONE_TILDE = "\u0303"
_TONE_DOT = "\u0323"
_ALL_TONE_MARKS: frozenset[str] = frozenset({
    _TONE_ACUTE, _TONE_GRAVE, _TONE_HOOK, _TONE_TILDE, _TONE_DOT,
})
_STOP_CODA_ALLOWED_TONES: frozenset[str] = frozenset({_TONE_ACUTE, _TONE_DOT})


def _fold_ascii(text: str) -> str:
    """Folds Vietnamese characters to plain ASCII lowercase."""
    replaced = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", replaced)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn").lower()


def _strip_tone_only(token: str) -> Tuple[str, Optional[str]]:
    """Strips only Vietnamese tone mark while preserving ă/â/đ/ê/ô/ơ/ư; returns (base, tone)."""
    tone: Optional[str] = None
    out: List[str] = []
    for ch in unicodedata.normalize("NFD", token.lower()):
        if ch in _ALL_TONE_MARKS:
            if tone is None:
                tone = ch
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out)), tone


def _canonicalize_tone_placement(text: str) -> str:
    """Applies Unicode NFC and VnCoreNLP old-to-new tone placement normalization."""
    nfc = unicodedata.normalize("NFC", text)
    for old_seq, new_seq in _TONE_CANONICAL_MAP:
        if old_seq in nfc:
            nfc = nfc.replace(old_seq, new_seq)
    return nfc


# ------------------------------------------------------------------------------
# 2. Underthesea Phonotactic Vietnamese Syllable Validator
# ------------------------------------------------------------------------------

_VI_ONSETS: Tuple[str, ...] = (
    "ngh", "ng", "nh", "kh", "th", "tr", "ch", "ph", "gh", "gi", "qu",
    "b", "c", "d", "đ", "g", "h", "k", "l", "m", "n", "p", "r", "s", "t", "v", "x",
)

_FRONT_VOWEL_ONSETS: frozenset[str] = frozenset({"k", "gh", "ngh"})
_BACK_VOWEL_ONSETS: frozenset[str] = frozenset({"c", "g", "ng"})
_FRONT_VOWELS: frozenset[str] = frozenset({"e", "ê", "i", "y"})
_STOP_CODAS: Tuple[str, ...] = ("ch", "c", "p", "t")

# Exact Vietnamese rhymes (base vowels without tone + valid codas)
_BASE_VI_RHYMES: frozenset[str] = frozenset({
    # Single vowels + codas
    "a", "ac", "ach", "am", "an", "ang", "anh", "ap", "at",
    "ăc", "ăm", "ăn", "ăng", "ăp", "ăt",
    "âc", "âm", "ân", "âng", "âp", "ât",
    "e", "ec", "em", "en", "eng", "ep", "et",
    "ê", "êch", "êm", "ên", "ênh", "êp", "êt",
    "i", "ich", "im", "in", "inh", "ip", "it",
    "y",
    "o", "oc", "om", "on", "ong", "op", "ot",
    "ô", "ôc", "ôm", "ôn", "ông", "ôp", "ôt",
    "ơ", "ơm", "ơn", "ơp", "ơt",
    "u", "uc", "um", "un", "ung", "up", "ut",
    "ư", "ưc", "ưm", "ưn", "ưng", "ưp", "ưt",
    # Diphthongs & triphthongs + codas
    "ai", "ao", "au", "âu", "ay", "ây", "eo", "êu",
    "ia", "iêc", "iêm", "iên", "iêng", "iêp", "iêt", "iêu", "iu",
    "oa", "oac", "oach", "oai", "oam", "oan", "oang", "oanh", "oao", "oap", "oat", "oay",
    "oăc", "oăm", "oăn", "oăng", "oăp", "oăt",
    "oe", "oem", "oen", "oeo", "oet",
    "oi", "ôi", "ơi", "ooc", "oong",
    "ua", "uac", "uan", "uang", "uat", "uay",
    "uân", "uâng", "uât", "uây", "uăn", "uăt",
    "uê", "uêch", "uên", "uênh", "uêt", "uêu",
    "ui", "uôc", "uôi", "uôm", "uôn", "uông", "uôp", "uôt",
    "uơ", "uơn", "uơt",
    "uy", "uya", "uych", "uyêm", "uyên", "uyêt", "uyn", "uynh", "uyp", "uyt", "uyu",
    "ưa", "ưi", "ươc", "ươi", "ươm", "ươn", "ương", "ươp", "ươt", "ươu", "ưu",
    "yêm", "yên", "yêng", "yêt", "yêu",
})

_ASCII_VI_RHYMES: frozenset[str] = frozenset(_fold_ascii(r) for r in _BASE_VI_RHYMES)


def _split_vi_onset(base_token: str) -> Tuple[str, str]:
    """Splits a lowercased tone-stripped syllable into (onset, rhyme)."""
    for onset in _VI_ONSETS:
        if base_token.startswith(onset):
            rem = base_token[len(onset):]
            if onset == "gi" and not rem:
                return "gi", "i"
            if rem:
                return onset, rem
    return "", base_token


def is_valid_vietnamese_syllable(token: str) -> bool:
    """Validates whether a token conforms to Vietnamese syllable phonotactics."""
    if not token or not isinstance(token, str):
        return False
    low = _canonicalize_tone_placement(token.strip()).lower()
    if not low or len(low) > 7 or not low.isalpha():
        return False

    folded = _fold_ascii(low)
    if any(ch in "fjwz" for ch in folded):
        return False

    has_diacritics = bool(_VI_DIACRITIC_RE.search(low))
    base, tone = _strip_tone_only(low)
    onset, rhyme = _split_vi_onset(base)
    if not rhyme:
        return False

    if onset in _FRONT_VOWEL_ONSETS and rhyme[0] not in _FRONT_VOWELS:
        return False
    if onset in _BACK_VOWEL_ONSETS and rhyme[0] in _FRONT_VOWELS:
        return False

    rhyme_table = _BASE_VI_RHYMES if has_diacritics else _ASCII_VI_RHYMES
    if rhyme not in rhyme_table:
        return False

    if has_diacritics and tone is not None and rhyme.endswith(_STOP_CODAS):
        return tone in _STOP_CODA_ALLOWED_TONES
    return True


# ------------------------------------------------------------------------------
# 3. Guarded Telex & Shorthand Normalization (Pyvi + Underthesea)
# ------------------------------------------------------------------------------

_EN_TELEX_SAFELIST: frozenset[str] = frozenset({
    # Core tech / QA terms required untouched
    "owasp", "aws", "root", "seed", "loop", "hook", "pool", "tool", "food", "good", "bool",
    "boot", "book", "cool", "door", "floor", "foot", "look", "mood", "moon", "noon", "poor",
    "proof", "room", "soon", "wood", "zoom", "feed", "feel", "free", "green", "keep", "meet",
    "need", "peer", "peek", "seen", "seek", "seem", "sleep", "speed", "steel", "sweet", "tree",
    "week", "add", "odd", "bdd", "tdd", "ddd", "ddos", "uuid", "raw", "law", "saw", "draw",
    "show", "flow", "slow", "grow", "know", "throw", "row", "now", "how", "down", "town",
    "allow", "follow", "window", "shadow", "arrow", "power", "lower", "owner", "tower",
    # Common short English tokens / plurals / verbs
    "has", "his", "her", "car", "bar", "far", "for", "per", "var", "tar", "jar", "war", "par",
    "our", "your", "out", "put", "cut", "but", "not", "hot", "lot", "got", "run", "runs",
    "fix", "max", "tax", "box", "six", "mix", "fox", "hex", "rex", "docs", "logs", "bugs",
    "tests", "users", "files", "lines", "rules", "gates", "rates", "locks", "pages", "nodes",
    "modes", "roles", "types", "items", "names", "paths", "steps", "calls", "fails", "waits",
    "seeds", "pools", "tools", "hooks", "loops", "roots", "codes", "cases", "notes", "bytes",
    "check", "checks", "click", "clicks", "class", "pass", "cross", "press", "stress", "crash",
    "flash", "slash", "trash", "fresh", "vs", "k6", "ci", "cd", "qa", "db", "ui", "ux", "id",
    "ok", "io", "os", "ip", "ai", "ml", "pr", "js", "ts", "py", "md", "go", "do", "to", "in",
    "on", "or", "is", "at", "by", "as", "if", "of", "no", "so", "up", "my", "me", "be", "he",
    "we", "it", "an", "am", "are", "was", "were", "can", "may", "all", "any", "new", "old",
    "get", "set", "let", "use", "try", "end", "and", "the", "this", "that", "from", "with",
    "into", "over", "under", "after", "before", "docker", "redis", "jwt", "dast", "sast",
    "wcag", "aria", "a11y", "lcp", "cls", "inp", "cwv", "sla", "slo", "rca", "pom", "dom",
    "aom", "ast", "dag", "fsm", "adr", "cli", "sdk", "api", "url", "uri", "sql", "csv", "pdf",
    "xml", "utf", "bom", "lru", "idf", "sif", "ece", "pav", "rdr", "nlp", "llm", "dto", "fpr",
})

# Shorthand mappings (len(token) <= 6)
_UNAMBIGUOUS_VI_SHORTHAND: Mapping[str, str] = {
    "ko": "không",
    "k0": "không",
    "ktra": "kiểm tra",
    "trc": "trước",
    "ntn": "như thế nào",
    "mik": "mình",
    "cx": "cũng",
    "nhg": "nhưng",
    "tks": "cảm ơn",
}

_CONTEXT_VI_SHORTHAND: Mapping[str, str] = {
    "dc": "được",
    "dk": "được",
    "ng": "người",
    "dl": "dữ liệu",
    "kh": "khách hàng",
    "gd": "giao dịch",
    "tt": "thanh toán",
}

_TELEX_TONE_MAP: Mapping[str, str] = {
    "s": _TONE_ACUTE,
    "f": _TONE_GRAVE,
    "r": _TONE_HOOK,
    "x": _TONE_TILDE,
    "j": _TONE_DOT,
}

_TELEX_VOWEL_MODS: Tuple[Tuple[str, str], ...] = (
    ("uow", "ươ"),
    ("aa", "â"),
    ("aw", "ă"),
    ("ee", "ê"),
    ("oo", "ô"),
    ("ow", "ơ"),
    ("uw", "ư"),
)

_VI_DIGRAPH_ONSETS: Tuple[str, ...] = ("ngh", "ng", "nh", "kh", "th", "tr", "ch", "ph", "gh", "gi", "qu")
# Unmistakable Vietnamese Telex patterns that never occur in normal English words/plurals
_STRONG_TELEX_RE = re.compile(r"(?:^dd|aa|uw|uow|[aeo][aeo][a-z]*[frxj]|[a-z]{2,}j$)")
_VOWEL_PRIORITY = "êôơăâeoaùyiu"
_VOWEL_CHARS = set("aăâeêioôơuưy")


def _apply_tone_to_syllable(base: str, tone: str) -> str:
    """Places a Vietnamese combining tone mark onto the main nucleus vowel."""
    indices = [i for i, ch in enumerate(base) if ch in _VOWEL_CHARS]
    if not indices:
        return base

    # Prefer modified vowels (â, ă, ê, ô, ơ, ư), else follow standard Vietnamese nucleus placement
    target_idx = indices[0]
    special = [i for i in indices if base[i] in "âăêôơư"]
    if special:
        target_idx = special[-1]
    elif len(indices) == 2:
        pair = base[indices[0]] + base[indices[1]]
        has_coda = indices[-1] < len(base) - 1
        target_idx = indices[1] if (has_coda or pair in ("oa", "oe", "uy", "ua", "ia")) else indices[0]
    elif len(indices) >= 3:
        target_idx = indices[1]

    marked = base[: target_idx + 1] + tone + base[target_idx + 1 :]
    return _canonicalize_tone_placement(marked)


def _extract_telex_tone(work: str) -> Tuple[str, Optional[str]]:
    """Extracts a trailing or inline post-vowel Telex tone key (s, f, r, x, j)."""
    if len(work) >= 3 and work[-1] in _TELEX_TONE_MAP:
        return work[:-1], _TELEX_TONE_MAP[work[-1]]
    for idx in range(1, len(work) - 1):
        if work[idx] in _TELEX_TONE_MAP and work[idx - 1] in _VOWEL_CHARS:
            return work[:idx] + work[idx + 1 :], _TELEX_TONE_MAP[work[idx]]
    return work, None


def _decode_telex_token(token: str, allow_weak_tone: bool) -> Optional[str]:
    """Attempts to decode a single lowercase ASCII Telex token with strict phonotactic verification."""
    if len(token) < 2 or len(token) > 9 or not token.isascii() or not token.islower() or not token.isalpha():
        return None
    if token in _EN_TELEX_SAFELIST:
        return None

    has_strong_marker = bool(_STRONG_TELEX_RE.search(token))
    has_vi_onset = token.startswith(_VI_DIGRAPH_ONSETS)
    if not has_strong_marker and not has_vi_onset and not allow_weak_tone:
        return None

    work = "đ" + token[2:] if token.startswith("dd") else token
    for src, dst in _TELEX_VOWEL_MODS:
        if src in work:
            work = work.replace(src, dst)

    work, tone_mark = _extract_telex_tone(work)
    if "wa" in work and work.startswith(("s", "c", "l", "n", "m", "d", "t", "ch", "th", "ng")):
        work = work.replace("uwa", "ưa").replace("wa", "ă")

    if tone_mark is not None:
        work = _apply_tone_to_syllable(work, tone_mark)

    if work == token or not _VI_DIACRITIC_RE.search(work):
        return None
    return work if is_valid_vietnamese_syllable(work) else None


# ------------------------------------------------------------------------------
# 4. Underthesea Viterbi Syllable Bigram Diacritics Restorer (Embedded QA Corpus)
# ------------------------------------------------------------------------------

_QA_VI_CORPUS: Tuple[str, ...] = (
    "kiểm tra dữ liệu đầu vào trong tệp và xuất báo cáo",
    "kiểm tra dữ liệu đầu vào biểu mẫu đăng ký người dùng",
    "kiểm tra cấu trúc tập tin tải về và xuất báo cáo định dạng",
    "tạo dữ liệu giả cho cơ sở dữ liệu kiểm thử tự động",
    "tạo dữ liệu đầu vào và kiểm tra kết quả đầu ra",
    "sửa hàm kiểm tra dữ liệu đầu vào và xử lý lỗi",
    "sửa lỗi bấm đúp nút thanh toán gây xung đột luồng đồng thời",
    "sửa giùm chỗ thanh toán bị treo cứng và khóa cơ sở dữ liệu",
    "hai người bấm cùng lúc bị trừ tiền <num> lần khi giao dịch",
    "giao dịch thanh toán bị trừ tiền hai lần và hoàn tác",
    "khóa cơ sở dữ liệu giao dịch đồng thời gây bế tắc",
    "xử lý bất đồng bộ hàng đợi và lưu trữ bộ nhớ đệm",
    "xác thực phiên đăng nhập và làm mới mã thông báo",
    "kiểm tra phân quyền truy cập và bảo mật lỗ hổng tiêm mã",
    "đổi mật khẩu thông tin đăng nhập hết hạn phiên làm việc",
    "phiên đăng nhập bị văng ra khi làm mới và cấp lại",
    "sửa lỗi hiển thị giá trên bảng giá thị trường",
    "tạo ma trận kiểm thử từ đặc tả hợp đồng giao diện lập trình",
    "giả lập mạng và chặn phản hồi lỗi hết thời gian chờ",
    "sai lệch lược đồ dữ liệu trả về khi gọi dịch vụ",
    "đo chỉ số hiệu năng độ trễ phản hồi chậm trên trang",
    "kiểm thử chịu tải cao và phân tích nghẽn cổ chai quá tải",
    "giới hạn tốc độ khi hệ thống quá tải và chịu tải",
    "kịch bản kiểm thử tự động chạy chập chờn không ổn định",
    "lúc được lúc không lúc chạy đạt lúc lỗi vì chờ tĩnh ngủ tĩnh",
    "tự sửa bộ chọn phần tử không tìm thấy nút trên mô hình trang",
    "chuyển đổi mã kịch bản kiểm thử tự động hóa lớp trang",
    "kiểm thử đột biến và phân tích nguyên nhân gốc khám nghiệm lỗi",
    "tái cấu trúc thiết kế lại kiến trúc và lập kế hoạch lên kế hoạch",
    "rà soát cổng chất lượng kiểm chứng bất biến định dạng trạng thái",
    "kiểm tra trợ năng giao diện màn hình bàn phím và màu sắc",
    "dọn dẹp dữ liệu và bản ghi sau khi chạy kiểm thử",
    "chỉnh giúp phần giỏ hàng hôm trước cho mượt hơn đi",
    "làm lại giùm chỗ xử lý hôm qua cho sạch sẽ hơn",
    "nó cứ giật giật khó chịu quá không chạy được như trước",
    "xuất báo cáo và tập tin dữ liệu cùng lúc không bị lỗi",
    "sửa lỗi thanh toán trong mã nguồn theo tài liệu hướng dẫn",
)

_VITERBI_UNIGRAMS: Counter[str] = Counter()
_VITERBI_BIGRAMS: Counter[Tuple[str, str]] = Counter()
_VITERBI_CANDIDATES: Dict[str, Tuple[str, ...]] = {}
_VITERBI_TOTAL_UNIGRAMS: int = 0
_VITERBI_VOCAB_SIZE: int = 1


def _compile_viterbi_lm() -> None:
    """Compiles unigram, bigram, and candidate tables from the embedded QA corpus."""
    global _VITERBI_TOTAL_UNIGRAMS, _VITERBI_VOCAB_SIZE
    cand_counts: Dict[str, Counter[str]] = defaultdict(Counter)

    for sentence in _QA_VI_CORPUS:
        tokens = sentence.split()
        prev = "<bos>"
        for tok in tokens:
            _VITERBI_UNIGRAMS[tok] += 1
            _VITERBI_BIGRAMS[(prev, tok)] += 1
            if tok != "<num>":
                cand_counts[_fold_ascii(tok)][tok] += 1
            prev = tok

    _VITERBI_TOTAL_UNIGRAMS = sum(_VITERBI_UNIGRAMS.values())
    _VITERBI_VOCAB_SIZE = max(len(_VITERBI_UNIGRAMS), 1)
    for ascii_key, counts in cand_counts.items():
        top = [w for w, _ in counts.most_common(MAX_CANDIDATES_PER_SYLLABLE)]
        _VITERBI_CANDIDATES[ascii_key] = tuple(top)


_compile_viterbi_lm()

# Protected span splitter: inline code, URLs, slash commands, file paths, underscore/dotted identifiers
_PROTECTED_SPAN_RE = re.compile(
    r"(`[^`]+`|https?://\S+|(?<!\w)/[a-zA-Z][a-zA-Z0-9_-]{1,48}|"
    r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_./-]+|[a-zA-Z0-9]+_[a-zA-Z0-9_]+|"
    r"[a-zA-Z0-9]+\.[a-zA-Z]{2,6})"
)
_WORD_OR_SEP_RE = re.compile(r"([A-Za-zÀ-ỹà-ỹđĐ]+|\d+|[^A-Za-zÀ-ỹà-ỹđĐ\d]+)")


def _apply_case(original: str, restored: str) -> str:
    """Preserves original casing (TitleCase / lowercase) on restored Vietnamese syllables."""
    if original.isupper() and len(original) > 1:
        return original
    if original and original[0].isupper():
        return restored[0].upper() + restored[1:]
    return restored


def _bigram_log_prob(prev_tok: str, curr_tok: str, lam: float) -> float:
    """Computes interpolated bigram + Laplace unigram log-probability."""
    prev_count = _VITERBI_UNIGRAMS.get(prev_tok, 0)
    bi_prob = (_VITERBI_BIGRAMS.get((prev_tok, curr_tok), 0) / prev_count) if prev_count > 0 else 0.0
    uni_prob = (_VITERBI_UNIGRAMS.get(curr_tok, 0) + 1.0) / (_VITERBI_TOTAL_UNIGRAMS + _VITERBI_VOCAB_SIZE)
    prob = lam * bi_prob + (1.0 - lam) * uni_prob
    return math.log(max(prob, 1e-12))


def _candidates_for_word(word: str) -> Tuple[str, ...]:
    """Returns candidate restorations for a single word or number token."""
    if word.isdigit():
        return ("<num>",)
    low = word.lower()
    if _VI_DIACRITIC_RE.search(low) or (word.isupper() and len(word) > 1):
        return (low,)
    cands = _VITERBI_CANDIDATES.get(low)
    return cands if cands else (low,)


def _best_prev_state(prev_dp: Mapping[str, float], cur_c: str, lam: float) -> Tuple[float, str]:
    """Selects the maximum-scoring predecessor candidate for a Viterbi trellis step."""
    best_score = -1e18
    best_prev = next(iter(prev_dp))
    for prev_c, prev_score in prev_dp.items():
        score = prev_score + _bigram_log_prob(prev_c, cur_c, lam)
        if score > best_score:
            best_score = score
            best_prev = prev_c
    return best_score, best_prev


def _viterbi_decode_chain(words: Sequence[str], lam: float) -> List[str]:
    """Runs O(T * K^2) Viterbi decoding over a bounded syllable chain (T <= 64)."""
    if not words:
        return []
    cand_lists = [_candidates_for_word(w) for w in words]
    dp: List[Dict[str, float]] = [{c: _bigram_log_prob("<bos>", c, lam) for c in cand_lists[0]}]
    back: List[Dict[str, str]] = [{c: "<bos>" for c in cand_lists[0]}]

    for t in range(1, len(words)):
        cur_dp: Dict[str, float] = {}
        cur_back: Dict[str, str] = {}
        prev_dp = dp[t - 1]
        for cur_c in cand_lists[t]:
            best_score, best_prev = _best_prev_state(prev_dp, cur_c, lam)
            cur_dp[cur_c] = best_score
            cur_back[cur_c] = best_prev
        dp.append(cur_dp)
        back.append(cur_back)

    best_last = max(dp[-1], key=lambda k: dp[-1][k])
    decoded = [best_last]
    for t in range(len(words) - 1, 0, -1):
        best_last = back[t][best_last]
        decoded.append(best_last)
    decoded.reverse()

    return [
        orig if orig.isdigit() else _apply_case(orig, rest)
        for orig, rest in zip(words, decoded)
    ]


def _restore_segment(segment: str, lam: float) -> str:
    """Restores Vietnamese diacritics on an unprotected text segment with 64-token chain caps."""
    pieces = _WORD_OR_SEP_RE.findall(segment)
    word_indices = [i for i, p in enumerate(pieces) if p.isalpha() or p.isdigit()]
    if not word_indices:
        return segment

    # Process in bounded chunks of MAX_VITERBI_CHAIN
    for start in range(0, len(word_indices), MAX_VITERBI_CHAIN):
        chunk_idx = word_indices[start : start + MAX_VITERBI_CHAIN]
        chunk_words = [pieces[i] for i in chunk_idx]
        restored_words = _viterbi_decode_chain(chunk_words, lam)
        for idx, new_w in zip(chunk_idx, restored_words):
            pieces[idx] = new_w
    return "".join(pieces)


def restore_qa_vietnamese_diacritics(text: str, lambda_bigram: float = 0.8) -> str:
    """Restores QA-domain Vietnamese diacritics via Viterbi while bypassing code/URLs/paths."""
    if not isinstance(text, str) or not text:
        return ""
    bounded = text[:MAX_INPUT_CHARS]
    lam = min(max(float(lambda_bigram), 0.0), 1.0)
    parts = _PROTECTED_SPAN_RE.split(bounded)
    out: List[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(part)
        else:
            out.append(_restore_segment(part, lam))
    return "".join(out)


# ------------------------------------------------------------------------------
# 5. Unified Orthography + Phonotactic Pipeline
# ------------------------------------------------------------------------------


def _has_vietnamese_context(tokens: Sequence[str]) -> bool:
    """Determines whether unprotected tokens exhibit Vietnamese context for weak Telex/shorthand."""
    alpha_tokens = [t for t in tokens if t.isalpha()]
    if not alpha_tokens:
        return False
    for tok in alpha_tokens:
        low = tok.lower()
        if _VI_DIACRITIC_RE.search(tok) or low in _UNAMBIGUOUS_VI_SHORTHAND:
            return True
        if _STRONG_TELEX_RE.search(low) and low not in _EN_TELEX_SAFELIST and tok.islower():
            return True
    vi_valid = sum(1 for t in alpha_tokens if is_valid_vietnamese_syllable(t))
    return len(alpha_tokens) >= 2 and (vi_valid / len(alpha_tokens)) >= 0.6


def _normalize_unprotected_segment(
    segment: str,
    expand_shorthand: bool,
    expand_guarded_telex: bool,
    vi_context: bool,
) -> Tuple[str, bool]:
    """Normalizes shorthand & guarded Telex on an unprotected text segment."""
    pieces = _WORD_OR_SEP_RE.findall(segment)
    changed = False
    for i, piece in enumerate(pieces):
        if not piece.isalpha() or not piece.islower():
            continue
        if expand_shorthand and len(piece) <= 6:
            mapped = _UNAMBIGUOUS_VI_SHORTHAND.get(piece)
            if mapped is None and vi_context:
                mapped = _CONTEXT_VI_SHORTHAND.get(piece)
            if mapped is not None:
                pieces[i] = mapped
                changed = True
                continue
        if expand_guarded_telex and len(piece) <= 9:
            decoded = _decode_telex_token(piece, allow_weak_tone=vi_context)
            if decoded is not None:
                pieces[i] = decoded
                changed = True
    return "".join(pieces), changed


def canonicalize_vietnamese_orthography(
    text: str,
    expand_shorthand: bool = True,
    expand_guarded_telex: bool = True,
) -> SyllabicAnalysisDTO:
    """Runs NFC/tone canonicalization, guarded Telex/shorthand expansion, and phonotactic scoring."""
    if not isinstance(text, str) or not text:
        return SyllabicAnalysisDTO("", "", 0, 0, 0.0, False)

    bounded = _canonicalize_tone_placement(text[:MAX_INPUT_CHARS])
    parts = _PROTECTED_SPAN_RE.split(bounded)
    unprotected_tokens = [
        p for i, seg in enumerate(parts) if i % 2 == 0 for p in _WORD_OR_SEP_RE.findall(seg) if p.isalpha()
    ]
    vi_context = _has_vietnamese_context(unprotected_tokens)

    had_expansion = False
    rebuilt: List[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            rebuilt.append(part)
        else:
            norm_seg, seg_changed = _normalize_unprotected_segment(
                part, expand_shorthand, expand_guarded_telex, vi_context
            )
            rebuilt.append(norm_seg)
            had_expansion = had_expansion or seg_changed

    canonical_nfc = _canonicalize_tone_placement("".join(rebuilt))
    restored = restore_qa_vietnamese_diacritics(canonical_nfc) if vi_context else canonical_nfc

    # Compute phonotactic syllable ratio across alpha tokens in canonical_nfc
    alpha_tokens = [tok for tok in re.findall(r"[A-Za-zÀ-ỹà-ỹđĐ]+", canonical_nfc)]
    total_alpha = len(alpha_tokens)
    valid_vi = sum(1 for tok in alpha_tokens if is_valid_vietnamese_syllable(tok))
    ratio = round(valid_vi / total_alpha, 4) if total_alpha > 0 else 0.0

    return SyllabicAnalysisDTO(
        canonical_nfc_text=canonical_nfc,
        restored_diacritics_text=restored,
        valid_vi_syllable_count=valid_vi,
        total_alpha_tokens=total_alpha,
        vi_syllable_ratio=ratio,
        had_telex_or_shorthand=had_expansion,
    )


# ------------------------------------------------------------------------------
# 6. VnCoreNLP Longest-Match + Ripple-Down Rules (RDR) Resolver
# ------------------------------------------------------------------------------


def _evaluate_rdr_rule(
    rule: RDRExceptionRuleDTO,
    folded_text: str,
) -> Tuple[Tuple[str, ...], Optional[str]]:
    """Evaluates a single RDRExceptionRuleDTO against folded_text (nesting <= 2)."""
    pos_pat = rule.positive_context_pattern
    neg_pat = rule.negative_context_pattern
    pos_match = bool(re.search(pos_pat, folded_text, re.IGNORECASE)) if pos_pat else False
    neg_match = bool(re.search(neg_pat, folded_text, re.IGNORECASE)) if neg_pat else False

    if pos_pat and neg_pat:
        if pos_match and neg_match:
            return rule.default_tokens, rule.conflict_tag
        return (rule.override_tokens, None) if (pos_match and not neg_match) else (rule.default_tokens, None)
    if pos_pat:
        return (rule.override_tokens, None) if pos_match else (rule.default_tokens, None)
    if neg_pat:
        return (rule.override_tokens, rule.conflict_tag) if neg_match else (rule.default_tokens, None)
    return rule.default_tokens, None


def _match_longest_at(
    words: Sequence[str],
    index: int,
    max_ngram: int,
    lexicon: Mapping[str, Tuple[str, ...]],
    rule_map: Mapping[str, RDRExceptionRuleDTO],
) -> Optional[Tuple[int, str]]:
    """Finds the longest matching n-gram starting at index (Longest-Match down to 1)."""
    limit = min(max_ngram, len(words) - index)
    for length in range(limit, 0, -1):
        ngram = " ".join(words[index : index + length])
        if ngram in rule_map or ngram in lexicon:
            return length, ngram
    return None


def resolve_longest_match_rdr(
    words: Sequence[str],
    folded_text: str,
    lexicon: Dict[str, Tuple[str, ...]],
    rdr_rules: Sequence[RDRExceptionRuleDTO],
    max_ngram: int = 5,
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Resolves canonical tokens and context conflicts via Longest-Match + RDR rules."""
    if not words:
        return (), ()

    rule_map: Dict[str, RDRExceptionRuleDTO] = {r.ngram: r for r in rdr_rules}
    tokens: List[str] = []
    seen_tokens: set[str] = set()
    conflicts: List[str] = []
    seen_conflicts: set[str] = set()

    idx = 0
    n_words = len(words)
    effective_max = max(int(max_ngram), 1)
    while idx < n_words:
        hit = _match_longest_at(words, idx, effective_max, lexicon, rule_map)
        if hit is None:
            idx += 1
            continue
        length, ngram = hit
        idx += length
        rule = rule_map.get(ngram)
        emitted, conflict = _evaluate_rdr_rule(rule, folded_text) if rule is not None else (lexicon[ngram], None)
        if conflict and conflict not in seen_conflicts:
            seen_conflicts.add(conflict)
            conflicts.append(conflict)
        for tok in emitted:
            if tok not in seen_tokens:
                seen_tokens.add(tok)
                tokens.append(tok)

    return tuple(tokens), tuple(conflicts)
