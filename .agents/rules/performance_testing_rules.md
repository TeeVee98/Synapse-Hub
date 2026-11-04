# Performance & Load Testing Invariants (k6 · JMeter · Locust)

> **Scope:** Applies whenever designing, executing, or analyzing performance, load, stress, spike, or soak test workloads.  
> Complement to `AGENTS.md` enforcing enterprise safety, workload realism, and zero-hallucination analysis.

---

## 1. Safety Gate & Pre-Flight Invariants
1. **Dedicated Environments Only:** Never run load tests against production, shared staging, or third-party APIs without written approval.
2. **Pre-Run Declaration:** Declare target host, archetype (Smoke, Average Load, Stress, Spike, Soak), VU/arrival profile, duration, and kill-switch threshold (`abortOnFail`).
3. **Progressive Escalation:** Smoke (1–5 VUs) -> Baseline Average Load -> Stress / Spike / Soak. Never start high-VU runs autonomously.
4. **Hard Caps & Kill-Switch:** Scripts must enforce finite durations, rate caps, and automated abort (`abortOnFail` when error rate > 10%). Unbounded loops are strictly forbidden.
5. **Isolation & Cleanup:** Mock third-party providers (Payment, SMS, Captcha). Use synthetic test data (`PERF_AUTO_`); teardown after runs.

---

## 2. Workload Modeling & k6 Script Standards
1. **Arrival Rate vs VU:** Use open arrival-rate executors for public traffic; use closed VU-based executors only for fixed employee portals.
2. **Realistic Think Time & Cache Skew:** Parameterize queries across realistic key spaces. Model user think time (1s–5s); zero think time is forbidden.
3. **Steady-State Evaluation:** Evaluate SLA thresholds strictly against Steady State, excluding warm-up/cool-down transients.
4. **k6 Script Structure:** `options` -> `setup()` -> default VU function (`check()`) -> `teardown()`.
   - Valid threshold syntax: `'http_req_duration{expected_response:true}': ['p(95)<500']`.
   - Always pair `check()` with `'checks': ['rate>0.99']`.
   - Set `discardResponseBodies: true` when responses are unparsed. Pass secrets via `__ENV`.

---

## 3. Truth Anchor & Autopsy Sequence
1. **Truth Anchor:** If an SLA is breached, report root cause honestly. Never loosen thresholds or drop samples to manufacture a fake pass.
2. **Analysis Sequence:** 1. Run Validity (`dropped_iterations == 0`, generator CPU < 80%) -> 2. Error Rate (4xx, 5xx, timeouts) -> 3. Latency Percentiles (P50, P90, P95, P99; never headline average) -> 4. Throughput -> 5. APM Correlation (DB slow queries, connection pool exhaustion).
