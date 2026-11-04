#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee998). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee998/Synapse-Hub)

"""
Tier-2 Skill Routing & Collision Guard (Addy Osmani Pattern)
------------------------------------------------------------
Computes pairwise cosine similarity across all SKILL.md descriptions.
Operates 100% offline with zero LLM tokens using a lightweight suffix-stripping
stemmer heuristic and TF-IDF word frequency representation.

Enforces:
  - Warning when description similarity >= 0.50 (semantic proximity)
  - Critical Error (Quality Gate Failure) when similarity >= 0.75 (ambiguous routing)

Usage:
  python tools/skill_collision_guard.py [--dir .agents/skills] [--threshold 0.75] [--json]
"""

import os
import sys
import re
import math
import json
import argparse
from typing import Dict, List, Tuple
from collections import Counter

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
    "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on",
    "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "should", "shouldn't", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "were", "weren't", "what",
    "when", "where", "which", "while", "who", "whom", "why", "with", "won't", "would", "wouldn't",
    "you", "your", "yours", "yourself", "yourselves", "use", "when", "allows", "provides", "designed"
}


def strip_suffix(word: str) -> str:
    """Lightweight suffix-stripping heuristic (Addy Osmani Tier-2 standard)."""
    if len(word) <= 4:
        return word
    for suffix in ("ing", "tion", "ment", "ness", "able", "ible", "ize", "ise", "ies", "es", "ed", "ly", "al", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]
    return word


def tokenize(text: str) -> List[str]:
    """Tokenizes text, strips punctuation, removes stopwords and applies suffix stripping."""
    words = re.findall(r"\b[a-zA-Z0-9_\-]+\b", text.lower())
    tokens = []
    for w in words:
        cleaned = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", w)
        if len(cleaned) >= 2 and cleaned not in STOPWORDS:
            tokens.append(strip_suffix(cleaned))
    return tokens


def build_tf_vector(tokens: List[str]) -> Dict[str, float]:
    """Builds normalized term-frequency vector."""
    counts = Counter(tokens)
    total = len(tokens)
    if total == 0:
        return {}
    return {word: count / total for word, count in counts.items()}


def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Computes cosine similarity between two term-frequency vectors."""
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[x] * vec2[x] for x in intersection)
    sum1 = sum(v ** 2 for v in vec1.values())
    sum2 = sum(v ** 2 for v in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    if not denominator:
        return 0.0
    return float(numerator) / denominator


class SkillCollisionGuard:
    """Audits skill descriptions across repository for routing collisions and ambiguous triggers."""

    def __init__(self, skills_dir: str = ".agents/skills", threshold: float = 0.75, warn_threshold: float = 0.50):
        self.skills_dir = skills_dir
        self.threshold = threshold
        self.warn_threshold = warn_threshold

    def load_descriptions(self) -> Dict[str, str]:
        """Loads all SKILL.md files and extracts their description strings."""
        descriptions = {}
        if not os.path.exists(self.skills_dir):
            return descriptions

        for root, _, files in os.walk(self.skills_dir):
            for file in files:
                if file.lower() == "skill.md":
                    full_path = os.path.join(root, file)
                    skill_name, desc = self._extract_frontmatter(full_path)
                    if skill_name and desc:
                        descriptions[skill_name] = desc
        return descriptions

    def _extract_frontmatter(self, path: str) -> Tuple[str, str]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return "", ""

        match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if match:
            fm = match.group(1)
            name_m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
            desc_m = re.search(r"^description:\s*[\"']?(.*?)[\"']?$", fm, re.MULTILINE)
            name = name_m.group(1).strip() if name_m else os.path.basename(os.path.dirname(path))
            desc = desc_m.group(1).strip() if desc_m else ""
            return name, desc

        fallback_name = os.path.basename(os.path.dirname(path))
        return fallback_name, ""

    def audit(self) -> Tuple[bool, List[Dict[str, any]]]:
        """
        Computes pairwise similarity.
        Returns (is_clean, report_items).
        """
        descriptions = self.load_descriptions()
        names = sorted(list(descriptions.keys()))
        vectors = {name: build_tf_vector(tokenize(descriptions[name])) for name in names}

        findings = []
        has_critical = False

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                name_a = names[i]
                name_b = names[j]
                sim = cosine_similarity(vectors[name_a], vectors[name_b])

                if sim >= self.threshold:
                    has_critical = True
                    findings.append({
                        "level": "CRITICAL",
                        "skill_a": name_a,
                        "skill_b": name_b,
                        "similarity": round(sim, 3),
                        "message": f"Critical Collision: '{name_a}' and '{name_b}' have cosine similarity {sim:.3f} >= {self.threshold}"
                    })
                elif sim >= self.warn_threshold:
                    findings.append({
                        "level": "WARNING",
                        "skill_a": name_a,
                        "skill_b": name_b,
                        "similarity": round(sim, 3),
                        "message": f"Proximity Warning: '{name_a}' and '{name_b}' have similarity {sim:.3f} >= {self.warn_threshold}"
                    })

        return (not has_critical), findings


def run_guard(skills_dir: str = ".agents/skills", threshold: float = 0.75, warn_threshold: float = 0.50, output_json: bool = False) -> int:
    guard = SkillCollisionGuard(skills_dir, threshold=threshold, warn_threshold=warn_threshold)
    passed, findings = guard.audit()

    if output_json:
        print(json.dumps({
            "skills_dir": skills_dir,
            "passed": passed,
            "threshold": threshold,
            "warn_threshold": warn_threshold,
            "findings": findings
        }, indent=2))
        return 0 if passed else 1

    print("\n" + "=" * 70)
    print("  TIER-2 SKILL ROUTING & COLLISION GUARD (ADDY OSMANI PATTERN)")
    print("=" * 70)
    print(f"Skills Directory : {skills_dir}")
    print(f"Collision Threshold: {threshold} (FAIL) | Warning Threshold: {warn_threshold} (WARN)")

    criticals = [f for f in findings if f["level"] == "CRITICAL"]
    warnings = [f for f in findings if f["level"] == "WARNING"]

    if warnings:
        print(f"\n⚠️  {len(warnings)} Near-Neighbor Warnings detected (similarity >= {warn_threshold}):")
        for w in warnings:
            print(f"   - {w['message']}")

    if criticals:
        print(f"\n❌ {len(criticals)} CRITICAL COLLISION(S) detected (similarity >= {threshold}):")
        for c in criticals:
            print(f"   [FAIL] {c['message']}")
        print("\n[DoD BLOCKED] High similarity causes routing ambiguity and context contamination.")
        print("=" * 70 + "\n")
        return 1

    print(f"\n✅ [PASS] 0 routing collisions detected. All skill descriptions uniquely segmented.\n")
    print("=" * 70 + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Tier-2 Skill Routing & Collision Guard")
    parser.add_argument("--dir", default=".agents/skills", help="Directory containing skill packages")
    parser.add_argument("--threshold", type=float, default=0.75, help="Critical similarity threshold (default: 0.75)")
    parser.add_argument("--warn-threshold", type=float, default=0.50, help="Warning similarity threshold (default: 0.50)")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    return run_guard(skills_dir=args.dir, threshold=args.threshold, warn_threshold=args.warn_threshold, output_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
