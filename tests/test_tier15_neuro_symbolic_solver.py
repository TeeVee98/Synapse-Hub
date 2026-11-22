#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
tests/test_tier15_neuro_symbolic_solver.py — Test Suite for Tier 15 Neuro-Symbolic Solver
----------------------------------------------------------------------------------------
Enforces 4-Scenario Testing: Positive, Negative, Boundary, and CLI invocation.
"""

import json
import subprocess
import sys
import unittest
from tools.reasoning.neuro_symbolic_solver import (
    DependencyCycleSolver,
    DPLLSatSolver,
    IntegerDifferenceLogicSolver,
    RBACConstraintSolver,
    run_benchmark,
)


class TestTier15NeuroSymbolicSolver(unittest.TestCase):
    """Test Suite for Tier 15 Neuro-Symbolic Constraint Offloading Engine."""

    # 1. Positive Scenario
    def test_positive_sat_and_cycle(self) -> None:
        # Satisfiable CNF: (A or B) and (-A or C)
        sat_cnf = [[1, 2], [-1, 3]]
        sat_sol = DPLLSatSolver.solve(sat_cnf)
        self.assertTrue(sat_sol.is_sat)
        self.assertIn(1, sat_sol.assignment)
        self.assertLess(sat_sol.duration_ms, 50.0)

        # Feasible IDL (Theory of Difference Logic for timing SLA): B - A <= 50, C - B <= 30
        idl_sol = IntegerDifferenceLogicSolver.solve([("B", "A", 50), ("C", "B", 30)])
        self.assertTrue(idl_sol.is_feasible)
        self.assertIn("A", idl_sol.assignment)
        self.assertIn("B", idl_sol.assignment)

        # Acyclic Dependency Graph: A -> B -> C
        acyclic_edges = [["A", "B"], ["B", "C"]]
        cycle_sol = DependencyCycleSolver.solve(acyclic_edges)
        self.assertFalse(cycle_sol.has_cycle)
        self.assertEqual(cycle_sol.topological_order, ["A", "B", "C"])

        # Compliant RBAC policy
        rbac_sol = RBACConstraintSolver.verify_policy(
            user_roles=["Tester"],
            role_permissions={"Tester": ["run_tests"]},
            separation_of_duty_rules=[("Developer", "Tester")],
        )
        self.assertTrue(rbac_sol.is_compliant)
        self.assertEqual(rbac_sol.effective_permissions, ["run_tests"])

    # 2. Negative Scenario
    def test_negative_unsat_and_cycle_detection(self) -> None:
        # Contradictory CNF (A) and (not A) -> UNSAT
        unsat_cnf = [[1], [-1]]
        unsat_sol = DPLLSatSolver.solve(unsat_cnf)
        self.assertFalse(unsat_sol.is_sat)

        # Infeasible IDL (Negative Cycle: B - A <= 10, A - B <= -20)
        idl_neg = IntegerDifferenceLogicSolver.solve([("B", "A", 10), ("A", "B", -20)])
        self.assertFalse(idl_neg.is_feasible)
        self.assertIsNotNone(idl_neg.negative_cycle)

        # Cyclic Graph: A -> B -> C -> A
        cyclic_edges = [["A", "B"], ["B", "C"], ["C", "A"]]
        cycle_sol = DependencyCycleSolver.solve(cyclic_edges)
        self.assertTrue(cycle_sol.has_cycle)
        self.assertGreater(len(cycle_sol.cycles_found), 0)
        self.assertGreater(len(cycle_sol.broken_edges), 0)

        # Conflicting RBAC policy (SoD Violation)
        rbac_violation = RBACConstraintSolver.verify_policy(
            user_roles=["Developer", "Tester"],
            role_permissions={"Developer": ["commit_code"], "Tester": ["run_tests"]},
            separation_of_duty_rules=[("Developer", "Tester")],
        )
        self.assertFalse(rbac_violation.is_compliant)
        self.assertEqual(len(rbac_violation.conflicts), 1)

    # 3. Boundary Scenario
    def test_boundary_empty_structures(self) -> None:
        # Empty SAT
        empty_sat = DPLLSatSolver.solve([])
        self.assertTrue(empty_sat.is_sat)
        self.assertEqual(empty_sat.variable_count, 0)

        # Empty IDL
        empty_idl = IntegerDifferenceLogicSolver.solve([])
        self.assertTrue(empty_idl.is_feasible)
        self.assertEqual(empty_idl.assignment, {})

        # Empty graph
        empty_graph = DependencyCycleSolver.solve([])
        self.assertFalse(empty_graph.has_cycle)
        self.assertEqual(empty_graph.topological_order, [])

        # Empty RBAC
        empty_rbac = RBACConstraintSolver.verify_policy([], {}, [])
        self.assertTrue(empty_rbac.is_compliant)
        self.assertEqual(empty_rbac.effective_permissions, [])

    # 4. CLI & Gate Scenario
    def test_cli_and_gate_execution(self) -> None:
        bench = run_benchmark()
        self.assertEqual(bench["status"], "PASS")

        # Subprocess CLI run: SAT problem
        proc = subprocess.run(
            [sys.executable, "tools/reasoning/neuro_symbolic_solver.py", "--problem", "sat", "--cnf", "[[1, 2], [-1, 3]]", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        self.assertTrue(data["is_sat"])

        # Subprocess Gate run
        gate_proc = subprocess.run(
            [sys.executable, "tools/reasoning/neuro_symbolic_solver.py", "--gate"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS]", gate_proc.stdout)


if __name__ == "__main__":
    unittest.main()
