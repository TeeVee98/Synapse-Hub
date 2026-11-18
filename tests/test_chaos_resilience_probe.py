#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT
# -*- coding: utf-8 -*-

"""
Unit tests for tools/chaos_resilience_probe.py
Verifies Chaos Engineering Principles, Safe Abort Kill-Switch, and ISO 25010 Reliability calculations.
"""

import unittest
from tools.perf.chaos_resilience_probe import ChaosResilienceEngine


class TestChaosResilienceProbe(unittest.TestCase):
    def setUp(self):
        self.engine = ChaosResilienceEngine(
            service_name="PaymentService",
            blast_radius="payment-gateway-pod-1",
            max_error_rate_pct=10.0,
            target_rto_sec=20.0,
            target_rpo_sec=3.0,
            min_availability_pct=70.0,
        )

    def test_mtbf_and_mttr_calculation(self):
        """Validates MTBF and MTTR mathematical formulas."""
        uptime = 3600.0  # 1 hour
        downtime = 60.0  # 1 min
        failures = 2

        mtbf = self.engine.calculate_mtbf(uptime, failures)
        mttr = self.engine.calculate_mttr(downtime, failures)

        self.assertEqual(mtbf, 1800.0)
        self.assertEqual(mttr, 30.0)

    def test_zero_failure_metrics(self):
        """Zero failures should produce 0 MTTR and total uptime MTBF."""
        mtbf = self.engine.calculate_mtbf(100.0, 0)
        mttr = self.engine.calculate_mttr(0.0, 0)
        self.assertEqual(mtbf, 100.0)
        self.assertEqual(mttr, 0.0)

    def test_reliability_evaluation_pass(self):
        """Validates SLA pass when RTO, RPO, and availability meet thresholds."""
        incidents = [
            {"incident_id": "INC-1", "start_sec": 10.0, "end_sec": 18.0, "fault_type": "latency", "recovered_gracefully": True}
        ]
        metrics = self.engine.evaluate_reliability(
            total_runtime_sec=100.0,
            incidents=incidents,
            data_loss_window_sec=1.0,
        )

        self.assertTrue(metrics["rto_passed"])
        self.assertTrue(metrics["rpo_passed"])
        self.assertEqual(metrics["overall_status"], "PASSED")
        self.assertEqual(metrics["max_recovery_sec"], 8.0)

    def test_reliability_evaluation_fail_rto(self):
        """Validates SLA failure when recovery duration breaches target RTO."""
        incidents = [
            {"incident_id": "INC-2", "start_sec": 5.0, "end_sec": 45.0, "fault_type": "disk_full", "recovered_gracefully": True}
        ]
        metrics = self.engine.evaluate_reliability(
            total_runtime_sec=100.0,
            incidents=incidents,
            data_loss_window_sec=1.0,
        )

        self.assertFalse(metrics["rto_passed"])
        self.assertEqual(metrics["overall_status"], "FAILED")
        self.assertEqual(metrics["max_recovery_sec"], 40.0)

    def test_simulate_chaos_scenarios(self):
        """Verifies simulation across all supported chaos scenarios."""
        scenarios = ["gateway_outage_circuit_breaker", "latency_injection", "container_disruption", "disk_pressure"]
        for sc in scenarios:
            result = self.engine.simulate_chaos_scenario(scenario_type=sc, probes_count=15)
            self.assertEqual(result["scenario"], sc)
            self.assertIn("reliability_metrics", result)
            self.assertIn("event_timeline", result)
            self.assertTrue(len(result["event_timeline"]) > 0)

            # Markdown report generation
            md = self.engine.render_markdown_report(result)
            self.assertIn("# Chaos Engineering & ISO/IEC 25010 Reliability Report", md)
            self.assertIn(sc, md)


if __name__ == "__main__":
    unittest.main()
