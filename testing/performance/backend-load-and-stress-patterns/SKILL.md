---
name: backend-load-and-stress-patterns
description: "Orchestrate k6, Locust, and JMeter backend load, stress, and SLA endurance test suites. Use when designing load, stress, or spike test patterns for backend systems."
category: test_automation_and_execution
version: "1.0.0"
policies:
  network: sandbox-only
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Backend Load & Performance Testing Skill

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Orchestrate k6, Locust, and JMeter backend load, stress, and SLA endurance test suites. Use when designing load, stress, or spike test patterns for backend systems.
- **Activation Scope:** Domain workflows for `04-performance-and-load` involving `backend-load-and-stress-patterns`.

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
- Do NOT run uncontrolled load tests against production systems without explicit authorization and scheduling.
- Do NOT ramp virtual users instantly without realistic warm-up stages (prevent artificial cold-start spikes).
- Do NOT ignore server error rates (p95 latency and HTTP 5xx errors must both be tracked).
- **Sibling Skill Boundaries:**
  - web-vitals-and-performance-profiler tests frontend client rendering; backend-load-and-stress-patterns tests server throughput and saturation (k6/JMeter).

---

## 3. Ordered Execution Workflow

> **Target:** Model concurrent Virtual User (VU) and arrival-rate traffic, execute stress/soak test profiles, and enforce automated SLA gates (P95/P99 latency, error rate < 1.0%) to detect bottlenecks before production.  
> **Mandatory Rule:** Adhere strictly to [performance_testing_rules.md](../performance_testing_rules.md) for safety approvals, hard caps, and truth-anchor reporting.

---

### Test Archetypes & SLA Targets (ISTQB CT-PT Standards)

| Archetype | VUs / Rate | Duration | Objective | SLA Assertion |
| :--- | :--- | :--- | :--- | :--- |
| **Smoke Test** | 1 - 5 VUs | 1 - 2 min | Health sanity check | Error rate = 0%, P95 < 300ms |
| **Average Load** | 50 - 200 VUs | 10 - 30 min | Standard peak capacity | Error rate < 0.5%, P95 < 500ms |
| **Stress Test** | 200 -> 2,000 VUs | 20 - 45 min | Find degradation cliff | Graceful 429/503 (no JVM OOM) |
| **Spike Test** | 10 -> 1,000 VUs | 5 - 10 min | Autoscaling & rate limiters | Gateway recovery < 30s |
| **Soak Test** | 50 - 100 VUs | 2 - 12 hr | Memory leaks & connection leaks | Stable heap & steady latency |
| **Scalability Test** | 50 -> 100 -> 200 VUs | 30 - 60 min | Linear scale-up/out elasticity | Throughput scales $\ge 80\%$ linearly |

👉 **Formal Test Plan Schema:** Refer to [**ISO/IEC/IEEE 29119-3 Performance Test Plan (`references/performance_test_plan_29119.md`)**](references/performance_test_plan_29119.md) for full environmental topology, NFR SLO targets, and risk declarations.

---

### Tooling Unified Runbook

### Option A: Apache JMeter (Headless CLI + JTL Analyzer)
<!-- classification: illustrative -->
```bash
# 1. Generate XML test plan from OpenAPI / Postman
synapse generate-jmx --spec api.json -o load_plan.jmx --vus 50 --duration 180 --sla-p95 500

# 2. Run headless benchmark
jmeter -n -t load_plan.jmx -l results.jtl -e -o ./html_report

# 3. Automated CI/CD Quality Gatekeeper
synapse analyze-jtl results.jtl --sla-p95 500 --max-error-rate 1.0
```

### Option B: k6 Production Load Testing (with Kill-Switch & Arrival Rate)
Execute high-concurrency production load tests with arrival-rate executors, user pooling, and automatic kill-switches.

<!-- classification: illustrative -->
```bash
# Execute k6 test suite with environment variables
k6 run -e BASE_URL=https://api.staging.enterprise.local tests/perf/load_test.js
```

👉 **Full Implementation Script:** Refer to [**k6 Load Testing Template (`references/k6_load_template.js`)**](references/k6_load_template.js) for arrival-rate scenarios, SLA thresholds (`P95 < 500ms`, `P99 < 1000ms`), and per-VU session isolation.

---

### Best Practices & Safety Invariants

- **Isolated Test Data:** Always use dynamic runtime identifiers (`PERF_AUTO_${Date.now()}`) to eliminate primary key collisions.
- **TearDown Hygiene:** Complement POST/creation load tests with automated teardown or ephemeral DB snapshots (`tools/core/db_sandbox.py`).
- **Telemetry Correlation:** Pair JTL/k6 metrics with server CPU/Memory traces via `tools/report/telemetry_correlator.py`.
- **Truth Anchor:** Never loosen thresholds to manufacture a false pass. A failing threshold indicates a system capacity limit to be investigated.

---

### Code-as-Code Load Model (Locust)

> *Borrowed and adapted from the Locust load-testing model (MIT license, locustio/locust).*

When version-controlled, reviewable load tests matter more than XML tooling,
generate a runnable locustfile from the same API ingestion used for JMeter:

<!-- classification: illustrative -->
```bash
synapse generate-jmx --spec swagger.json --emit-locust locustfile.py \
  --weighted-mix "70,20,10" --think-time-min 500 --think-time-max 1500
locust -f locustfile.py --host=https://api.staging.enterprise.local
```

The generated file follows the Locust shape — one `HttpUser` class, one
`@task(weight)` method per endpoint, `wait_time` from think-time — so QA
engineers can hand-tune scenarios in pure Python and commit them next to the
test suite.

1. **Weights are the traffic mix** — the same `--weighted-mix` percentages that
   drive JMeter `ThroughputController`s drive `@task` weights; keep both exports
   in sync from one spec.
2. **Prefer code-as-code for logic-heavy journeys** — conditional flows
   (login → create → assert → delete) are Python, not XML; use the JMX export
   for protocol breadth (JDBC/Kafka/gRPC/WS) and Locust for flow logic.
3. **Same SLA gates** — run `agent-qa analyze-jtl` semantics on Locust stats:
   fail CI when P95 breaches the SLA budget.

---

## 4. Verification Points & DoD

1. Load profile defines clear ramp-up, steady-state, and ramp-down stages.
2. Thresholds enforce p95/p99 latency ceilings and maximum allowable error rates (< 1%).
3. Performance report includes request throughput, response distribution, and failure analysis.

---

## 5. Handoff Protocol

- **Deliverables:** Load test scripts (`k6` / `JMeter`), threshold configurations, and performance execution reports.
- **Next Subagent:** perf-engineer
- **Output Format:** Clean POM code, structured JSON telemetry, or validated markdown handoff.
