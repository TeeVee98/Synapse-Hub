# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
End-to-End Integration Suite for 5 Deep Autonomous Reasoning Engines:
  1. Unconstrained-to-Constrained Decoding (tools/reasoning/constrained_decoding.py)
  2. Prover-Verifier Zero-Sum Debate Games (tools/reasoning/prover_verifier_games.py)
  3. Semantic Entropy & Epistemic Search (tools/reasoning/semantic_entropy.py)
  4. Information-Theoretic Entropy Pruning (tools/reasoning/entropy_pruning.py)
  5. Associative Graph Memory & Sleep Consolidation (tools/reasoning/associative_memory.py)
"""

import os
import sys
import tempfile
import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
sys.path.insert(0, TOOLS_DIR)

from reasoning.constrained_decoding import ConstrainedDecoder
from reasoning.prover_verifier_games import ProverVerifierGame
from reasoning.semantic_entropy import SemanticEntropyEngine
from reasoning.entropy_pruning import EntropyPruner
from reasoning.associative_memory import AssociativeMemory


def test_e2e_full_5_engine_pipeline():
    """Validates the complete 5-engine reasoning and memory pipeline end-to-end."""

    # -------------------------------------------------------------
    # Stage 1: Unconstrained Thinking -> FSM Grammar Projection (R1)
    # -------------------------------------------------------------
    raw_thought = """
    <thought>
    I should structure the order checkout logic cleanly.
    {
      action: 'process_payment',
      amount_usd: 150.50,
      idempotency_key: 'PAY_991823', // required for duplicate prevention
      retry_policy: { max_retries: 3, backoff_ms: 500, },
    }
    </thought>
    """
    decoder = ConstrainedDecoder()
    projected_payload = decoder.project_json(raw_thought)
    assert isinstance(projected_payload, dict)
    assert projected_payload["action"] == "process_payment"
    assert projected_payload["idempotency_key"] == "PAY_991823"
    assert projected_payload["retry_policy"]["max_retries"] == 3

    # -------------------------------------------------------------
    # Stage 2: Prover-Verifier Zero-Sum Debate Game (R2)
    # -------------------------------------------------------------
    game = ProverVerifierGame()
    debate_proposal = "Enforce idempotent transaction token PAY_991823 with atomic DB lock and exponential backoff retry"
    debate_res = game.run_debate(proposal=debate_proposal, rounds=2)
    assert debate_res["rounds_completed"] == 2
    assert debate_res["status"] in ("ACCEPTED", "REFUTED")
    assert debate_res["winner"] in ("prover", "verifier")
    assert "nash_equilibrium_score" in debate_res

    # -------------------------------------------------------------
    # Stage 3: Semantic Entropy & Epistemic Uncertainty (R3)
    # -------------------------------------------------------------
    entropy_engine = SemanticEntropyEngine()
    # High-agreement hypotheses (Low entropy -> Write permitted)
    low_ent_hypotheses = [
        "Payment token PAY_991823 is unique and valid.",
        "Payment token PAY_991823 is verified unique.",
        "Payment token PAY_991823 has unique constraint in DB."
    ]
    low_ent_eval = entropy_engine.evaluate_hypotheses(low_ent_hypotheses, threshold=0.60)
    assert low_ent_eval["uncertainty_status"] == "CONFIDENT_LOW_ENTROPY"
    assert low_ent_eval["code_write_permission"] is True
    assert low_ent_eval["epistemic_search_required"] is False

    # High-entropy hypotheses (High uncertainty -> Write locked)
    high_ent_hypotheses = [
        "Payment service is written in Go.",
        "Payment service is an external Stripe webhook.",
        "Payment service uses local SQLite database.",
        "Payment service is simulated via mocked in-memory dictionary."
    ]
    high_ent_eval = entropy_engine.evaluate_hypotheses(high_ent_hypotheses, threshold=0.40)
    assert high_ent_eval["uncertainty_status"] == "HIGH_ENTROPY_CONFABULATION_RISK"
    assert high_ent_eval["code_write_permission"] is False
    assert high_ent_eval["epistemic_search_required"] is True

    # -------------------------------------------------------------
    # Stage 4: Information-Theoretic Entropy Pruning (R4)
    # -------------------------------------------------------------
    pruner = EntropyPruner()
    source_context = """
    # This is a very verbose and repetitive comment explaining checkout
    # Another unnecessary comment explaining basic variables
    def execute_payment(order_id: str, amount: float) -> bool:
        # Note: check if order is valid
        if not order_id:
            raise ValueError("Invalid order ID")
        # Proceed with transaction
        is_success = True
        assert is_success is True
        return is_success
    """
    pruned_text, stats = pruner.compress(source_context, target_ratio=0.70)
    assert stats["status"] in ("ok", "PASS")
    assert "def execute_payment" in pruned_text
    assert "assert is_success is True" in pruned_text

    # -------------------------------------------------------------
    # Stage 5: Associative Graph Memory & Sleep Consolidation (R5)
    # -------------------------------------------------------------
    with tempfile.NamedTemporaryFile("w", suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        mem = AssociativeMemory(db_path=db_path)
        # Record nodes and associations
        mem.record_node("CHECKOUT_SERVICE", "MODULE", attributes={"desc": "Service module"})
        mem.record_node("DEFECT_DOUBLE_CLICK", "DEFECT", attributes={"desc": "Double click race bug"})
        mem.record_association("CHECKOUT_SERVICE", "DEFECT_DOUBLE_CLICK", "EXHIBITED_BUG", weight=1.0)

        # Verify query
        assocs = mem.query_associations("CHECKOUT_SERVICE")
        assert len(assocs) == 1
        assert assocs[0]["target_id"] == "DEFECT_DOUBLE_CLICK"

        # Apply continuous temporal decay with future timestamp
        future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=14)
        decayed_count = mem.apply_time_decay(half_life_days=7.0, current_time=future_time)
        assert decayed_count >= 1

        decayed_assocs = mem.query_associations("CHECKOUT_SERVICE")
        assert decayed_assocs[0]["weight"] < 0.35

        # Perform sleep consolidation
        cons_res = mem.sleep_consolidate(prune_threshold=0.10, current_time=future_time)
        assert "pruned_count" in cons_res
        assert "consolidated_principles" in cons_res

    finally:
        mem.close()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass
