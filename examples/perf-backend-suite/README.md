# Enterprise Performance & Load Testing Suite (Sprint 4)

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.  
> **Standards Alignment:** Conforms to **ISO/IEC 25010:2023 (Performance Efficiency)**, **ISO/IEC/IEEE 29119-3 (Performance Test Plan)**, and **ISTQB CT-PT (Certified Tester Performance Testing)**.

---

## 1. Overview & Architecture

This suite delivers a production-grade, multi-engine performance engineering ecosystem:
- **Engine 1: k6 Modern JavaScript Suite (`k6/`)** — Ramping arrival-rate executors, user pooling (`SharedArray`), per-VU session isolation, automated kill-switch (`abortOnFail`), and strict percentile SLA assertions (`P95 < 500ms`, `P99 < 1000ms`, `Error Rate < 1.0%`).
- **Engine 2: Apache JMeter 5.6.3 Suite (`jmeter/`)** — Headless XML test plan parameterized via JMeter CLI properties (`-Jhost=... -Jusers=...`), Gaussian Random Timers, Response Assertions, and automated JTL reporting.
- **Engine 3: Locust Code-as-Code Suite (`locust/`)** — High-performance Python `HttpUser` class, Pareto 70/20/10 traffic mix modeling, fail-fast event listeners, and standalone multi-threaded headless runner.

---

## 2. Workload Archetypes (ISTQB CT-PT)

| Archetype | File | Concurrency / Profile | Duration | Core Verification Target | SLA Threshold |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Smoke Test** | `k6/k6_smoke_test.js` | 5 VUs constant | 1 min | Sanity check endpoint responsiveness | Error: 0.0%, P95 < 300ms |
| **Peak Load** | `k6/k6_load_test.js` | Ramping arrival-rate (5 -> 20/s) | 3 min | Nominal peak capacity & throughput | Error < 0.5%, P95 < 500ms |
| **Stress Test** | `k6/k6_stress_test.js` | Step-up (20 -> 50 -> 100 -> 200 VUs) | 4 min | Detect degradation cliff & graceful 429/503 | No server crash / leak |
| **Spike Test** | `k6/k6_spike_test.js` | Shock surge (5 -> 150 VUs) | 1.5 min | Circuit breaker & autoscaling recovery | Recovery < 30s |
| **Soak / Endurance** | `k6/k6_soak_test.js` | Constant sustained load (30 VUs) | 15 min | Memory leak & thread depletion drift | Error < 0.5%, P95 < 600ms |
| **JMeter Load** | `jmeter/jmeter_api_load_suite.jmx` | 10–50 Threads | Parameterized | Enterprise XML test execution | P95 < 500ms |

---

## 3. Quick Start & Execution

### 3.1 Running with k6
```bash
# Smoke test
k6 run k6/k6_smoke_test.js

# Peak Load test with custom AUT URL
k6 run -e BASE_URL=http://localhost:8080 k6/k6_load_test.js

# Soak / Endurance test (exporting summary JSON)
k6 run --summary-export=summary.json k6/k6_soak_test.js

# Automated CI/CD SLA Analysis for k6
python tools/perf/k6_analyzer.py summary.json --sla-p95 500 --max-error-rate 1.0 --markdown reports/perf/K6_PERF_REPORT.md
```

### 3.2 Running with Apache JMeter (Headless CLI)
```bash
jmeter -n -t jmeter/jmeter_api_load_suite.jmx -l reports/perf/perf_results.jtl -e -o reports/perf/html_report
```

### 3.3 Running with Locust / Headless Python Engine
```bash
python locust/run_locust_headless.py --vus 15 --duration 30 -o reports/perf/perf_results.jtl
```

### 3.4 Automated CI/CD SLA Analysis
```bash
python tools/perf/jtl_analyzer.py reports/perf/perf_results.jtl --sla-p95 500 --max-error-rate 1.0 --markdown reports/perf/PERFORMANCE_REPORT.md
```
