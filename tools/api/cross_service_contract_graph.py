#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Cross-Service Contract Graph & Ephemeral Micro-Sandboxing
---------------------------------------------------------
Replaces blind state-flushing with a typed dependency DAG for multi-service architectures.
Maintains invariant upstream and downstream contract schemas during batch execution,
detects API breaking changes across consumers before committing, and provides
ephemeral micro-sandboxing to isolate filesystem and runtime state per service.
"""

import os
import sys
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set

_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_TOOLS_ROOT)
for _p in (_REPO_ROOT, _TOOLS_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    import tools  # noqa: F401
except ImportError:  # synapse-ignore: SWALLOWED_EXCEPTION
    pass

from tools.api.api_drift_sentinel import compare_specs


@dataclass
class ServiceContractNode:
    """Represents a microservice or domain module in the distributed contract graph."""
    service_id: str
    version: str = "1.0.0"
    spec_path: Optional[str] = None
    spec_data: Dict[str, Any] = field(default_factory=dict)
    consumes: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_id": self.service_id,
            "version": self.version,
            "spec_path": self.spec_path,
            "spec_data": self.spec_data,
            "consumes": self.consumes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceContractNode":
        return cls(
            service_id=data.get("service_id", ""),
            version=data.get("version", "1.0.0"),
            spec_path=data.get("spec_path"),
            spec_data=data.get("spec_data", {}),
            consumes=data.get("consumes", []),
            metadata=data.get("metadata", {}),
        )


class CrossServiceContractGraph:
    """
    Typed Cross-Service Dependency DAG.
    Tracks producer-consumer relationships, extracts minimal schema contexts,
    and enforces bidirectional compatibility across multi-service pipelines.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, ServiceContractNode] = {}

    def register_service(self, node: ServiceContractNode | Dict[str, Any]) -> None:
        """Registers a service node in the contract graph."""
        if isinstance(node, dict):
            node = ServiceContractNode.from_dict(node)
        self.nodes[node.service_id] = node

    def build_dependency_dag(self) -> Dict[str, List[str]]:
        """
        Builds adjacency list of dependencies:
        service_id -> list of upstream services it depends on (consumes).
        """
        dag: Dict[str, List[str]] = {s_id: [] for s_id in self.nodes}
        for s_id, node in self.nodes.items():
            for req in node.consumes:
                upstream_id = req.get("service_id")
                if upstream_id and upstream_id not in dag[s_id]:
                    dag[s_id].append(upstream_id)
        return dag

    def build_consumer_dag(self) -> Dict[str, List[str]]:
        """
        Builds adjacency list of consumers:
        producer_id -> list of downstream services that consume it.
        """
        consumer_dag: Dict[str, List[str]] = {s_id: [] for s_id in self.nodes}
        for s_id, node in self.nodes.items():
            for req in node.consumes:
                producer_id = req.get("service_id")
                if producer_id in consumer_dag and s_id not in consumer_dag[producer_id]:
                    consumer_dag[producer_id].append(s_id)
        return consumer_dag

    def get_topological_execution_order(self) -> List[str]:
        """
        Computes valid execution order using Kahn's algorithm (topological sort).
        Producers without dependencies are processed first.
        Raises ValueError if a cyclic dependency is detected.
        """
        dep_dag = self.build_dependency_dag()
        # In-degree is count of upstream services each service depends on
        in_degree: Dict[str, int] = {s_id: len(deps) for s_id, deps in dep_dag.items()}

        # Queue contains services with 0 dependencies
        queue: List[str] = [s_id for s_id, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        # Adjacency from producer to consumers
        consumer_dag = self.build_consumer_dag()

        while queue:
            curr = queue.pop(0)
            order.append(curr)

            for consumer in consumer_dag.get(curr, []):
                in_degree[consumer] -= 1
                if in_degree[consumer] == 0:
                    queue.append(consumer)

        if len(order) < len(self.nodes):
            remaining = [s for s, deg in in_degree.items() if deg > 0]
            raise ValueError(f"Cycle detected in cross-service contract graph among: {remaining}")

        return order

    def get_service_context(self, service_id: str) -> Dict[str, Any]:
        """
        Extracts minimal invariant context for a specific service:
        - upstream_dependencies: Schemas of services this service calls.
        - downstream_consumers: Endpoints and fields required by consumers calling this service.
        """
        if service_id not in self.nodes:
            raise KeyError(f"Service '{service_id}' not found in contract graph.")

        node = self.nodes[service_id]
        upstream_deps: Dict[str, Any] = {}
        for req in node.consumes:
            u_id = req.get("service_id")
            if u_id and u_id in self.nodes:
                upstream_deps[u_id] = {
                    "version": self.nodes[u_id].version,
                    "spec_data": self.nodes[u_id].spec_data,
                    "required_contract": req,
                }

        downstream_consumers: List[Dict[str, Any]] = []
        for other_id, other_node in self.nodes.items():
            for req in other_node.consumes:
                if req.get("service_id") == service_id:
                    downstream_consumers.append({
                        "consumer_id": other_id,
                        "consumer_version": other_node.version,
                        "expectation": req,
                    })

        return {
            "service_id": service_id,
            "version": node.version,
            "spec_data": node.spec_data,
            "upstream_dependencies": upstream_deps,
            "downstream_consumers": downstream_consumers,
        }

    def verify_contract_compatibility(
        self, service_id: str, new_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verifies if an updated contract spec introduces breaking changes
        for any registered downstream consumers.
        """
        if service_id not in self.nodes:
            raise KeyError(f"Service '{service_id}' not found in contract graph.")

        old_node = self.nodes[service_id]
        old_spec = old_node.spec_data

        # 1. Structural schema comparison via compare_specs
        drift_analysis = compare_specs(old_spec, new_spec)
        breaking = list(drift_analysis.get("breaking_changes", []))
        warnings = list(drift_analysis.get("warnings", []))

        # 2. Cross-check against consumer expectations
        impacted_consumers: Set[str] = set()
        ctx = self.get_service_context(service_id)

        new_paths = new_spec.get("paths", {})

        for c_entry in ctx["downstream_consumers"]:
            consumer_id = c_entry["consumer_id"]
            exp = c_entry["expectation"]
            exp_ep = exp.get("endpoint")
            exp_method = (exp.get("method") or "get").lower()

            if exp_ep:
                # Check if expected endpoint was deleted
                if exp_ep not in new_paths:
                    breaking.append({
                        "type": "CONSUMER_ENDPOINT_REMOVED",
                        "path": f"{exp_method.upper()} {exp_ep}",
                        "detail": f"Consumer '{consumer_id}' expects deleted endpoint '{exp_ep}'",
                    })
                    impacted_consumers.add(consumer_id)
                elif exp_method not in new_paths[exp_ep]:
                    breaking.append({
                        "type": "CONSUMER_METHOD_REMOVED",
                        "path": f"{exp_method.upper()} {exp_ep}",
                        "detail": f"Consumer '{consumer_id}' expects deleted method '{exp_method.upper()}' on '{exp_ep}'",
                    })
                    impacted_consumers.add(consumer_id)

        # Also map general breaking changes to all consumers
        if breaking:
            for c_entry in ctx["downstream_consumers"]:
                impacted_consumers.add(c_entry["consumer_id"])

        is_compatible = len(breaking) == 0

        return {
            "is_compatible": is_compatible,
            "service_id": service_id,
            "breaking_changes": breaking,
            "warnings": warnings,
            "impacted_consumers": sorted(list(impacted_consumers)),
            "contract_health_score": drift_analysis.get("contract_health_score", 100.0 if is_compatible else 0.0),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "services": [node.to_dict() for node in self.nodes.values()]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrossServiceContractGraph":
        graph = cls()
        for s_data in data.get("services", []):
            graph.register_service(s_data)
        return graph


class EphemeralServiceSandbox:
    """
    Ephemeral Micro-Sandbox for service-level execution.
    Creates isolated temporary working tree, dynamic port binding,
    and dedicated database instances to prevent cross-service collision.
    """

    def __init__(
        self,
        service_id: str,
        base_dir: Optional[str] = None,
        port_offset: int = 0,
        keep_on_error: bool = False,
    ) -> None:
        self.service_id = service_id
        self.base_dir = base_dir
        self.port_offset = port_offset
        self.keep_on_error = keep_on_error
        self.sandbox_dir: Optional[str] = None
        self.prev_env: Dict[str, Optional[str]] = {}

    def __enter__(self) -> Dict[str, Any]:
        if self.base_dir:
            os.makedirs(self.base_dir, exist_ok=True)
            self.sandbox_dir = tempfile.mkdtemp(prefix=f"sbx_{self.service_id}_", dir=self.base_dir)
        else:
            self.sandbox_dir = tempfile.mkdtemp(prefix=f"sbx_{self.service_id}_")

        port = 10000 + self.port_offset
        sqlite_db = os.path.join(self.sandbox_dir, f"{self.service_id}.sqlite3")

        # Snapshot and set environment
        env_updates = {
            "SYNAPSE_SANDBOX_DIR": self.sandbox_dir,
            "SERVICE_PORT": str(port),
            "SQLITE_DB_PATH": sqlite_db,
        }
        for k, v in env_updates.items():
            self.prev_env[k] = os.environ.get(k)
            os.environ[k] = v

        return {
            "service_id": self.service_id,
            "sandbox_dir": self.sandbox_dir,
            "port": port,
            "sqlite_db_path": sqlite_db,
        }

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Restore environment
        for k, orig_val in self.prev_env.items():
            if orig_val is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = orig_val

        # Teardown sandbox
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            if exc_type is not None and self.keep_on_error:
                sys.stderr.write(f"Notice: Preserving failed sandbox: {self.sandbox_dir}\n")
            else:
                shutil.rmtree(self.sandbox_dir, ignore_errors=True)
