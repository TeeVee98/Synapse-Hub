#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
Multi-Trial Episodic Reflexion Loop for Autonomous Healing (Noah Shinn / Reflexion Pattern)
------------------------------------------------------------------------------------------
Replaces single-shot heuristic locator healing with an iterative, multi-trial reflection
loop (K=3). When a test fails:
  1. Evaluator extracts failure stacktrace & symptom.
  2. AOM Context Analyzer extracts and prunes a compact Accessibility Object Model
     subtree (< 500 tokens) surrounding the failing locator.
  3. Reflexion Generator creates a structured 2-line verbal diagnosis and prompt semantic
     reasoning conditioned on live accessibility roles and states.
  4. Memory Buffer accumulates trials across attempts.
  5. Actor synthesizes adaptive Clean POM locator patches (getByRole, getByLabel, getByTestId).
  6. Upon pass -> records to positive cache (healing_cache & lessons_learned).
  7. Upon exhaustion of K=3 -> records to negative cache (failed_fixes) to block blind retries.

Reference:
  - Noah Shinn et al. (Reflexion: Language Agents with Verbal Reinforcement Learning).
  - Synapse-Hub Subsystem 2: Section 6.3 of agent_skill_training_analysis.md.
"""

import os
import sys
import re
import json
import argparse
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple, Dict, Any

# Enforce UTF-8 stdout encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    import cache_resolver
except ImportError:
    from tools import cache_resolver


@dataclass
class ReflexionTrial:
    trial_number: int
    patch_attempt: str
    error_feedback: str
    verbal_reflection: str
    is_passing: bool


def prune_aom_tree(aom_data: Any, target_selector: str = "", max_chars: int = 1800) -> Dict[str, Any]:
    """
    Prunes an Accessibility Object Model (AOM) tree down to a compact, semantically dense
    subtree surrounding the target element (< 500 tokens / ~1800 characters).
    Preserves role, name, disabled, expanded, selected, checked, and testId.
    """
    if isinstance(aom_data, str):
        try:
            aom_data = json.loads(aom_data)
        except Exception:
            # Fallback: clean string representation capped to budget
            clean_str = aom_data.strip()[:max_chars]
            return {"type": "raw_aom_text", "content": clean_str}

    sel_tokens = [
        tok.lower() for tok in re.split(r'[^a-zA-Z0-9_]', target_selector.lower())
        if len(tok) >= 3 and tok.lower() not in {"button", "input", "div", "span", "select", "table", "form", "page", "locator"}
    ]

    def _clean_node(node: Any, depth: int = 0) -> Optional[Dict[str, Any]]:
        if depth > 4 or not isinstance(node, dict):
            return None

        # Extract only salient accessibility properties
        cleaned: Dict[str, Any] = {}
        for key in ["role", "name", "aria-label", "label", "text", "testId", "data-testid", "id"]:
            if key in node and node[key]:
                cleaned[key] = str(node[key])[:80]

        for state_key in ["disabled", "expanded", "selected", "checked", "focused", "modal"]:
            if state_key in node:
                cleaned[state_key] = bool(node[state_key])

        # Recurse children
        children = node.get("children") or node.get("nodes") or []
        if isinstance(children, list) and depth < 4:
            clean_children = []
            for child in children:
                c_clean = _clean_node(child, depth + 1)
                if c_clean:
                    clean_children.append(c_clean)
                if len(clean_children) >= 12:
                    break
            if clean_children:
                cleaned["children"] = clean_children

        return cleaned if cleaned else None

    if isinstance(aom_data, list):
        pruned_nodes = []
        for n in aom_data:
            cleaned = _clean_node(n, depth=0)
            if cleaned:
                pruned_nodes.append(cleaned)
            if len(pruned_nodes) >= 8:
                break
        result: Dict[str, Any] = {"aom_nodes": pruned_nodes}
    elif isinstance(aom_data, dict):
        result = _clean_node(aom_data, depth=0) or {}
    else:
        result = {"aom_data": str(aom_data)[:max_chars]}

    # Ensure token budget: truncate children safely without dropping the whole tree
    serialized = json.dumps(result, ensure_ascii=False)
    if len(serialized) > max_chars:
        if "aom_nodes" in result and isinstance(result["aom_nodes"], list):
            result["aom_nodes"] = result["aom_nodes"][:3]
        elif "children" in result and isinstance(result["children"], list):
            result["children"] = result["children"][:2]
            for c in result["children"]:
                if isinstance(c, dict) and "children" in c and isinstance(c["children"], list):
                    c["children"] = c["children"][:3]
        result["notice"] = "Pruned to < 500 token budget"
        serialized = json.dumps(result, ensure_ascii=False)
        if len(serialized) > max_chars and "children" in result and isinstance(result["children"], list):
            result["children"] = result["children"][:1]
            for c in result["children"]:
                if isinstance(c, dict) and "children" in c and isinstance(c["children"], list):
                    c["children"] = c["children"][:2]

    return result


def analyze_aom_semantic_discrepancy(failing_selector: str, aom_data: Any) -> Dict[str, Any]:
    """
    Analyzes live accessibility state to diagnose why failing_selector broke and synthesizes
    robust Clean POM locator recommendations (getByRole, getByLabel, getByTestId).
    """
    selector_clean = failing_selector.strip()
    sel_lower = selector_clean.lower()

    # Flatten nodes for fast inspection
    nodes: List[Dict[str, Any]] = []

    def _collect(n: Any):
        if isinstance(n, dict):
            nodes.append(n)
            for child in n.get("children", []):
                _collect(child)
        elif isinstance(n, list):
            for item in n:
                _collect(item)

    if isinstance(aom_data, dict) and "aom_nodes" in aom_data:
        _collect(aom_data["aom_nodes"])
    else:
        _collect(aom_data)

    # 1. Look for matching interactive nodes by priority (exact -> specific token -> fallback)
    candidate_node = None
    GENERIC_TAGS = {
        "button", "input", "div", "span", "select", "table", "form", "page",
        "locator", "click", "fill", "getbyrole", "getbylabel", "getbytestid", "a", "tr", "td"
    }
    raw_tokens = [tok for tok in re.split(r'[^a-zA-Z0-9_]', sel_lower) if len(tok) >= 2]
    specific_tokens = [tok for tok in raw_tokens if tok not in GENERIC_TAGS and len(tok) >= 3]
    target_tokens = specific_tokens if specific_tokens else raw_tokens

    # Priority 1: Exact match on accessible name or testId
    for node in nodes:
        name = str(node.get("name", "")).lower()
        test_id = str(node.get("testId") or node.get("data-testid") or "").lower()
        if any(tok == name or tok == test_id for tok in target_tokens):
            candidate_node = node
            break

    # Priority 2: Substring match on specific non-tag tokens
    if not candidate_node and specific_tokens:
        for node in nodes:
            name = str(node.get("name", "")).lower()
            test_id = str(node.get("testId") or node.get("data-testid") or "").lower()
            if any(tok in name or tok in test_id for tok in specific_tokens):
                candidate_node = node
                break

    # Priority 3: Fallback match on any token
    if not candidate_node:
        for node in nodes:
            name = str(node.get("name", "")).lower()
            test_id = str(node.get("testId") or node.get("data-testid") or "").lower()
            if any(tok in name or tok in test_id for tok in target_tokens):
                candidate_node = node
                break

    if candidate_node:
        role = candidate_node.get("role", "button")
        name = candidate_node.get("name", "")
        test_id = candidate_node.get("testId") or candidate_node.get("data-testid")
        is_disabled = candidate_node.get("disabled", False)

        if is_disabled:
            cause = "TARGET_ELEMENT_DISABLED"
            detail = f"Element with accessible name '{name}' is currently disabled in live AOM."
            recommendation = "Wait for element to be enabled or assert isEnabled() before interaction."
        else:
            cause = "ACCESSIBLE_NAME_OR_ROLE_RESOLVED"
            detail = f"Resolved live AOM node: role='{role}', name='{name}'."
            recommendation = "Replace brittle CSS/XPath with Clean POM semantic locator."

        candidates = []
        if name:
            candidates.append(f"page.getByRole('{role}', {{ name: '{name}' }})")
        if test_id:
            candidates.append(f"page.getByTestId('{test_id}')")
        if name and role in ("textbox", "combobox", "searchbox"):
            candidates.append(f"page.getByLabel('{name}')")
        if not candidates:
            candidates.append(f"page.getByRole('{role}')")

        return {
            "discrepancy_cause": cause,
            "detail": detail,
            "target_node": candidate_node,
            "recommended_patch": candidates[0],
            "candidate_locators": candidates,
            "recommendation": recommendation
        }

    # Fallback when exact node is not matched in AOM
    # Guess role from selector
    inferred_role = "button"
    if any(k in sel_lower for k in ("input", "txt", "search", "field", "query")):
        inferred_role = "textbox"
    elif any(k in sel_lower for k in ("link", "nav", "a[", "href")):
        inferred_role = "link"
    elif any(k in sel_lower for k in ("select", "dropdown", "combo")):
        inferred_role = "combobox"

    inferred_name = target_tokens[0].capitalize() if target_tokens else "Target"
    fallback_patch = f"page.getByRole('{inferred_role}', {{ name: '{inferred_name}' }})"

    return {
        "discrepancy_cause": "SELECTOR_NOT_FOUND_IN_ACCESSIBILITY_TREE",
        "detail": f"Selector '{failing_selector}' does not match any current accessible nodes. Element may be unmounted or renamed.",
        "target_node": None,
        "recommended_patch": fallback_patch,
        "candidate_locators": [fallback_patch, f"page.locator('{failing_selector}')"],
        "recommendation": f"Verify element visibility and switch to semantic role: {fallback_patch}."
    }


def generate_semantic_reflexion(
    error_sig: str,
    failing_selector: str = "",
    aom_tree: Optional[Any] = None,
    patch_attempt: str = "",
    previous_error: str = ""
) -> Dict[str, Any]:
    """
    Generates a structured LLM-guided semantic reflexion payload:
    1. Prunes AOM tree to < 500 tokens.
    2. Runs semantic diagnosis.
    3. Produces a 2-line verbal reflection and formatted LLM reasoning prompt.
    """
    compact_aom = prune_aom_tree(aom_tree, target_selector=failing_selector) if aom_tree else {}
    diagnosis = analyze_aom_semantic_discrepancy(failing_selector, compact_aom) if (aom_tree and failing_selector) else None

    if diagnosis:
        rec_patch = diagnosis["recommended_patch"]
        cause = diagnosis["discrepancy_cause"]
        detail = diagnosis["detail"]
        verbal_reflection = (
            f"Reflection: Locator '{failing_selector}' failed with {error_sig[:60]}. Live AOM indicates: {detail}\n"
            f"Adjustment: {diagnosis['recommendation']} Use semantic locator: {rec_patch}."
        )
    else:
        # Fallback to standard heuristic reflection
        err_lower = (previous_error or error_sig).lower()
        if "staleelement" in err_lower or "stale" in err_lower:
            verbal_reflection = "Reflection: DOM node re-rendered asynchronously after API call.\nAdjustment: Must wait for loader/backdrop detachment before re-querying element."
            rec_patch = "page.waitForLoadState('networkidle')"
        elif "intercepted" in err_lower or "click" in err_lower:
            verbal_reflection = "Reflection: Click intercepted by fading overlay/spinner animation.\nAdjustment: Use smart wait for overlay detachment or bypass via safe JS click."
            rec_patch = f"page.locator('{failing_selector}').click({{ force: true }})"
        elif "hydration" in err_lower or "did not match" in err_lower:
            verbal_reflection = "Reflection: React/Next.js hydration mismatch caused DOM element to re-render.\nAdjustment: Ensure DOM is interactive and wait for loadState('domcontentloaded') before query."
            rec_patch = "page.waitForLoadState('domcontentloaded')"
        elif "shadow" in err_lower or "shadowroot" in err_lower:
            verbal_reflection = "Reflection: Target element encapsulated inside closed Shadow DOM boundary.\nAdjustment: Pierce Shadow DOM via locator piercing syntax or evaluate via CDP."
            rec_patch = f"page.locator('{failing_selector}').locator(':scope')"
        elif "iframe" in err_lower or "frame" in err_lower:
            verbal_reflection = "Reflection: Target element resides inside cross-origin iframe container.\nAdjustment: Switch context to frameLocator('iframe#...') before clicking."
            rec_patch = f"page.frameLocator('iframe').locator('{failing_selector}')"
        elif any(auth_err in err_lower for auth_err in ("401", "403", "unauthorized", "forbidden", "token expired")):
            verbal_reflection = "Reflection: Session auth token or cookie expired mid-test.\nAdjustment: Refresh storageState or trigger silent token re-authentication via API fixture."
            rec_patch = "authManager.refreshStorageState()"
        elif "timeout" in err_lower or "nosuchelement" in err_lower:
            verbal_reflection = "Reflection: Static selector did not appear within timeout window.\nAdjustment: Fallback to Accessibility role/label or dynamic data-testid attribute."
            rec_patch = "page.getByRole('button')"
        elif "assert" in err_lower:
            verbal_reflection = "Reflection: Assertion condition violated actual state.\nAdjustment: Check if state change was asynchronous or if expected data was corrupted."
            rec_patch = "expect(element).toBeVisible()"
        else:
            verbal_reflection = f"Reflection: Patch attempt failed with '{error_sig[:80]}'.\nAdjustment: Re-examine live DOM tree and avoid static sleeps."
            rec_patch = f"page.locator('{failing_selector}')"

        cause = "HEURISTIC_ERROR_SIGNATURE"
        detail = "Standard error pattern match."

    # Synthesize LLM semantic reasoning prompt
    aom_json_str = json.dumps(compact_aom, indent=2, ensure_ascii=False) if compact_aom else "None provided."
    prompt = f"""### Autonomous QA Self-Healing Reflexion Prompt (Noah Shinn Pattern)
You are an expert QA Automation Engineer specialized in Clean POM and Playwright self-healing.

#### 1. Failure Symptom:
- Failing Selector : {failing_selector or 'N/A'}
- Error Signature  : {error_sig}
- Previous Patch   : {patch_attempt or 'Initial failure'}
- Previous Error   : {previous_error or 'None'}

#### 2. Compact Accessibility Object Model (AOM) Subtree (< 500 tokens):
```json
{aom_json_str}
```

#### 3. Semantic Diagnosis:
- Root Cause       : {cause}
- Structural Detail: {detail}

#### 4. Mandatory Instructions:
1. Synthesize a single Clean POM locator adhering strictly to Flat Architecture (zero raw XPaths/brittle CSS).
2. Prioritize user-facing accessibility semantics:
   - Priority 1: page.getByRole('role', {{ name: 'accessible_name' }})
   - Priority 2: page.getByTestId('test-id')
   - Priority 3: page.getByLabel('label_text')
3. Proposed Patch: {rec_patch}
"""

    return {
        "verbal_reflection": verbal_reflection,
        "recommended_patch": rec_patch,
        "compact_aom": compact_aom,
        "semantic_diagnosis": diagnosis,
        "discrepancy_cause": cause,
        "prompt": prompt
    }


class ClosedLoopHealer:
    """Orchestrates multi-trial reflection loops for self-healing test automation."""

    def __init__(self, max_trials: int = 3):
        self.max_trials = max_trials
        self.memory_buffer: List[ReflexionTrial] = []

    def generate_reflection(
        self,
        error_sig: str,
        patch_attempt: str,
        previous_error: str,
        aom_tree: Optional[Any] = None,
        failing_selector: str = ""
    ) -> str:
        """
        Synthesizes a structured 2-line verbal reflection explaining why the previous attempt failed
        and prescribing the strategic adjustment for the next attempt.
        When AOM context is available, grounds reflection in live semantic accessibility nodes.
        """
        res = generate_semantic_reflexion(
            error_sig=error_sig,
            failing_selector=failing_selector,
            aom_tree=aom_tree,
            patch_attempt=patch_attempt,
            previous_error=previous_error
        )
        return res["verbal_reflection"]

    def execute_healing_loop(
        self,
        failing_test: str,
        initial_error: str,
        patch_synthesizer: Callable[[str, str, List[ReflexionTrial]], str],
        verifier: Callable[[str, str], Tuple[bool, str]],
        page_context: str = "GLOBAL",
        aom_tree: Optional[Any] = None,
        failing_selector: str = ""
    ) -> Tuple[bool, Optional[str], List[ReflexionTrial]]:
        """
        Executes up to max_trials attempts.
        Returns (is_success, winning_patch, trial_history).
        """
        self.memory_buffer.clear()
        current_error = initial_error

        print(f"\n🔄 [REFLEXION LOOP] Starting Multi-Trial Self-Healing (Max K={self.max_trials}) for '{failing_test}'...")

        for t in range(1, self.max_trials + 1):
            prev_attempt = self.memory_buffer[-1].patch_attempt if self.memory_buffer else ""
            reflection = self.generate_reflection(
                initial_error,
                prev_attempt,
                current_error,
                aom_tree=aom_tree,
                failing_selector=failing_selector
            )

            print(f"\n  --- Trial {t}/{self.max_trials} ---")
            print(f"  🧠 Verbal Reflection:\n{reflection}")

            # Synthesize next patch conditioned on reflection memory
            try:
                if patch_synthesizer:
                    candidate_patch = patch_synthesizer(failing_test, reflection, self.memory_buffer)
                else:
                    sem = generate_semantic_reflexion(initial_error, failing_selector, aom_tree=aom_tree)
                    candidate_patch = sem["recommended_patch"]
            except Exception as e:
                candidate_patch = f"// Error in patch_synthesizer: {e}"

            print(f"  🔧 Candidate Patch  : {candidate_patch[:100]}...")

            # Verify patch in headless execution safely
            try:
                is_pass, new_error = verifier(failing_test, candidate_patch)
            except Exception as err:
                is_pass, new_error = False, f"Verifier execution error: {err}"

            trial = ReflexionTrial(
                trial_number=t,
                patch_attempt=candidate_patch,
                error_feedback=new_error if not is_pass else "PASS",
                verbal_reflection=reflection,
                is_passing=is_pass
            )
            self.memory_buffer.append(trial)

            if is_pass:
                print(f"  ✅ [TRIAL {t} SUCCESS] Patch verified passing!")
                self._record_positive_memory(page_context, initial_error, candidate_patch, reflection)
                return True, candidate_patch, self.memory_buffer
            else:
                print(f"  ❌ [TRIAL {t} FAILED] Error: {new_error[:100]}")
                current_error = new_error

        print(f"\n⚠️  [REFLEXION EXHAUSTED] Failed after {self.max_trials} trials. Persisting to negative memory blacklist.")
        self._record_negative_memory(initial_error, self.memory_buffer[-1].patch_attempt, f"Failed across {self.max_trials} multi-trial attempts")
        return False, None, self.memory_buffer

    def _record_positive_memory(self, page_context: str, error_sig: str, patch: str, reflection: str):
        try:
            cache_resolver.record_lesson(
                page_context=page_context,
                error_signature=error_sig,
                root_cause=reflection,
                failed_attempt="Initial failing code",
                successful_fix=patch,
                lesson_summary=reflection
            )
        except Exception as e:
            sys.stderr.write(f"Notice: Failed to record positive memory: {e}\n")

    def _record_negative_memory(self, error_sig: str, failed_patch: str, reason: str):
        try:
            cache_resolver.record_failed_fix(
                error_signature=error_sig,
                patch=failed_patch,
                reason=reason,
                agent_role="failure-analyst"
            )
        except Exception as e:
            sys.stderr.write(f"Notice: Failed to record negative memory: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="Multi-Trial Episodic Reflexion Self-Healer with AOM Semantic Analysis")
    parser.add_argument("--test", default="SampleTest", help="Failing test identifier")
    parser.add_argument("--error", default="ElementClickInterceptedException", help="Initial error signature")
    parser.add_argument("--selector", default="", help="Failing selector (e.g. #login-btn)")
    parser.add_argument("--aom", default="", help="Inline AOM JSON string or file path containing AOM data")
    parser.add_argument("--max-trials", type=int, default=3, help="Max trials (default: 3)")
    parser.add_argument("--semantic-prompt", action="store_true", help="Output full synthesized LLM reasoning prompt")
    args = parser.parse_args()

    aom_data = None
    if args.aom:
        if os.path.isfile(args.aom):
            try:
                with open(args.aom, "r", encoding="utf-8") as f:
                    aom_data = json.load(f)
            except Exception as e:
                aom_data = {"error": f"Failed to read AOM file: {e}"}
        else:
            try:
                aom_data = json.loads(args.aom)
            except Exception:
                aom_data = args.aom

    semantic_res = generate_semantic_reflexion(
        error_sig=args.error,
        failing_selector=args.selector,
        aom_tree=aom_data
    )

    output = {
        "test": args.test,
        "error": args.error,
        "selector": args.selector,
        "max_trials": args.max_trials,
        "verbal_reflection": semantic_res["verbal_reflection"],
        "recommended_patch": semantic_res["recommended_patch"],
        "discrepancy_cause": semantic_res["discrepancy_cause"]
    }

    if args.semantic_prompt:
        output["semantic_prompt"] = semantic_res["prompt"]

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
