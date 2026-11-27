#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
tools/reasoning/dynamic_budget_engine.py — Tier 9 Hard Stop-Sequences & Dynamic Thinking Budget
-------------------------------------------------------------------------------------------------
Eliminates conversational chatter and reasoning overhead across LLM execution turns:
  1. Dynamic Thinking Budget & Max Tokens:
     - Mechanical steps (read_file, format, re_run_test, git_status, FSM DISCOVERY/HEADLESS_EXEC):
       forces thinking_budget = 0 and max_tokens = 256.
     - Analytical / RCA steps (autopsy_heal, failure_analyst, FSM AUTOPSY_HEAL):
       allocates thinking_budget = 2048 (or 4096) and max_tokens = 4096.
     - Code Synthesis steps (pom_crafter, FSM CODE_SYNTHESIS):
       allocates thinking_budget = 1024 and max_tokens = 2048.
  2. Physical Stop Sequences:
     - Enforces hard stop sequences for tool calls, patch replacements, and structured JSON.
     - Limits sequences according to provider constraints (OpenAI max 4, Anthropic max 10, Gemini max 5).
  3. Stream Truncation:
     - Intercepts and truncates output streams at the earliest stop sequence, eliminating trailing
       conversational noise and quantifying exact tokens saved.
  4. Multi-Provider Payload Formatting:
     - Assembles compliant configuration payloads for Anthropic, OpenAI, and Google Gemini.

Usage:
  python3 tools/reasoning/dynamic_budget_engine.py --task-type mechanical --json
  python3 tools/reasoning/dynamic_budget_engine.py --fsm-stage AUTOPSY_HEAL --provider anthropic --json
  python3 tools/reasoning/dynamic_budget_engine.py --truncate-stream '</tool_call>\\nI have finished the test.' --stop-seq '</tool_call>'
  python3 tools/reasoning/dynamic_budget_engine.py --demo
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from tools.core.token_estimator import count_tokens
except ImportError:
    def count_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / 3.85))


class DynamicBudgetEngine:
    """
    Tier 9 Dynamic Budget & Hard Stop-Sequences Engine.
    Controls thinking budget, max tokens, and hard physical boundaries.
    """

    BUDGET_PROFILES: Dict[str, Dict[str, int]] = {
        "mechanical": {
            "thinking_budget": 0,
            "max_tokens": 256,
        },
        "synthesis": {
            "thinking_budget": 1024,
            "max_tokens": 2048,
        },
        "rca": {
            "thinking_budget": 2048,
            "max_tokens": 4096,
        },
    }

    FSM_STAGE_MAP: Dict[str, str] = {
        "DISCOVERY": "mechanical",
        "HEADLESS_EXEC": "mechanical",
        "ACCEPTANCE_DOD": "mechanical",
        "CODE_SYNTHESIS": "synthesis",
        "AUTOPSY_HEAL": "rca",
    }

    MECHANICAL_ACTIONS = {
        "read_file", "format", "re_run_test", "git_status", "run_cmd", "lint",
        "grep_search", "find_by_name", "read_slice", "ast_slice", "verify_compliance",
        "check_env", "distill_log", "status", "list_dir",
    }

    RCA_ACTIONS = {
        "autopsy_heal", "root_cause_analysis", "rca", "failure_analyst",
        "architecture_decision", "triage", "heal", "failure_triage", "deep_diagnosis",
    }

    SYNTHESIS_ACTIONS = {
        "pom_crafter", "generate_code", "code_synthesis", "synthesize",
        "codeact_script", "write_patch", "refactor_clean",
    }

    STOP_SEQUENCES: Dict[str, List[str]] = {
        "tool_call": ["</tool_call>", "</tool_code>", "```\n\n", "```\n"],
        "patch": [">>>>>>> REPLACE", "=======\n", "\n<<<<<<< SEARCH"],
        "json": ["}\n```", "\n}\n", "}\n"],
        "general": ["</tool_call>", ">>>>>>> REPLACE", "```\n\n", "\n---\n"],
    }

    PROVIDER_STOP_LIMITS: Dict[str, int] = {
        "openai": 4,
        "anthropic": 10,
        "gemini": 5,
        "deepseek": 4,
        "local_openai": 4,
    }

    @classmethod
    def resolve_budget(
        cls,
        task_type: str = "mechanical",
        fsm_stage: Optional[str] = None,
        action_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dynamically calculates thinking_budget and max_tokens based on execution context.

        Precedence:
          1. fsm_stage (if provided)
          2. action_name (if provided)
          3. task_type (fallback)

        Returns:
            Dict containing:
              - task_type: Resolved task category ("mechanical", "synthesis", "rca")
              - thinking_budget: Assigned thinking/reasoning budget (0 for mechanical)
              - max_tokens: Hard ceiling for output generation
              - fsm_stage: Input FSM stage
              - action_name: Input action name
        """
        resolved_category = "mechanical"

        # 1. FSM Stage resolution
        if fsm_stage:
            stage_upper = fsm_stage.upper().strip()
            if stage_upper in cls.FSM_STAGE_MAP:
                resolved_category = cls.FSM_STAGE_MAP[stage_upper]
            elif "HEAL" in stage_upper or "AUTOPSY" in stage_upper:
                resolved_category = "rca"
            elif "SYNTHESIS" in stage_upper or "CODE" in stage_upper:
                resolved_category = "synthesis"
            else:
                resolved_category = "mechanical"

        # 2. Action name resolution
        elif action_name:
            action_norm = action_name.lower().strip()
            if action_norm in cls.RCA_ACTIONS:
                resolved_category = "rca"
            elif action_norm in cls.SYNTHESIS_ACTIONS:
                resolved_category = "synthesis"
            elif action_norm in cls.MECHANICAL_ACTIONS:
                resolved_category = "mechanical"
            elif any(k in action_norm for k in ("heal", "rca", "autopsy", "triage", "diagnose")):
                resolved_category = "rca"
            elif any(k in action_norm for k in ("gen", "synth", "patch", "craft")):
                resolved_category = "synthesis"
            else:
                resolved_category = "mechanical"

        # 3. Explicit task_type fallback
        else:
            tt_norm = task_type.lower().strip()
            if tt_norm in ("rca", "analytical", "diagnosis"):
                resolved_category = "rca"
            elif tt_norm in ("synthesis", "creative", "code"):
                resolved_category = "synthesis"
            else:
                resolved_category = "mechanical"

        profile = cls.BUDGET_PROFILES.get(resolved_category, cls.BUDGET_PROFILES["mechanical"])

        return {
            "task_type": resolved_category,
            "thinking_budget": profile["thinking_budget"],
            "max_tokens": profile["max_tokens"],
            "fsm_stage": fsm_stage,
            "action_name": action_name,
        }

    @classmethod
    def get_stop_sequences(
        cls,
        action_type: str = "tool_call",
        provider: str = "anthropic",
    ) -> List[str]:
        """
        Returns physical stop sequences customized for the action type and provider constraints.
        Enforces provider ceilings (OpenAI: max 4, Gemini: max 5, Anthropic: max 10).
        """
        action_norm = action_type.lower().strip()
        base_seqs = cls.STOP_SEQUENCES.get(action_norm, cls.STOP_SEQUENCES["general"])

        limit = cls.PROVIDER_STOP_LIMITS.get(provider.lower().strip(), 10)
        return base_seqs[:limit]

    @classmethod
    def truncate_stream(
        cls,
        text: str,
        stop_sequences: List[str],
    ) -> Tuple[str, bool, int]:
        """
        Intercepts and truncates stream or text at the earliest stop sequence,
        cutting conversational chatter and calculating saved tokens.

        Returns:
            Tuple of:
              - truncated_text: Output truncated immediately after the stop sequence
              - hit_stop_sequence: True if a stop sequence was encountered
              - tokens_saved: Number of conversational tokens pruned
        """
        if not text or not stop_sequences:
            return text or "", False, 0

        earliest_idx = -1
        matching_seq = ""

        for seq in stop_sequences:
            if not seq:
                continue
            idx = text.find(seq)
            if idx != -1:
                if earliest_idx == -1 or idx < earliest_idx:
                    earliest_idx = idx
                    matching_seq = seq

        if earliest_idx != -1:
            cut_point = earliest_idx + len(matching_seq)
            truncated_text = text[:cut_point]
            discarded_text = text[cut_point:]
            tokens_saved = count_tokens(discarded_text)
            return truncated_text, True, tokens_saved

        return text, False, 0

    @classmethod
    def detect_partial_stop_sequence(
        cls,
        accumulated_text: str,
        stop_sequences: List[str],
    ) -> Tuple[str, bool]:
        """Truncates streamed accumulated text immediately upon hitting any stop sequence."""
        trimmed, hit, _saved = cls.truncate_stream(accumulated_text, stop_sequences)
        return trimmed, hit is True

    @classmethod
    def format_provider_payload(
        cls,
        budget_config: Dict[str, Any],
        provider: str = "anthropic",
    ) -> Dict[str, Any]:
        """
        Formats provider-native API payloads incorporating dynamic thinking budget,
        max token limits, and physical stop sequences.
        """
        provider_norm = provider.lower().strip()
        max_tokens = budget_config.get("max_tokens", 256)
        thinking_budget = budget_config.get("thinking_budget", 0)

        # Stop sequences resolution
        custom_stops = budget_config.get("stop_sequences")
        if custom_stops:
            stop_seqs = custom_stops
        else:
            stop_seqs = cls.get_stop_sequences("tool_call", provider=provider_norm)

        if provider_norm == "anthropic":
            payload: Dict[str, Any] = {
                "max_tokens": max_tokens,
                "stop_sequences": stop_seqs[:10],
            }
            if thinking_budget > 0:
                payload["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_budget,
                }
            else:
                payload["thinking"] = {
                    "type": "disabled",
                }
            return payload

        if provider_norm == "openai":
            if thinking_budget >= 2048:
                reasoning_effort = "high"
            elif thinking_budget > 0:
                reasoning_effort = "medium"
            else:
                reasoning_effort = "low"

            return {
                "max_completion_tokens": max_tokens,
                "stop": stop_seqs[:4],
                "reasoning_effort": reasoning_effort,
            }

        if provider_norm == "gemini":
            return {
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "stopSequences": stop_seqs[:5],
                    "thinkingConfig": {
                        "thinkingBudget": thinking_budget,
                    },
                }
            }

        if provider_norm == "deepseek":
            thinking_mode = "enabled" if thinking_budget else "disabled"
            return {
                "max_tokens": max_tokens,
                "stop": stop_seqs[:4],
                "thinking": {"type": thinking_mode},
            }

        if provider_norm == "local_openai":
            local_payload: Dict[str, Any] = {
                "max_tokens": max_tokens,
                "stop": stop_seqs[:4],
                "options": {"num_predict": max_tokens},
            }
            if thinking_budget and budget_config.get("supports_thinking") is not False:
                local_payload["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
            return local_payload

        return {
            "max_tokens": max_tokens,
            "thinking_budget": thinking_budget,
            "stop_sequences": stop_seqs,
        }

    @classmethod
    def run_benchmark_demo(cls) -> Dict[str, Any]:
        """
        Executes a comprehensive demonstration of dynamic budgeting and stream truncation.
        """
        # 1. Budget resolutions across phases
        mech_budget = cls.resolve_budget(fsm_stage="DISCOVERY")
        synth_budget = cls.resolve_budget(fsm_stage="CODE_SYNTHESIS")
        rca_budget = cls.resolve_budget(fsm_stage="AUTOPSY_HEAL")

        # 2. Multi-provider payloads
        anthropic_payload = cls.format_provider_payload(mech_budget, provider="anthropic")
        openai_payload = cls.format_provider_payload(mech_budget, provider="openai")
        gemini_payload = cls.format_provider_payload(rca_budget, provider="gemini")

        # 3. Stream chatter truncation demo
        sample_output_with_chatter = (
            "<tool_call>\n"
            '{"name": "read_file", "path": "AGENTS.md"}\n'
            "</tool_call>\n"
            "I have called the tool to read AGENTS.md. "
            "Now I will wait for the output and then proceed with the analysis. "
            "Please let me know if you would like me to inspect any other files as well!"
        )

        stops = cls.get_stop_sequences("tool_call", provider="anthropic")
        truncated, hit, tokens_saved = cls.truncate_stream(sample_output_with_chatter, stops)

        return {
            "budget_profiles": {
                "mechanical_discovery": mech_budget,
                "code_synthesis": synth_budget,
                "autopsy_heal_rca": rca_budget,
            },
            "provider_payloads": {
                "anthropic_mechanical": anthropic_payload,
                "openai_mechanical": openai_payload,
                "gemini_rca": gemini_payload,
            },
            "stream_truncation_demo": {
                "original_text_tokens": count_tokens(sample_output_with_chatter),
                "truncated_text_tokens": count_tokens(truncated),
                "tokens_saved": tokens_saved,
                "hit_stop_sequence": hit,
                "truncated_output": truncated,
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tier 9 Hard Stop-Sequences & Dynamic Thinking Budget Engine")
    parser.add_argument("--task-type", type=str, default="mechanical", help="Task type (mechanical, rca, synthesis)")
    parser.add_argument("--action", type=str, help="Specific tool action name (e.g. read_file, autopsy_heal)")
    parser.add_argument("--fsm-stage", type=str, help="FSM Stage (DISCOVERY, CODE_SYNTHESIS, HEADLESS_EXEC, AUTOPSY_HEAL, ACCEPTANCE_DOD)")
    parser.add_argument("--provider", type=str, default="anthropic", help="Target LLM provider (anthropic, openai, gemini)")
    parser.add_argument("--action-type", type=str, default="tool_call", help="Action type for stop sequences (tool_call, patch, json)")
    parser.add_argument("--truncate-stream", type=str, help="Raw LLM completion string to truncate at stop sequence")
    parser.add_argument("--stop-seq", type=str, action="append", help="Custom stop sequence to enforce (can specify multiple)")
    parser.add_argument("--demo", action="store_true", help="Run comprehensive demo of dynamic budgets and stream truncation")
    parser.add_argument("--json", action="store_true", help="Format output as JSON")

    args = parser.parse_args()

    if args.demo:
        demo_res = DynamicBudgetEngine.run_benchmark_demo()
        if args.json:
            print(json.dumps(demo_res, indent=2))
        else:
            print("======================================================================")
            print("   TIER 9 DYNAMIC THINKING BUDGET & HARD STOP-SEQUENCES DEMO         ")
            print("======================================================================")
            print("  [1] Mechanical Step (DISCOVERY):")
            print(f"      thinking_budget = {demo_res['budget_profiles']['mechanical_discovery']['thinking_budget']}")
            print(f"      max_tokens      = {demo_res['budget_profiles']['mechanical_discovery']['max_tokens']}")
            print("  [2] Analytical Step (AUTOPSY_HEAL RCA):")
            print(f"      thinking_budget = {demo_res['budget_profiles']['autopsy_heal_rca']['thinking_budget']}")
            print(f"      max_tokens      = {demo_res['budget_profiles']['autopsy_heal_rca']['max_tokens']}")
            print("  [3] Conversational Chatter Elimination:")
            print(f"      Original Tokens : {demo_res['stream_truncation_demo']['original_text_tokens']}")
            print(f"      Pruned Tokens   : {demo_res['stream_truncation_demo']['tokens_saved']}")
            print(f"      Truncated Tokens: {demo_res['stream_truncation_demo']['truncated_text_tokens']}")
            print("  Distilled Output:")
            print(demo_res["stream_truncation_demo"]["truncated_output"].strip())
            print("======================================================================")
        sys.exit(0)

    # Stream truncation mode
    if args.truncate_stream:
        stop_seqs = args.stop_seq if args.stop_seq else DynamicBudgetEngine.get_stop_sequences(args.action_type, args.provider)
        truncated, hit, saved = DynamicBudgetEngine.truncate_stream(args.truncate_stream, stop_seqs)
        out = {
            "truncated_text": truncated,
            "hit_stop_sequence": hit,
            "tokens_saved": saved,
            "stop_sequences_evaluated": stop_seqs,
        }
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            sys.stdout.write(truncated)
            if not truncated.endswith("\n"):
                sys.stdout.write("\n")
        sys.exit(0)

    # Budget resolution mode
    budget = DynamicBudgetEngine.resolve_budget(
        task_type=args.task_type,
        fsm_stage=args.fsm_stage,
        action_name=args.action,
    )
    payload = DynamicBudgetEngine.format_provider_payload(budget, provider=args.provider)

    res = {
        "budget": budget,
        "provider": args.provider,
        "provider_payload": payload,
    }

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"Task Category  : {budget['task_type']}")
        print(f"Thinking Budget: {budget['thinking_budget']}")
        print(f"Max Tokens     : {budget['max_tokens']}")
        print(f"Provider       : {args.provider}")
        print("Payload Structure:")
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
