---
trigger: on_demand
description: Performance and load testing invariants for k6, JMeter, and Locust suites.
profiles: [perf, full]
---

# Performance & Load Testing Invariants (k6 · JMeter · Locust)

> **Scope:** Applies whenever designing, executing, or analyzing performance, load, stress, spike, soak, or scalability workloads.  
> **International Standards Alignment:** Codifies ISO/IEC 25010:2023 (Performance Efficiency), ISO/IEC/IEEE 29119-3/4, ISTQB CT-PT, TPC/SPEC Steady-State discipline, Google SRE SLA budgets, and W3C Trace Context.  
> Complement to `AGENTS.md` enforcing enterprise safety, workload realism, and zero-hallucination analysis.

---

## 1. Safety Gate & Pre-Flight Invariants
1. **Dedicated Environments Only:** Never run load tests against production, shared staging, or third-party APIs without written approval.
2. **Pre-Run Declaration:** Declare target host, archetype (Smoke, Average Load, Stress, Spike, Soak, Scalability), VU/arrival profile, duration, and kill-switch threshold (`abortOnFail`).
3. **Progressive Escalation:** Smoke (1–5 VUs) -> Baseline Average Load -> Stress / Spike / Soak / Scalability. Never start high-VU runs autonomously.
4. **Hard Caps & Kill-Switch:** Scripts must enforce finite durations, rate caps, and automated abort (`abortOnFail` when error rate > 10%). Unbounded loops are strictly forbidden.
5. **Isolation & Cleanup:** Mock third-party providers (Payment, SMS, Captcha). Use synthetic test data (`PERF_AUTO_`); teardown after runs.

---

## 2. Workload Modeling & Multi-Tool Standards (k6 · JMeter · Locust)

### 2.1 Universal Workload Invariants
1. **Arrival Rate vs VU:** Use open arrival-rate executors for public traffic; use closed VU-based executors only for fixed employee portals.
2. **Realistic Think Time & Cache Skew:** Parameterize queries across realistic key spaces. Model user think time (1s–5s); zero think time is forbidden.
3. **Steady-State Evaluation:** Evaluate SLA thresholds strictly against Steady State, excluding warm-up/cool-down transients.

### 2.2 k6 Script Standards
1. **k6 Script Structure:** `options` -> `setup()` -> default VU function (`check()`) -> `teardown()`.
2. **Threshold Syntax:** Use valid syntax, e.g., `'http_req_duration{expected_response:true}': ['p(95)<500']`.
3. **Assertion Coupling:** Always pair `check()` with `'checks': ['rate>0.99']`.
4. **Resource Discipline:** Set `discardResponseBodies: true` when responses are unparsed. Pass secrets via `__ENV`.

### 2.3 Apache JMeter (.jmx) Standards
1. **Mandatory Non-GUI Execution:** Automated test runs must execute via CLI non-GUI mode:
   `jmeter -n -t plan.jmx -l results.jtl -e -o report/`
   GUI mode is strictly forbidden for load generation in automated pipelines or CI/CD.
2. **Dynamic Parameterization:** Decouple environment hosts and concurrency via JMeter properties:
   `${__P(host,staging.local)}` and `${__P(users,50)}`. Pass overrides via `-Jhost=... -Jusers=...`. Never hardcode static hosts or thread counts.
3. **Dynamic Data Prefix:** Synthetic data generation must use dynamic prefix `PERF_AUTO_` (e.g., `PERF_AUTO_${__time()}_${__threadNum}`) paired with automated teardown cleanup.
4. **AutoStop Trigger:** Configure an automated abort trigger (AutoStop listener plugin or JSR223 threshold assertion) to stop execution when error rate > 10% or P95 latency breaches SLA limits.

### 2.4 Locust (locustfile.py) Standards
1. **Headless Execution Standard:** Automated test executions must run headlessly via CLI:
   `locust -f locustfile.py --headless -u 50 -r 5 -t 5m --csv=perf_report`
   Mandatory headless mode with defined user count (`-u`), spawn rate (`-r`), duration (`-t`), and CSV reporting output (`--csv`). Never require the Locust web UI in automated pipelines.
2. **User Class Modeling:** Inherit from `HttpUser` or high-performance `FastHttpUser` (`geventhttpclient`) for HTTP workload simulation. Structure user journeys using `@task(weight)` and logical groupings via `@tag`.
3. **Fail-Fast Listener:** Attach an event listener via `events.quitting` or `events.request` to monitor aggregate error rate and trigger early termination when `error_rate > 0.10` (10% threshold).

---

## 3. Truth Anchor & Autopsy Sequence
1. **Truth Anchor:** If an SLA is breached, report root cause honestly. Never loosen thresholds or drop samples to manufacture a fake pass.
2. **Analysis Sequence:** 1. Run Validity (`dropped_iterations == 0`, generator CPU < 80%) -> 2. Error Rate (4xx, 5xx, timeouts) -> 3. Latency Percentiles (P50, P90, P95, P99; never headline average) -> 4. Throughput -> 5. APM Correlation (DB slow queries, connection pool exhaustion).
