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
2. **Dynamic Parameterization:** Decouple environment hosts and concurrency via JMeter properties (with no leading whitespace after commas in `${__P(key,default)}`):
   `${__P(host,staging.local)}`, `${__P(protocol,https)}`, `${__P(port,443)}`, and `${__P(vus,50)}` (or `${__P(users,50)}`). Pass overrides via `-Jhost=... -Jport=... -Jvus=...`. Never hardcode static hosts or thread counts.
3. **Open Arrival-Rate Pacing:** For public web APIs, inject `--target-rps <N>` (`ConstantThroughputTimer`) to prevent Coordinated Omission under server queuing.
4. **Dynamic Data Prefix:** Synthetic data generation must use dynamic prefix `PERF_AUTO_` (e.g., `PERF_AUTO_${__time()}_${__threadNum}`) paired with automated teardown cleanup.
5. **AutoStop Trigger:** Configure a thread-safe global abort trigger (`props` `AtomicLong` JSR223 threshold assertion) to stop execution when aggregate error rate > 10% (`--abort-on-fail`).
6. **Steady-State Evaluation:** Evaluate SLA gates excluding warm-up and cool-down transients via `analyze-jtl results.jtl --warmup-sec <N> --cooldown-sec <M>`.

### 2.4 Locust (locustfile.py) Standards
1. **Headless Execution Standard:** Automated test executions must run headlessly via CLI:
   `locust -f locustfile.py --headless -u 50 -r 5 -t 5m --csv=perf_report`
   Mandatory headless mode with defined user count (`-u`), spawn rate (`-r`), duration (`-t`), and CSV reporting output (`--csv`). Never require the Locust web UI in automated pipelines.
2. **User Class Modeling:** Inherit from `HttpUser` or high-performance `FastHttpUser` (`geventhttpclient`) for HTTP workload simulation. Structure user journeys using `@task(weight)` and logical groupings via `@tag`.
3. **Fail-Fast Listener:** Attach an event listener via `events.quitting` or `events.request` to monitor aggregate error rate and trigger early termination when `error_rate > 0.10` (10% threshold).

---

## 3. Truth Anchor, Baseline Regression & Autopsy Sequence
1. **Truth Anchor:** If an SLA is breached, report root cause honestly. Never loosen thresholds or drop samples to manufacture a fake pass.
2. **Analysis Sequence:** 1. Run Validity (`dropped_iterations == 0`, generator CPU < 80%) -> 2. Error Rate (4xx, 5xx, timeouts) -> 3. Latency Percentiles (P50, P90, P95, P99; never headline average) -> 4. Throughput -> 5. APM Correlation (DB slow queries, connection pool exhaustion).
3. **Baseline Regression Delta Gate (`<= 15.0%`):** In addition to absolute SLA ceilings, compare candidate P95 latency against `baseline_summary.json` (`synapse.config.json::performance.sla.max_p95_regression_pct = 15.0`); fail CI if P95 regresses by more than `+15.0%` even when still below the absolute P95 ceiling.

---

## 4. Business Workload Model, SPA Leak & Mobile App Performance

### A. Business-Driven Performance Workload Design
Before authoring load scripts, lock down 3 foundational parameters anchored to `synapse.config.json::performance.sla_profiles` (single source of truth):
1. **Workload Mix:** Distribute traffic percentages across realistic user journeys (e.g., Browse 70%, Search 20%, Checkout 10%), converting DAU/CCU into target RPS via Little's Law (`L = lambda * W`).
2. **DB Data Volume Precondition:** Specify baseline dataset volume (e.g., DB pre-seeded with `>= 100,000` rows prior to measurement) to expose missing indexes and full-table scan regressions.
3. **Canonical Tiered SLA Matrix (`synapse.config.json::performance.sla_profiles`):**
   - `smoke` (Sanity Health): `P95 <= 300ms`, `P99 <= 600ms`, `Error Rate == 0.0%`
   - `read_api` (Read / Lookup API): `P95 <= 200ms`, `P99 <= 400ms`, `Error Rate <= 0.5%`
   - `search_api` (Default / Complex Search & Average Load): `P95 <= 500ms`, `P99 <= 1000ms`, `Error Rate <= 1.0%`
   - `write_checkout` (Write / Checkout / Payment): `P95 <= 800ms`, `P99 <= 1500ms`, `Error Rate <= 0.1%`

### B. Web Throttling & Long-Session SPA Memory Leak
- **Standard Measurement Profile:** Measure Core Web Vitals under emulated **Slow 4G + 4x CPU slowdown** rather than unconstrained local loopback bandwidth.
- **SPA Memory Leak Guard:** For long-lived web apps (dashboards, POS), repeat tab switches and modal open/close cycles 20–50 times and verify JS Heap Memory stabilizes without monotonic linear growth.

### C. Mobile App Performance (Android Vitals & iOS MetricKit)
Enforced on mid-tier physical devices (`mobile-appium`, `katalon`):
- **App Startup Time:** Measure **Cold / Warm / Hot Start** separately across `TTID` (Time to Initial Display) and `TTFD` (Time to Full Display).
- **UI Rendering & Smoothness:** Sustain `60 FPS` (`<= 16.6ms/frame`); track **Janky Frames** (`> 16.6ms`), **Frozen Frames** (`> 700ms`), and **ANR** (`> 5s` Android / Watchdog crash iOS) during long-list scrolling.
- **Resource & Network Resilience:** Monitor **RAM/Memory** (zero leaks across repeated screen transitions), **CPU %**, background **Battery drain**, APK/IPA binary size, and live network handoffs (**Wi-Fi <-> 4G/5G <-> Offline**).
