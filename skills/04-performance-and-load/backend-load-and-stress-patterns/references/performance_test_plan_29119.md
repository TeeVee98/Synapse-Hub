# Performance Test Plan (PTP) — ISO/IEC/IEEE 29119-3 Reference

> **Standard Compliance:** Conforms to ISO/IEC/IEEE 29119-3 (Non-Functional Test Plan), ISO/IEC 25010:2023 (Performance Efficiency), ISTQB CT-PT, and Google SRE Framework.  
> **Target Execution Engines:** Apache JMeter 5.x, k6, Locust.

---

## 1. Document Overview & Context (ISO 29119-3 §5.2)

- **Test Plan ID:** `PTP-PERF-YYYYMMDD-[MODULE]`
- **Target System / AUT:** `[Application / Microservices under test]`
- **Revision History:** `v1.0 (Initial Draft)`
- **Author / Lead Performance QA:** `[AI Agent perf-engineer / Performance Architect]`
- **Scope of Testing:**
  - *In-Scope Endpoints / Journeys:* `[List of APIs, gRPC methods, or user journeys]`
  - *Out-of-Scope Dependencies:* `[Third-party payment gateways, SMS providers, external CDNs — to be mocked]`
- **Key Business Stakeholders:** `[Product Owner, Lead Architect, SRE Manager]`

---

## 2. Software Quality Criteria (ISO/IEC 25010:2023 SQuaRE)

| SQuaRE Sub-Characteristic | Target Metric / Evaluation Criteria | Verification Tool / Engine |
| :--- | :--- | :--- |
| **Time Behaviour** | P90, P95, P99 Tail Latencies, Peak Throughput (TPS/RPS), TTFB | `tools/perf/jtl_analyzer.py` / `k6` |
| **Resource Utilization** | CPU (< 80%), RAM/JVM GC (< 85%), DB Connection Pool (< 80%), I/O | `tools/report/telemetry_correlator.py` |
| **Capacity** | Maximum Concurrency Envelope & Degradation Cliff without crash | `tools/contrib/generate_jmx_plan.py` |

---

## 3. SRE Non-Functional Requirements & SLA/SLO Budgets

- **Service Level Indicator (SLI):** Percentiles calculated on steady-state traffic (excluding warm-up/cool-down transients).
- **Service Level Objective (SLO):**
  - **P95 Latency:** $\le 500\text{ms}$ (Warning at $400\text{ms}$)
  - **P99 Latency:** $\le 1000\text{ms}$
  - **Max Allowable Error Rate:** $< 1.0\%$ (HTTP 5xx, timeouts, connection drops)
  - **Throughput Budget:** $\ge [Target]\text{ RPS}$ under normal peak load
- **Service Level Agreement (SLA Gate):** Automated pipeline halt (Exit Code 1) if P95 breaches $500\text{ms}$ or error rate $\ge 1.0\%$.

---

## 4. Operational Profile & Workload Modeling (ISTQB CT-PT)

- **Traffic Distribution (Pareto 70/20/10 Rule):**
  - High-frequency browsing / querying (Read): `70%`
  - Mutation / Transactional creation (Write): `20%`
  - Complex aggregation / Reporting (Heavy): `10%`
- **User Behavior & Pacing:**
  - **Realistic Think-Time:** Uniform Random Timers `1,000ms – 5,000ms` (Zero think-time is strictly forbidden).
  - **Traffic Model:** Open Arrival-Rate (`ramping-arrival-rate` / throughput pacing) for public web APIs; Concurrency VU pool for private employee portals.
  - **Session Isolation:** Pre-seeded user pools (`users.csv` or `userPool SharedArray`) with dedicated auth tokens per VU.

---

## 5. Workload Archetypes & Execution Schedule

| # | Archetype | Target Concurrency / Rate | Duration | Objective / Risk Addressed |
|---|:---|:---|:---|:---|
| **1** | **Smoke Test** | 1 – 5 VUs | 2 min | Pre-flight sanity check & endpoint reachability. |
| **2** | **Average Load Test** | 50 – 200 VUs | 15 – 30 min | Verify SLA compliance under expected peak volume. |
| **3** | **Stress Test (Step-Up)**| 200 $\rightarrow$ 2,000 VUs | 30 – 45 min | Locate degradation cliff, saturation knee & recovery. |
| **4** | **Spike Test** | 10 $\rightarrow$ 1,000 VUs | 5 – 10 min | Test autoscaling speed & circuit breaker recovery. |
| **5** | **Soak / Endurance** | 50 – 100 VUs | 2 – 12 hours | Uncover JVM memory leaks, GC pauses, connection leaks. |
| **6** | **Scalability Test** | 50 $\rightarrow$ 100 $\rightarrow$ 200 VUs | 30 – 60 min | Verify linear scale-up / scale-out elasticity ($\ge 80\%$). |

---

## 6. Test Environment Topology & SPEC/TPC Disclosure

- **Hardware & Host Specification:**
  - Application Server: `[e.g., 4 vCPU, 16GB RAM, Linux Kernel 5.15]`
  - Database Cluster: `[e.g., PostgreSQL 15, max_connections=200, pool_size=50]`
  - Network Bandwidth: `[e.g., 10 Gbps VPC / local internal virtual bridge]`
- **Steady-State Measurement Interval (TPC Standard):**
  - Warm-up Period: `[e.g., 3 minutes (excluded from SLA calculations)]`
  - Steady-State Window: `[e.g., 10 minutes (official evaluation window)]`
  - Cool-down Period: `[e.g., 2 minutes (excluded from SLA calculations)]`

---

## 7. Safety Gates, Pre-Flight Checks & Kill-Switch

- [ ] **Dedicated Isolated Environment:** Verified non-production target; staging approval granted.
- [ ] **Synthetic Test Data:** Parameterized with dynamic prefix `PERF_AUTO_${timestamp}_${thread}`.
- [ ] **Kill-Switch Threshold:** Configured `abortOnFail` if aggregate error rate $> 10\%$ over a 30s window.
- [ ] **Teardown & Cleanup Automation:** Reversible sandbox rollback (`reversible_sandbox.py`) scheduled post-test.

---

## 8. Telemetry, APM & Observability (OpenTelemetry)

- **Distributed Tracing Header:** Injected W3C Trace Context `traceparent` (`00-{trace_id}-{span_id}-01`).
- **Telemetry Streaming:** InfluxDB Backend Listener / Prometheus Node Exporter.
- **Root Cause Analysis (RCA):** Automated Pearson correlation matrix connecting tail latencies with CPU, Memory, and Database thread pools.

---

## 9. Definition of Done & Gate 10 Acceptance

- [ ] Test execution completed headlessly without manual browser GUI interference.
- [ ] Steady-state P95 latency is strictly below SLA budget.
- [ ] Error rate is strictly below 1.0% (0% on authentication & transaction routes).
- [ ] Zero database primary key collisions or lock contention from unparameterized test data.
- [ ] Artifacts generated and saved to `reports/perf/`: `perf_results.jtl` and `k6_summary.json`.
- [ ] Gate 10 DoD status: **PASSED (`python tools/core/verify_all.py --mode hub`)**.
