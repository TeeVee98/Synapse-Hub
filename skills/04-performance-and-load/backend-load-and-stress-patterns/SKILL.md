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
> **Mandatory Rule:** Adhere strictly to [performance_testing_rules.md](../../../testing/performance/performance_testing_rules.md) for safety approvals, hard caps, and truth-anchor reporting.

---

### Test Archetypes & SLA Targets (Canonical `synapse.config.json::performance.sla_profiles`)

| Archetype | VUs / Rate | Duration | Objective | Canonical SLA Assertion (`sla_profiles`) |
| :--- | :--- | :--- | :--- | :--- |
| **Smoke Test** (`smoke`) | 1 - 5 VUs | 1 - 2 min | Health sanity check | Error rate = 0.0%, P95 <= 300ms, P99 <= 600ms |
| **Read Lookup** (`read_api`) | 50 - 200 VUs | 10 - 30 min | High-frequency GET lookup | Error rate <= 0.5%, P95 <= 200ms, P99 <= 400ms |
| **Average / Search Load** (`search_api`) | 50 - 200 VUs | 10 - 30 min | Standard peak & filter capacity | Error rate <= 1.0%, P95 <= 500ms, P99 <= 1000ms |
| **Write / Checkout** (`write_checkout`) | 20 - 100 VUs | 10 - 30 min | Transactional write integrity | Error rate <= 0.1%, P95 <= 800ms, P99 <= 1500ms |
| **Stress / Spike Test** | 200 -> 2,000 VUs | 10 - 45 min | Find degradation cliff & recovery | Graceful 429/503 (zero OOM), gateway recovery < 30s |
| **Soak / Scalability** | 50 -> 200 VUs | 1 - 12 hr | Memory leaks & linear elasticity | Zero heap slope, P95 drift <= +15.0% vs baseline |

👉 **Formal Test Plan Schema:** Refer to [**ISO/IEC/IEEE 29119-3 Performance Test Plan (`references/performance_test_plan_29119.md`)**](references/performance_test_plan_29119.md) for full environmental topology, NFR SLO targets, and risk declarations.

---

### Tooling Unified Runbook

### Option A: Apache JMeter (Headless CLI + JTL Analyzer)
<!-- classification: illustrative -->
```bash
# 1. Generate XML test plan from OpenAPI / Postman (with realistic think-time & arrival-rate pacing)
synapse generate-jmx --spec api.json -o load_plan.jmx --vus 50 --duration 180 --target-rps 40 --sla-p95 500

# 2. Run headless benchmark with runtime property overrides
jmeter -n -t load_plan.jmx -Jhost=staging.example.com -Jvus=50 -l results.jtl -e -o ./html_report

# 3. Automated CI/CD Quality Gatekeeper (steady-state window excluding warm-up/cool-down)
synapse analyze-jtl results.jtl --warmup-sec 30 --cooldown-sec 10 --sla-p95 500 --max-error-rate 1.0
```

### Option B: k6 Production Load Testing (with Kill-Switch & Arrival Rate)
Execute high-concurrency production load tests with arrival-rate executors, user pooling, and automatic kill-switches.

<!-- classification: illustrative -->
```bash
# Execute k6 test suite with environment variables
k6 run -e BASE_URL=http://localhost:8080 examples/perf-backend-suite/k6/k6_load_test.js

# Run soak/endurance test and evaluate SLA gate
k6 run --summary-export=summary.json examples/perf-backend-suite/k6/k6_soak_test.js
python tools/perf/k6_analyzer.py summary.json --sla-p95 500 --max-error-rate 1.0
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

### 7-Question Empirical Benchmark Vetting Gate

Before claiming a throughput/latency improvement or regression from `k6`, `JMeter`, or `Locust` runs, verify all 7 checks:
1. **Why not double (Limiter)?** Profile CPU, I/O wait, DB locks, and load-generator saturation in a separate run to name the true limiter.
2. **Was it tuned?** Ensure release builds, connection pools, DB indexes, and warm/cold cache states match production on both sides.
3. **Did it break limits?** Cross-check RPS/bytes-per-sec against core count and network/disk limits to rule out cached no-ops.
4. **Did it error?** Report error counts alongside p95/p99; fast 4xx/5xx rejections artificially lower latency.
5. **Does it reproduce?** Alternate baseline and candidate runs (`A, B, A, B...`, >= 5 runs for close calls) and report median + range.
6. **Does it matter?** Measure end-to-end user journey impact, not only isolated micro-endpoints.
7. **Did it even happen?** Verify requests hit the real backend and mutated/returned expected payloads inside the timed window.

*Paired with [`web-vitals-and-performance-profiler`](../web-vitals-and-performance-profiler/SKILL.md) for frontend CWV empirical vetting.*

### Attribution

7-Question Empirical Benchmark Vetting Gate adapted from Lauren Tan (`@poteto`) (`benchmark-checklist`, MIT License), rescoped for `k6`, `JMeter`, and `Locust` load suites in Synapse Hub.

---

## 4. Verification Points & DoD

1. Load profile defines clear ramp-up, steady-state, and ramp-down stages.
2. Thresholds enforce p95/p99 latency ceilings and maximum allowable error rates (< 1%).
3. Performance report includes request throughput, response distribution, and failure analysis.

---

## 5. Handoff Protocol

- **Deliverables:** Load test scripts (`k6` `.js`, `JMeter` `.jmx`, `Locust` `locustfile.py`), canonical SLA profile configurations, and steady-state percentile reports.
- **Next Subagent:** perf-engineer
- **Output Format:** Parameterized headless load scripts (`.jmx` / `.js` / `.py`), steady-state JTL/k6 JSON SLA summaries, and baseline regression delta reports.
