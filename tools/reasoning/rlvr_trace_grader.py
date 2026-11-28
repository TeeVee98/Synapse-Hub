# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""Grade locally verifiable reasoning traces and select inference candidates."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
import json
import math
import re
from statistics import fmean, stdev
import sys


@dataclass(frozen=True)
class RLVRTraceScoreDTO:
    format_score: float
    tag_count_score: float
    reasoning_steps_score: float
    cosine_length_score: float
    repetition_penalty: float
    overlong_penalty: float
    composite_reward: float
    extracted_answer: str | None = None


@dataclass(frozen=True)
class InferenceScalingResultDTO:
    selected_answer: str
    vote_counts: dict[str, int]
    consensus_ratio: float
    refinement_rounds: int
    stopped_early_no_gain: bool
    group_advantages: tuple[float, ...] = ()


@dataclass(frozen=True)
class ReasoningModelProfileDTO:
    model_id: str
    temperature: float
    avoid_system_prompt: bool
    enforce_think_prefix: str
    estimated_kv_cache_mb: float
    estimated_flops_per_token: float


_TAGS = ("<think>", "</think>", "<answer>", "</answer>")
_STEPS = re.compile(
    r"\bStep[ \t]+(?P<step>\d+):|^[ \t]*(?P<number>\d+)\.[ \t]+"
    r"|^[ \t]*[-*][ \t]+(?P<bullet>[^\n]+)|\b(?P<transition>First|Second|Next|Finally),",
    flags=re.MULTILINE | re.IGNORECASE,
)
_WORDS = re.compile(r"\w+")
_BOX_TOKENS = re.compile(r"\\[{}\\]|\\boxed[ \t]*\{|[{}]")


def _trace_parts(trace: str) -> tuple[str, str] | None:
    think_open, think_close, answer_open, answer_close = _TAGS
    text = trace.strip()
    if not text.startswith(think_open) or not text.endswith(answer_close):
        return None
    thought, delimiter, remaining = text[len(think_open):].partition(think_close)
    final = remaining.lstrip()
    if not delimiter or not final.startswith(answer_open):
        return None
    reasoning = thought.strip()
    answer = final[len(answer_open):-len(answer_close)].strip()
    if not reasoning or not answer or any(trace.count(tag) != 1 for tag in _TAGS):
        return None
    return reasoning, answer


def _answer_key(answer: str) -> str:
    return " ".join(answer.split()).casefold()


class RLVRTraceGrader:
    """Score trace structure, exact answer verification, length, and repetition."""

    @staticmethod
    def format_reward(trace: str) -> float:
        return float(_trace_parts(trace) is not None)

    @staticmethod
    def tag_count_reward(trace: str) -> float:
        return sum(0.25 for tag in _TAGS if trace.count(tag) == 1)

    @staticmethod
    def reasoning_steps_reward(reasoning: str) -> float:
        steps = set()
        for match in _STEPS.finditer(reasoning):
            number = match["step"] or match["number"]
            if number:
                steps.add(("number", number.lstrip("0")))
            elif match["bullet"]:
                steps.add(("bullet", _answer_key(match["bullet"])))
            else:
                steps.add(("transition", match["transition"].casefold()))
        return min(len(steps) / 3, 1.0)

    @staticmethod
    def cosine_scaled_length_reward(length: int, correct: bool, *, max_length: int = 1024) -> float:
        if length < 0 or max_length <= 0:
            raise ValueError("Length must be non-negative and max_length must be positive")
        progress = min(length / max_length, 1.0)
        shortness = (1 + math.cos(math.pi * progress)) / 2
        return 0.5 + 0.5 * shortness if correct else -0.5 - 0.5 * shortness

    @staticmethod
    def ngram_repetition_penalty(trace: str, *, ngram_size: int = 3) -> float:
        if ngram_size < 1:
            raise ValueError("ngram_size must be positive")
        words = _WORDS.findall(trace.casefold())
        total = len(words) - ngram_size + 1
        if total <= 0:
            return 0.0
        unique = {tuple(words[index:index + ngram_size]) for index in range(total)}
        return -(total - len(unique)) / total

    @staticmethod
    def soft_overlong_penalty(length: int, *, max_length: int, soft_limit: int) -> float:
        if length < 0 or not 0 < soft_limit <= max_length:
            raise ValueError("Require non-negative length and 0 < soft_limit <= max_length")
        overage = length - (max_length - soft_limit)
        return -min(1.0, max(0.0, overage / soft_limit))

    @staticmethod
    def compute_grpo_advantages(rewards: Sequence[float], *, epsilon: float = 1e-4) -> tuple[float, ...]:
        if not math.isfinite(epsilon) or epsilon <= 0:
            raise ValueError("epsilon must be positive and finite")
        if not all(math.isfinite(reward) for reward in rewards):
            raise ValueError("Group rewards must be finite")
        if len(rewards) < 2:
            return (0.0,) * len(rewards)
        average = fmean(rewards)
        scale = stdev(rewards) + epsilon
        return tuple((reward - average) / scale for reward in rewards)

    def grade(
        self, trace: str, *, expected_answer: str | None = None,
        max_length: int = 1024, soft_limit: int | None = None,
    ) -> RLVRTraceScoreDTO:
        """Use lexical exactness for verification and word counts for length."""
        if max_length < 1:
            raise ValueError("max_length must be positive")
        parts = _trace_parts(trace)
        reasoning, answer = parts if parts is not None else ("", None)
        if answer is not None:
            answer = InferenceScalingController.extract_last_boxed(answer) or answer
        length = len(_WORDS.findall(trace.strip()))
        format_score = float(parts is not None)
        tag_score = self.tag_count_reward(trace)
        steps_score = self.reasoning_steps_reward(reasoning)
        verified = answer is not None and expected_answer is not None and _answer_key(answer) == _answer_key(expected_answer)
        cosine_score = (
            self.cosine_scaled_length_reward(length, verified, max_length=max_length)
            if length and expected_answer is not None else 0.0
        )
        repetition = self.ngram_repetition_penalty(reasoning if parts is not None else trace)
        penalty = self.soft_overlong_penalty(
            length, max_length=max_length, soft_limit=min(128, max_length) if soft_limit is None else soft_limit,
        )
        composite = format_score + tag_score + steps_score + cosine_score + 2 * repetition + penalty
        return RLVRTraceScoreDTO(
            format_score, tag_score, steps_score, cosine_score, repetition, penalty, composite, answer,
        )


class InferenceScalingController:
    """Select likely answers and retain only strictly improving refinements."""

    MAX_REFINEMENT_ROUNDS = 5

    @staticmethod
    def extract_last_boxed(text: str) -> str | None:
        """Read balanced LaTeX boxes in one pass, including nested and escaped braces."""
        stack: list[tuple[int, bool]] = []
        latest = -1
        selected = None
        for match in _BOX_TOKENS.finditer(text):
            token = match[0]
            if token == "}" and stack:
                start, boxed = stack.pop()
                if boxed and start > latest:
                    candidate = text[start:match.start()].strip()
                    if candidate:
                        latest, selected = start, candidate
            elif token.endswith("{") and token != r"\{":
                stack.append((match.end(), token != "{"))
        return selected

    def _candidate_answer(self, text: str) -> str:
        parts = _trace_parts(text)
        candidate = parts[1] if parts is not None else text.strip()
        return self.extract_last_boxed(candidate) or candidate

    def self_consistency_vote(self, candidates: Sequence[str]) -> InferenceScalingResultDTO:
        votes: Counter[str] = Counter()
        labels: dict[str, str] = {}
        for candidate in candidates:
            answer = self._candidate_answer(candidate)
            if answer:
                key = _answer_key(answer)
                labels.setdefault(key, answer)
                votes[key] += 1
        if not votes:
            return InferenceScalingResultDTO("", {}, 0.0, 0, False)
        key, count = votes.most_common(1)[0]
        return InferenceScalingResultDTO(
            labels[key], {labels[item]: frequency for item, frequency in votes.items()},
            count / sum(votes.values()), 0, False,
        )

    def self_refinement_loop(
        self, initial: str, refine: Callable[[str, int], str], score: Callable[[str], float], *,
        max_rounds: int = 3,
    ) -> InferenceScalingResultDTO:
        if max_rounds < 0:
            raise ValueError("max_rounds must be non-negative")
        strongest, best_score = initial, score(initial)
        if not math.isfinite(best_score):
            raise ValueError("Refinement scores must be finite")
        scores = [best_score]
        rounds = 0
        stopped = False
        for round_number in range(1, min(max_rounds, self.MAX_REFINEMENT_ROUNDS) + 1):
            rounds = round_number
            candidate = refine(strongest, round_number)
            candidate_score = score(candidate)
            if not math.isfinite(candidate_score):
                raise ValueError("Refinement scores must be finite")
            scores.append(candidate_score)
            if candidate_score <= best_score:
                stopped = True
                break
            strongest, best_score = candidate, candidate_score

        selected = self._candidate_answer(strongest)
        return InferenceScalingResultDTO(
            selected, {}, 0.0, rounds, stopped, RLVRTraceGrader.compute_grpo_advantages(scores),
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-answer")
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--json", action="store_true", help="Print the grade as JSON")
    args = parser.parse_args(argv)
    try:
        result = RLVRTraceGrader().grade(
            sys.stdin.read(), expected_answer=args.expected_answer, max_length=args.max_length,
        )
    except ValueError as error:
        print(json.dumps({"error": str(error)}) if args.json else str(error))
        return 2
    print(json.dumps(asdict(result)) if args.json else f"Composite reward: {result.composite_reward:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
