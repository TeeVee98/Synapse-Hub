---
name: backend-load-and-stress-patterns
description: "Orchestrate k6, Locust, and JMeter backend load, stress, and SLA endurance test suites. Use when designing load, stress, or spike test patterns for backend systems."
---

# Backend Load & Performance Testing Skill

> **Target:** Model concurrent Virtual User (VU) and arrival-rate traffic, execute stress/soak test profiles, and enforce automated SLA gates (P95/P99 latency, error rate < 1.0%) to detect bottlenecks before production.  
> **Mandatory Rule:** Adhere strictly to [performance_testing_rules.md](../../rules/performance_testing_rules.md) for safety approvals, hard caps, and truth-anchor reporting.

---

## 1. Test Archetypes & SLA Targets

| Archetype | VUs / Rate | Duration | Objective | SLA Assertion |
| :--- | :--- | :--- | :--- | :--- |
| **Smoke Test** | 1 - 5 VUs | 1 - 2 min | Health sanity check | Error rate = 0%, P95 < 300ms |
| **Average Load** | 50 - 200 VUs | 10 - 30 min | Standard peak capacity | Error rate < 0.5%, P95 < 500ms |
| **Stress Test** | 200 -> 2,000 VUs | 20 - 45 min | Find degradation cliff | Graceful 429/503 (no JVM OOM) |
| **Spike Test** | 10 -> 1,000 VUs | 5 - 10 min | Autoscaling & rate limiters | Gateway recovery < 30s |
| **Soak Test** | 50 - 100 VUs | 2 - 12 hr | Memory leaks & connection leaks | Stable heap & steady latency |

---

## 2. Tooling Unified Runbook

### Option A: Apache JMeter (Headless CLI + JTL Analyzer)
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

```bash
# Execute k6 test suite with environment variables
k6 run -e BASE_URL=https://api.staging.enterprise.local tests/perf/load_test.js
```

👉 **Full Implementation Script:** Refer to [**k6 Load Testing Template (`references/k6_load_template.js`)**](references/k6_load_template.js) for arrival-rate scenarios, SLA thresholds (`P95 < 500ms`, `P99 < 1000ms`), and per-VU session isolation.

---

## 3. Best Practices & Safety Invariants

- **Isolated Test Data:** Always use dynamic runtime identifiers (`PERF_AUTO_${Date.now()}`) to eliminate primary key collisions.
- **TearDown Hygiene:** Complement POST/creation load tests with automated teardown or ephemeral DB snapshots (`tools/db_sandbox.py`).
- **Telemetry Correlation:** Pair JTL/k6 metrics with server CPU/Memory traces via `tools/telemetry_correlator.py`.
- **Truth Anchor:** Never loosen thresholds to manufacture a false pass. A failing threshold indicates a system capacity limit to be investigated.

---

## 4. Code-as-Code Load Model (Locust)

> *Borrowed and adapted from the Locust load-testing model (MIT license, locustio/locust).*

When version-controlled, reviewable load tests matter more than XML tooling,
generate a runnable locustfile from the same API ingestion used for JMeter:

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
