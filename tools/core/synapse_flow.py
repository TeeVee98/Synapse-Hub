#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Thế Vị (@TeeVee98). All rights reserved.
# SPDX-License-Identifier: MIT
# Project: Synapse-Hub (https://github.com/TeeVee98/Synapse-Hub)

"""
SynapseFlow: Cyclic State Graph & Workflow Orchestrator
-------------------------------------------------------
A lightweight, zero-dependency, compiler-grade state graph runtime for multi-agent
orchestration and QA automation workflows.

Key Capabilities:
  1. Cyclic Graph Execution: Supports loops (e.g. Generation -> Test -> Heal -> Test)
     with configurable max_iterations and infinite-loop guards.
  2. Deterministic State Management: Immutable state transitions with incremental
     delta updates.
  3. Checkpoint Persistence & Time-Travel: Save and restore execution state at every
     step with SQLite WAL or in-memory storage, enabling replay and forking.
  4. Conditional Branching: Dynamic routing based on runtime state inspection.
  5. Gate Interceptors: Pre-node and post-node validation hooks (integrating with
     quality gates and fact-forcing checks).

Usage Example:
  >>> from tools.core.synapse_flow import StateGraph, START, END
  >>> workflow = StateGraph()
  >>> workflow.add_node("discover", discover_step)
  >>> workflow.add_node("heal", heal_step)
  >>> workflow.add_edge(START, "discover")
  >>> workflow.add_conditional_edge("discover", should_heal_or_end, {"heal": "heal", "end": END})
  >>> workflow.add_edge("heal", "discover")  # Cyclic loop
  >>> app = workflow.compile(checkpoint_db=":memory:")
  >>> result = app.invoke({"tests": ["test_login"]})
"""

import os
import json
import uuid
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, Callable, List, Optional, Union, Tuple

# Constants for Graph Boundaries
START = "__START__"
END = "__END__"


class FlowError(Exception):
    """Base exception for SynapseFlow runtime errors."""
    pass


class InfiniteLoopError(FlowError):
    """Raised when cyclic iterations exceed the maximum configured threshold."""
    pass


class NodeExecutionError(FlowError):
    """Raised when a graph node fails during execution."""
    def __init__(self, node_name: str, original_error: Exception):
        super().__init__(f"Error in node '{node_name}': {str(original_error)}")
        self.node_name = node_name
        self.original_error = original_error


class GateRejectionError(FlowError):
    """Raised when a pre-node or post-node gate rejects state progression."""
    pass


class Checkpointer:
    """Checkpointer persisting flow state snapshots using SQLite with WAL support."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or ":memory:"
        self._is_memory = (self.db_path == ":memory:")
        if not self._is_memory and self.db_path:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self._conn:
            if not self._is_memory:
                try:
                    self._conn.execute("PRAGMA journal_mode=WAL;")
                except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
                    pass
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS flow_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    flow_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    node_name TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
            """)
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_flow_step ON flow_checkpoints (flow_id, step_index);")

    def save(self, flow_id: str, step_index: int, node_name: str, state: Dict[str, Any]) -> str:
        checkpoint_id = f"chk_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        state_json = json.dumps(state, default=str)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO flow_checkpoints (checkpoint_id, flow_id, step_index, node_name, state_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (checkpoint_id, flow_id, step_index, node_name, state_json, now)
            )
        return checkpoint_id

    def load_latest(self, flow_id: str) -> Optional[Dict[str, Any]]:
        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM flow_checkpoints WHERE flow_id = ? ORDER BY step_index DESC LIMIT 1;",
            (flow_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "checkpoint_id": row["checkpoint_id"],
                "flow_id": row["flow_id"],
                "step_index": row["step_index"],
                "node_name": row["node_name"],
                "state": json.loads(row["state_json"]),
                "timestamp": row["timestamp"],
            }
        return None

    def load_by_id(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM flow_checkpoints WHERE checkpoint_id = ?;",
            (checkpoint_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "checkpoint_id": row["checkpoint_id"],
                "flow_id": row["flow_id"],
                "step_index": row["step_index"],
                "node_name": row["node_name"],
                "state": json.loads(row["state_json"]),
                "timestamp": row["timestamp"],
            }
        return None

    def list_checkpoints(self, flow_id: str) -> List[Dict[str, Any]]:
        self._conn.row_factory = sqlite3.Row
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM flow_checkpoints WHERE flow_id = ? ORDER BY step_index ASC;",
            (flow_id,)
        )
        rows = cursor.fetchall()
        return [
            {
                "checkpoint_id": r["checkpoint_id"],
                "step_index": r["step_index"],
                "node_name": r["node_name"],
                "timestamp": r["timestamp"]
            }
            for r in rows
        ]

    def close(self):
        """Closes the underlying database connection."""
        try:
            self._conn.close()
        except Exception:  # synapse-ignore: SWALLOWED_EXCEPTION
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class CompiledGraph:
    """An executable graph instance compiled from StateGraph specification."""

    def __init__(
        self,
        nodes: Dict[str, Callable[[Dict[str, Any]], Union[Dict[str, Any], None]]],
        edges: Dict[str, str],
        conditional_edges: Dict[str, Tuple[Callable[[Dict[str, Any]], str], Dict[str, str]]],
        entry_point: str,
        checkpointer: Optional[Checkpointer] = None,
        max_iterations: int = 50,
        pre_node_hooks: Optional[List[Callable[[str, Dict[str, Any]], bool]]] = None,
        post_node_hooks: Optional[List[Callable[[str, Dict[str, Any]], bool]]] = None,
    ):
        self.nodes = nodes
        self.edges = edges
        self.conditional_edges = conditional_edges
        self.entry_point = entry_point
        self.checkpointer = checkpointer or Checkpointer(":memory:")
        self.max_iterations = max_iterations
        self.pre_node_hooks = pre_node_hooks or []
        self.post_node_hooks = post_node_hooks or []

    def close(self):
        """Releases checkpointer connections."""
        if self.checkpointer:
            self.checkpointer.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def invoke(
        self,
        initial_state: Dict[str, Any],
        flow_id: Optional[str] = None,
        resume_from_checkpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the graph to completion starting from the entry point or resumed checkpoint.
        Returns the final state dictionary.
        """
        active_flow_id = flow_id or f"flow_{uuid.uuid4().hex[:10]}"
        state = dict(initial_state)
        step_index = 0

        # Support resumption from prior checkpoint
        if resume_from_checkpoint:
            checkpoint = self.checkpointer.load_by_id(resume_from_checkpoint)
            if not checkpoint:
                raise FlowError(f"Checkpoint not found: {resume_from_checkpoint}")
            state = checkpoint["state"]
            step_index = checkpoint["step_index"]
            completed_node = checkpoint["node_name"]

            # Advance to successor node so completed_node is not re-executed
            if completed_node == START:
                current_node = self.entry_point
            elif completed_node in self.conditional_edges:
                router_fn, routing_map = self.conditional_edges[completed_node]
                route_key = router_fn(state)
                current_node = routing_map.get(route_key, END)
            elif completed_node in self.edges:
                current_node = self.edges[completed_node]
            else:
                current_node = END

            # Save resumption snapshot
            self.checkpointer.save(active_flow_id, step_index, f"RESUME_AFTER_{completed_node}", state)
        else:
            current_node = self.entry_point
            self.checkpointer.save(active_flow_id, step_index, START, state)

        # Execution loop
        while current_node != END:
            step_index += 1
            if step_index > self.max_iterations:
                raise InfiniteLoopError(
                    f"Flow '{active_flow_id}' exceeded max_iterations ({self.max_iterations}). "
                    f"Possible infinite loop between nodes."
                )

            if current_node not in self.nodes:
                raise FlowError(f"Target node '{current_node}' is not registered in graph.")

            # Pre-node hooks / Gates
            for hook in self.pre_node_hooks:
                if not hook(current_node, state):
                    raise GateRejectionError(f"Pre-node gate rejected execution before '{current_node}'.")

            node_fn = self.nodes[current_node]

            try:
                # Node returns state delta or full state dict
                delta = node_fn(state)
                if isinstance(delta, dict):
                    state.update(delta)
            except Exception as e:
                raise NodeExecutionError(current_node, e) from e

            # Post-node hooks / Gates
            for hook in self.post_node_hooks:
                if not hook(current_node, state):
                    raise GateRejectionError(f"Post-node gate rejected state after '{current_node}'.")

            # Persist checkpoint after node completion
            self.checkpointer.save(active_flow_id, step_index, current_node, state)

            # Determine next node
            if current_node in self.conditional_edges:
                cond_fn, path_map = self.conditional_edges[current_node]
                decision = cond_fn(state)
                if decision not in path_map:
                    raise FlowError(
                        f"Conditional routing in node '{current_node}' returned '{decision}', "
                        f"which is not in path_map: {list(path_map.keys())}"
                    )
                current_node = path_map[decision]
            elif current_node in self.edges:
                current_node = self.edges[current_node]
            else:
                # Default to END if no outgoing edge defined
                current_node = END

        # Save final state checkpoint
        self.checkpointer.save(active_flow_id, step_index + 1, END, state)
        return state


class StateGraph:
    """Builder for constructing a state graph with cyclic support and checkpoints."""

    def __init__(self):
        self.nodes: Dict[str, Callable[[Dict[str, Any]], Union[Dict[str, Any], None]]] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, Tuple[Callable[[Dict[str, Any]], str], Dict[str, str]]] = {}
        self.entry_point: Optional[str] = None
        self.pre_node_hooks: List[Callable[[str, Dict[str, Any]], bool]] = []
        self.post_node_hooks: List[Callable[[str, Dict[str, Any]], bool]] = []

    def add_node(self, name: str, fn: Callable[[Dict[str, Any]], Union[Dict[str, Any], None]]) -> "StateGraph":
        """Registers a named step/node in the graph."""
        if name in (START, END):
            raise ValueError(f"Cannot name a custom node '{name}' (reserved identifier).")
        if name in self.nodes:
            raise ValueError(f"Node '{name}' is already registered in graph.")
        self.nodes[name] = fn
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        """Sets the first node to execute when the flow starts."""
        self.entry_point = name
        return self

    def add_edge(self, source: str, target: str) -> "StateGraph":
        """Adds a deterministic direct transition from source to target."""
        if source == START:
            self.set_entry_point(target)
            return self
        self.edges[source] = target
        return self

    def add_conditional_edge(
        self,
        source: str,
        condition: Callable[[Dict[str, Any]], str],
        path_map: Dict[str, str]
    ) -> "StateGraph":
        """
        Adds a dynamic conditional transition from source node based on condition function output.
        """
        self.conditional_edges[source] = (condition, path_map)
        return self

    def add_pre_gate(self, hook: Callable[[str, Dict[str, Any]], bool]) -> "StateGraph":
        """Adds a pre-node guard/gate that must evaluate to True before node execution."""
        self.pre_node_hooks.append(hook)
        return self

    def add_post_gate(self, hook: Callable[[str, Dict[str, Any]], bool]) -> "StateGraph":
        """Adds a post-node guard/gate that must evaluate to True after node execution."""
        self.post_node_hooks.append(hook)
        return self

    def compile(
        self,
        checkpoint_db: Optional[str] = None,
        max_iterations: int = 50
    ) -> CompiledGraph:
        """
        Compiles the graph definition into an executable CompiledGraph instance.
        """
        if not self.entry_point:
            raise FlowError("Graph cannot be compiled without an entry point. Use add_edge(START, <node>).")

        return CompiledGraph(
            nodes=self.nodes,
            edges=self.edges,
            conditional_edges=self.conditional_edges,
            entry_point=self.entry_point,
            checkpointer=Checkpointer(checkpoint_db) if checkpoint_db else None,
            max_iterations=max_iterations,
            pre_node_hooks=self.pre_node_hooks,
            post_node_hooks=self.post_node_hooks,
        )
