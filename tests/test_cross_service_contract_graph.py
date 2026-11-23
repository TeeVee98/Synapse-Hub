# SPDX-FileCopyrightText: © 2026 Thế Vị (@TeeVee98) <https://github.com/TeeVee98/Synapse-Hub>
# SPDX-License-Identifier: MIT

"""
Tests for Cross-Service Contract Graph & Ephemeral Micro-Sandboxing
Validates typed contract DAG, upstream/downstream schema context extraction,
breaking change detection across consumers, and ephemeral runtime isolation.
"""

import os
import sys
import tempfile
import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TESTS_DIR)
_TOOLS_DIR = os.path.join(_REPO_ROOT, "tools")
for _p in (_REPO_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from tools.api.cross_service_contract_graph import (
    CrossServiceContractGraph,
    ServiceContractNode,
    EphemeralServiceSandbox,
)


def _make_sample_spec(paths_dict=None):
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": paths_dict or {
            "/api/auth/token": {
                "post": {
                    "summary": "Obtain Token",
                    "parameters": [
                        {"name": "grant_type", "in": "query", "required": True, "type": "string"}
                    ],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }


def test_contract_graph_registration_and_dag():
    graph = CrossServiceContractGraph()

    auth_node = ServiceContractNode(
        service_id="auth-service",
        version="1.0.0",
        spec_data=_make_sample_spec(),
        consumes=[],
    )
    order_node = ServiceContractNode(
        service_id="order-service",
        version="1.0.0",
        spec_data=_make_sample_spec({"/api/orders": {"get": {"responses": {"200": {}}}}}),
        consumes=[
            {"service_id": "auth-service", "endpoint": "/api/auth/token", "method": "POST"},
            {"service_id": "auth-service", "endpoint": "/api/auth/token2", "method": "POST"},
            {"service_id": ""},
        ],
    )
    notif_node = ServiceContractNode(
        service_id="notification-service",
        version="1.0.0",
        spec_data=_make_sample_spec({"/api/notify": {"post": {"responses": {"200": {}}}}}),
        consumes=[{"service_id": "order-service", "endpoint": "/api/orders", "method": "GET"}],
    )

    graph.register_service(auth_node)
    graph.register_service(order_node)
    graph.register_service(notif_node)

    dep_dag = graph.build_dependency_dag()
    assert dep_dag["order-service"] == ["auth-service"]

    consumer_dag = graph.build_consumer_dag()
    assert consumer_dag["auth-service"] == ["order-service"]

    order = graph.get_topological_execution_order()
    # auth-service must come before order-service, which must come before notification-service
    auth_idx = order.index("auth-service")
    order_idx = order.index("order-service")
    notif_idx = order.index("notification-service")

    assert auth_idx < order_idx
    assert order_idx < notif_idx
    assert len(order) == 3


def test_contract_graph_cycle_detection():
    graph = CrossServiceContractGraph()
    node_a = ServiceContractNode(
        service_id="service-a",
        consumes=[{"service_id": "service-b"}],
    )
    node_b = ServiceContractNode(
        service_id="service-b",
        consumes=[{"service_id": "service-a"}],
    )
    graph.register_service(node_a)
    graph.register_service(node_b)

    with pytest.raises(ValueError) as excinfo:
        graph.get_topological_execution_order()

    err_text = str(excinfo.value)
    assert "cycle" in err_text.lower()
    assert "service-a" in err_text
    assert "service-b" in err_text


def test_get_service_context_upstream_and_downstream():
    graph = CrossServiceContractGraph()
    auth_spec = _make_sample_spec()
    order_spec = _make_sample_spec({"/api/orders": {"get": {"responses": {"200": {}}}}})

    graph.register_service(ServiceContractNode(
        service_id="auth-service",
        spec_data=auth_spec,
        consumes=[],
    ))
    graph.register_service(ServiceContractNode(
        service_id="order-service",
        spec_data=order_spec,
        consumes=[
            {"service_id": "auth-service", "endpoint": "/api/auth/token", "method": "POST"},
            {"service_id": "unregistered-dep", "endpoint": "/api/dep"},
            {"service_id": ""},
        ],
    ))

    # Inspect context for order-service
    ctx = graph.get_service_context("order-service")
    assert ctx["service_id"] == "order-service"
    assert "auth-service" in ctx["upstream_dependencies"]
    assert "unregistered-dep" not in ctx["upstream_dependencies"]
    upstream_auth = ctx["upstream_dependencies"]["auth-service"]
    assert "/api/auth/token" in upstream_auth["spec_data"]["paths"]

    # Inspect context for auth-service
    auth_ctx = graph.get_service_context("auth-service")
    assert len(auth_ctx["downstream_consumers"]) >= 1
    consumer_ids = [c["consumer_id"] for c in auth_ctx["downstream_consumers"]]
    assert "order-service" in consumer_ids


def test_verify_contract_compatibility_detects_breaking_change():
    graph = CrossServiceContractGraph()
    auth_spec = _make_sample_spec()
    graph.register_service(ServiceContractNode(
        service_id="auth-service",
        spec_data=auth_spec,
    ))
    graph.register_service(ServiceContractNode(
        service_id="order-service",
        consumes=[{"service_id": "auth-service", "endpoint": "/api/auth/token", "method": "POST"}],
    ))

    # New spec removes /api/auth/token completely!
    broken_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "2.0.0"},
        "paths": {
            "/api/v2/oauth/token": {"post": {"responses": {"200": {}}}}
        }
    }

    compat = graph.verify_contract_compatibility("auth-service", broken_spec)
    assert compat["is_compatible"] is False
    assert len(compat["breaking_changes"]) >= 1
    types = [b["type"] for b in compat["breaking_changes"]]
    assert "REMOVED_ENDPOINT" in types
    assert "order-service" in compat["impacted_consumers"]


def test_verify_contract_compatibility_backward_compatible():
    graph = CrossServiceContractGraph()
    auth_spec = _make_sample_spec()
    graph.register_service(ServiceContractNode(
        service_id="auth-service",
        spec_data=auth_spec,
    ))
    graph.register_service(ServiceContractNode(
        service_id="order-service",
        consumes=[{"service_id": "auth-service", "endpoint": "/api/auth/token", "method": "POST"}],
    ))

    # New spec keeps /api/auth/token and adds /api/auth/refresh
    updated_spec = _make_sample_spec({
        "/api/auth/token": auth_spec["paths"]["/api/auth/token"],
        "/api/auth/refresh": {"post": {"responses": {"200": {}}}},
    })

    compat = graph.verify_contract_compatibility("auth-service", updated_spec)
    assert compat["is_compatible"] is True
    assert len(compat["breaking_changes"]) == 0


def test_ephemeral_service_sandbox_isolation_and_cleanup():
    tmp_base = tempfile.mkdtemp()
    sandbox = EphemeralServiceSandbox(service_id="payment-svc", base_dir=tmp_base, port_offset=42)
    assert sandbox.keep_on_error is False

    with sandbox as sb:
        sandbox_dir = sb["sandbox_dir"]
        port = sb["port"]
        db_path = sb["sqlite_db_path"]

        assert os.path.isdir(sandbox_dir)
        assert port == 10042
        assert db_path.startswith(sandbox_dir)
        assert os.environ.get("SYNAPSE_SANDBOX_DIR") == sandbox_dir
        assert os.environ.get("SERVICE_PORT") == str(port)

        # Write dummy file inside sandbox
        dummy = os.path.join(sandbox_dir, "test.txt")
        with open(dummy, "w", encoding="utf-8") as f:
            f.write("isolation test")
        assert os.path.exists(dummy)

    # After normal exit, sandbox_dir should be cleanly wiped and env vars restored
    assert not os.path.exists(sandbox_dir)
    assert "SYNAPSE_SANDBOX_DIR" not in os.environ
    assert "SERVICE_PORT" not in os.environ

    # Test error retention when keep_on_error is True
    err_sb = EphemeralServiceSandbox(service_id="err-svc", base_dir=tmp_base, keep_on_error=True)
    with pytest.raises(RuntimeError):
        with err_sb as sb_err:
            preserved_dir = sb_err["sandbox_dir"]
            raise RuntimeError("Expected simulation error")
    assert os.path.exists(preserved_dir)

    # Test clean deletion when keep_on_error is False during error
    err_sb2 = EphemeralServiceSandbox(service_id="err-svc-2", base_dir=tmp_base, keep_on_error=False)
    with pytest.raises(RuntimeError):
        with err_sb2 as sb_err2:
            cleaned_dir = sb_err2["sandbox_dir"]
            raise RuntimeError("Expected simulation error 2")
    assert not os.path.exists(cleaned_dir)
