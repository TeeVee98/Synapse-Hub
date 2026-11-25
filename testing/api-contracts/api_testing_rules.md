---
trigger: on_demand
description: International API testing & performance reliability invariants for REST, OpenAPI, gRPC, and CDC contracts.
profiles: [api, perf, full]
---

# Enterprise API Testing & Performance Reliability Invariants

> **Scope:** Mandatory invariants for subagents `api-engineer` and `perf-engineer` when designing, executing, or auditing API suites (REST, OpenAPI, GraphQL, gRPC).  
> **International Standards Alignment:** Codifies Google SRE Four Golden Signals, Percentile Tail Latency (P50/P95/P99/P99.9), IETF RFC 9110/9112/9113, OpenAPI OAS 3.0/3.1, CNCF gRPC, and RFC 6585 Rate Limiting.

---

## 1. Google SRE Four Golden Signals for API Testing

1. **Latency (Separation of Success vs Error):**
   - Latency percentiles must be calculated **independently** for successful requests (`2xx`) versus failed requests (`4xx/5xx`).
   - *Invariant:* Never allow rapid HTTP 500/502 responses (e.g. 5ms gateway rejection) to artificially depress overall average or P95 latency.
2. **Traffic (Throughput Accounting):**
   - All load generators must record aggregate and per-endpoint throughput in Requests Per Second (RPS) or Transactions Per Second (TPS).
3. **Errors (Explicit & Implicit Failure Guard):**
   - **Explicit Errors:** HTTP `4xx` and `5xx` status codes must be tracked against SLA error budgets.
   - **Implicit Errors (False 200s):** An HTTP `200 OK` returning an empty body `{}`, `null`, or an error payload (`{"code": 500}`) is classified as a critical defect. Tests must validate JSON Schema contracts.
4. **Saturation (Resource Headroom):**
   - Correlate API traffic with infrastructure utilization via `tools/report/telemetry_correlator.py`: CPU saturation ($> 85\%$), JVM heap/GC stalls ($> 90\%$), database connection pool exhaustion, and socket starvation.

---

## 2. Percentile Measurement Invariant (Absolute Ban on Average)

1. **Zero Average Headline:** Never use Average or Mean response times for acceptance sign-off.
2. **Mandatory Percentile Matrix:**
   - **P50 (Median):** Typical user experience benchmark.
   - **P95:** Standard commercial SLA baseline for peak traffic.
   - **P99 / P99.9 (Tail Latency):** Mandatory for financial, authentication, and distributed microservice call chains (*Google Tail at Scale*).

---

## 3. Tiered Industry SLA Benchmarks (NFR Reference Table)

When evaluating or generating API performance suites, apply the following tier-specific SLA budgets:

| Tier | API Category & Use Case | Target P95 Latency | Target P99 Latency | Max Error Rate |
| :---: | :--- | :---: | :---: | :---: |
| **Tier 1** | **Simple Read / Cached** (GET by ID, Session/Auth check, Ping) | $< 100\text{ms}$ | $< 200\text{ms}$ | $< 0.01\%$ |
| **Tier 2** | **Standard Business CRUD** (Indexed Search, User update, Entity create) | $< 500\text{ms}$ | $< 1,000\text{ms}$ | $< 0.1\%$ |
| **Tier 3** | **Complex Processing** (Payment checkout, Multi-table aggregation) | $< 2,000\text{ms}$ | $< 3,000\text{ms}$ | $< 0.1\%$ |
| **Tier 4** | **Async / Heavy Processing** (Report generation, Batch data import) | HTTP 202 in $< 200\text{ms}$ | $< 500\text{ms}$ | $< 0.01\%$ |

---

## 4. Technical Standards & Protocol Verification (IETF, OpenAPI, gRPC)

1. **IETF RFC 9110 / 9112 / 9113 (HTTP Semantics & HTTP/2, HTTP/3):**
   - Enforce HTTP Keep-Alive and connection pooling in load scripts.
   - Validate response compression (`Content-Encoding: gzip` or `br`) for JSON payloads $> 1\text{KB}$.
   - Verify Time To First Byte (TTFB) does not exceed $800\text{ms}$.
2. **OpenAPI Specification (OAS 3.0 / 3.1) & Contract Discipline:**
   - Treat OpenAPI specs as legally binding contracts: zero undeclared fields, no type shifting (`string` to `integer`), and no silent payload drift (`tools/api/api_drift_sentinel.py`).
   - Monitor payload sizes to prevent over-fetching (unnecessary entity fields causing bandwidth bottlenecks).
3. **gRPC & Protobuf Benchmarks (CNCF):**
   - Internal service-to-service RPCs must prioritize binary Protobuf serialization over JSON, targeting $5\times - 10\times$ lower latency (P99 $< 50\text{ms}$).

---

## 5. Architectural Guardrail Testing (Distributed Systems Resilience)

1. **Rate Limiting & Throttling (RFC 6585):**
   - When traffic exceeds configured rate limits, the API must return HTTP `429 Too Many Requests` with a valid `Retry-After` header. Crashing with `500` or `502` is a failure.
2. **Timeout & Circuit Breaker Pattern:**
   - Outbound calls to third-party or downstream microservices must enforce explicit connect/response timeouts ($3\text{s} - 5\text{s}$).
   - Under continuous downstream degradation, the circuit breaker must trip open (returning fast fallback or HTTP 503) to prevent gateway thread exhaustion.
3. **Database Connection Pool Saturation (HikariCP / pgpool):**
   - Stress testing must verify that database connections never exceed `max_connections` or trigger connection pool leak warnings. All data writes must execute idempotent teardown cleanup (`tools/heal/reversible_sandbox.py` and `tools/core/db_sandbox.py`).
