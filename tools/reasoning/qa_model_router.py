# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-
"""Cost & Latency-Aware QA Model Router (tools/reasoning/qa_model_router.py).

Inspired by AgentScope 2.0's ModelRouterMiddleware:
Analyzes task complexity, keyword semantics, and context token footprint to route
QA prompts dynamically to the most cost-efficient and capable LLM tier
(Flash-Lite for triage, Flash for execution, Pro/Reasoning for root cause analysis).

Author: Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
License: MIT
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

# Enforce UTF-8 stdout/stderr encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class ModelComputeTier(Enum):
    """Categorized model compute and intelligence tiers."""

    FLASH_LITE = "flash_lite"      # Micro-tasks, linting, format check, state polling
    FLASH = "flash"                # Standard test running, assertion check, smoke tests
    PRO_REASONING = "pro"          # Root cause analysis, POM refactor, flaky self-healing


@dataclass(frozen=True)
class ModelRouteDecision:
    """Deterministic routing verdict produced by QAModelRouter."""

    tier: ModelComputeTier
    recommended_model: str
    estimated_cost_ratio: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "recommended_model": self.recommended_model,
            "estimated_cost_ratio": self.estimated_cost_ratio,
            "reason": self.reason,
        }


class QAModelRouter:
    """Heuristic semantic router optimizing cost vs intelligence for QA workflows."""

    COMPLEX_REASONING_PATTERNS = [
        re.compile(r"\b(?:root\s+cause|rca|flaky|heal|healing|autopsy)\b", re.IGNORECASE),
        re.compile(r"\b(?:refactor|redesign|architecture|deadlock|race\s+condition)\b", re.IGNORECASE),
        re.compile(r"\b(?:pom\s+design|clean\s+pom\s+audit|fuzz|fuzzer)\b", re.IGNORECASE),
        re.compile(r"\b(?:deep\s+plan|super-plan|tree-of-thought|tot)\b", re.IGNORECASE),
    ]

    LITE_TRIAGE_PATTERNS = [
        re.compile(r"\b(?:lint|format|ruff|prettier|clean\s+encoding|utf-8)\b", re.IGNORECASE),
        re.compile(r"\b(?:list\s+tools|status|health\s+check|catalog|quick\s+check)\b", re.IGNORECASE),
        re.compile(r"\b(?:distill|summary\s+excerpt|git\s+status)\b", re.IGNORECASE),
    ]

    DEFAULT_MODELS = {
        ModelComputeTier.FLASH_LITE: "gemini-2.5-flash-lite",
        ModelComputeTier.FLASH: "gemini-2.5-flash",
        ModelComputeTier.PRO_REASONING: "gemini-2.5-pro",
    }

    COST_RATIOS = {
        ModelComputeTier.FLASH_LITE: 0.05,
        ModelComputeTier.FLASH: 0.20,
        ModelComputeTier.PRO_REASONING: 1.00,
    }

    def route_task(
        self,
        task_description: str,
        context_tokens: int = 0,
    ) -> ModelRouteDecision:
        """Determines the optimal model tier based on task complexity and context length."""
        text = str(task_description or "").strip()
        if not text:
            tier = ModelComputeTier.FLASH_LITE
            return ModelRouteDecision(
                tier=tier,
                recommended_model=self.DEFAULT_MODELS[tier],
                estimated_cost_ratio=self.COST_RATIOS[tier],
                reason="Empty or trivial query defaults to Flash-Lite.",
            )

        # 1. Complex reasoning keywords prioritize PRO_REASONING
        for pattern in self.COMPLEX_REASONING_PATTERNS:
            match = pattern.search(text)
            if match:
                tier = ModelComputeTier.PRO_REASONING
                return ModelRouteDecision(
                    tier=tier,
                    recommended_model=self.DEFAULT_MODELS[tier],
                    estimated_cost_ratio=self.COST_RATIOS[tier],
                    reason=f"Task involves deep reasoning or diagnosis ({match.group(0)}).",
                )

        # 2. Large context (> 30k tokens) needs heavy context reasoning
        if context_tokens > 30000:
            tier = ModelComputeTier.PRO_REASONING
            return ModelRouteDecision(
                tier=tier,
                recommended_model=self.DEFAULT_MODELS[tier],
                estimated_cost_ratio=self.COST_RATIOS[tier],
                reason=f"High context load ({context_tokens:,} tokens) requires Pro tier reasoning.",
            )

        # 3. Micro-tasks and triage map to FLASH_LITE
        for pattern in self.LITE_TRIAGE_PATTERNS:
            match = pattern.search(text)
            if match:
                tier = ModelComputeTier.FLASH_LITE
                return ModelRouteDecision(
                    tier=tier,
                    recommended_model=self.DEFAULT_MODELS[tier],
                    estimated_cost_ratio=self.COST_RATIOS[tier],
                    reason=f"Task is a lightweight linter/triage operation ({match.group(0)}).",
                )

        # 4. Standard default is FLASH
        tier = ModelComputeTier.FLASH
        return ModelRouteDecision(
            tier=tier,
            recommended_model=self.DEFAULT_MODELS[tier],
            estimated_cost_ratio=self.COST_RATIOS[tier],
            reason="Standard QA workflow execution mapped to balanced Flash model.",
        )

    def extract_intended_qa_action(self, prompt: str) -> Optional[str]:
        """Maps natural language prompts to executable Synapse Hub QA action commands."""
        text = str(prompt or "").lower().strip()
        if not text:
            return None

        if any(k in text for k in ("fast gate", "fast-gate", "cổng nhanh", "quick gate")):
            return "fast-gate"
        if any(k in text for k in ("smoke", "smoke test", "smoke-test")):
            return "fast-gate"
        if any(k in text for k in ("verify all", "verify-all", "10 cổng", "10 quality gates", "toàn diện", "full gate")):
            return "hub-verify"
        if any(k in text for k in ("pass ảo", "nuốt lỗi", "linter", "infer", "swallow")):
            return "infer-lint"
        if any(k in text for k in ("clean pom", "clean-pom", "kiểm tra pom", "selector")):
            return "clean-pom"
        if any(k in text for k in ("doctor", "chẩn đoán", "môi trường", "check env")):
            return "doctor"
        if any(k in text for k in ("đột biến", "mutant", "mutation")):
            return "mutate"
        if any(k in text for k in ("alm", "jira", "sync bug")):
            return "alm-status"

        return None

    def get_degraded_fallback_model(self, current_tier: ModelComputeTier) -> str:
        """Returns the fallback model to maintain service continuity under rate limits or quota errors."""
        if current_tier == ModelComputeTier.PRO_REASONING:
            return self.DEFAULT_MODELS[ModelComputeTier.FLASH]
        return self.DEFAULT_MODELS[ModelComputeTier.FLASH_LITE]
