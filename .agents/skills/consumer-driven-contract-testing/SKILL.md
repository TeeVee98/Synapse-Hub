---
name: consumer-driven-contract-testing
description: "Standardize Consumer-Driven Contract (CDC) testing with Pact and OpenAPI Bidirectional Contract Testing. Detect and prevent breaking schema changes, payload drift, and microservice integration failures."
---

# Consumer-Driven Contract (CDC) Testing — Schema Drift & Integration Sentinel

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee998)** (<https://github.com/TeeVee998/Synapse-Hub>) under the MIT License.

---

## 1. Overview & Architecture

Consumer-Driven Contract (CDC) Testing shifts integration verification left by formalizing expectations between API consumers (Web/Mobile frontends, backend BFFs) and API providers (microservices) into explicit, machine-readable contracts.

Instead of relying on fragile, slow, and expensive multi-service end-to-end environments, CDC enables isolated testing:
1. **Consumer Tests:** The consumer defines its exact expectation contract (HTTP method, headers, request body, response schema, status code) against a mock provider. A signed Pact file (`.json`) or OpenAPI specification is generated.
2. **Contract Broker:** The contract is published to the Pact Broker / Contract Ledger with semantic versioning.
3. **Provider Verification:** The provider independently replays all registered consumer contracts against its live endpoints (or generated stubs) in CI/CD without needing any running consumers.
4. **Deploy Gate (`can-i-deploy`):** Verifies that both consumer and provider versions are compatible before promoting artifacts to staging or production.

```mermaid
flowchart LR
    subgraph Consumer_CI ["1. Consumer Pipeline"]
        CT["Consumer Test"] -->|Record expectations| MockProv["Pact Mock Server"]
        MockProv -->|Generate| Contract["pact-contract.json"]
        Contract -->|Publish| Broker[("Pact Broker / Contract Ledger")]
    end

    subgraph Provider_CI ["2. Provider Pipeline"]
        Broker -->|Fetch contracts| Verifier["Pact Verifier / OpenAPI Diff"]
        Verifier -->|Replay requests| RealProv["Provider Microservice"]
        RealProv -->|Verification results| Broker
    end

    subgraph Release_Gate ["3. Promotion Gate"]
        Broker -->|can-i-deploy| Gate{"Compatible?"}
        Gate -->|Yes| Deploy["Deploy to Production"]
        Gate -->|No (Breaking Drift)| Block["Block Release & Alert"]
    end
```

---

## 2. Bi-Directional Contract Testing (BDCT) & OpenAPI Diffing

In bi-directional contract testing, consumers use mock fixtures or recorded network HAR traffic, while providers supply their authoritative OpenAPI 3.0/3.1 specification. The engine executes automated schema diffing:

### Breaking Changes Checklist (Strictly Blocked by Gatekeeper):
- ❌ **Removing an existing field** that any consumer contract depends on.
- ❌ **Adding a new mandatory (`required`) field** to a request body without a default value.
- ❌ **Mutating property data types** (e.g., `id: string` changed to `id: integer`, or `amount: number` to `amount: string`).
- ❌ **Narrowing enum values** (removing an enum value that consumers submit or expect).
- ❌ **Altering response status codes** (e.g., changing HTTP 201 Created to HTTP 200 OK without consumer migration).
- ❌ **Tightening validation rules** (e.g., lowering `maxLength` below existing consumer field lengths).

### Non-Breaking Changes (Permitted):
- ✅ Adding optional fields (`required: false`) to response bodies.
- ✅ Adding new endpoints without touching existing routes.
- ✅ Loosening validation rules (e.g., increasing `maxLength` or expanding enum options).

---

## 3. Consumer Contract Authoring Standards (Clean POM & Pact DSL)

Consumer contracts must use flexible matchers rather than hardcoded static payloads to prevent flakiness:

### TypeScript / Playwright Pact Pattern:
```typescript
import { PactV3, MatchersV3 } from '@pact-foundation/pact';

const { like, regex, integer, eachLike } = MatchersV3;

const provider = new PactV3({
  consumer: 'SynapseWebFrontend',
  provider: 'OrderService',
  dir: './pacts'
});

describe('Order Service CDC Suite', () => {
  it('validates order creation contract', async () => {
    await provider
      .uponReceiving('a request to create a new order')
      .withRequest({
        method: 'POST',
        path: '/api/v1/orders',
        headers: { 'Content-Type': 'application/json', 'Authorization': regex('Bearer .+') },
        body: {
          customerId: like('CUST_1001'),
          items: eachLike({
            sku: regex('^[A-Z0-9_-]{3,20}$', 'SKU_ITEM_01'),
            quantity: integer(1),
            price: like(49.99)
          })
        }
      })
      .willRespondWith({
        status: 201,
        headers: { 'Content-Type': 'application/json' },
        body: {
          orderId: regex('^ORD-[0-9]{8}$', 'ORD-20261106'),
          status: regex('^(PENDING|CONFIRMED)$', 'CONFIRMED'),
          createdAt: like('2026-11-06T10:00:00Z')
        }
      })
      .executeTest(async (mockserver) => {
        const client = new OrderApiClient(mockserver.url);
        const response = await client.createOrder({ ... });
        expect(response.status).toBe('CONFIRMED');
      });
  });
});
```

---

## 4. Provider Verification Protocol

Providers verify all active consumer contracts against their test instances:

```bash
# Verify provider implementation against contracts registered in broker
pact-verifier \
  --provider-base-url="http://localhost:8080" \
  --pact-broker-url="https://broker.synapse-qa.internal" \
  --provider="OrderService" \
  --publish-verification-results \
  --provider-app-version="3.2.0" \
  --provider-version-branch="main"
```

---

## 5. Automated CI/CD Deployment Verification (`can-i-deploy`)

Before triggering deployment in CI/CD, the release pipeline invokes the compatibility ledger:

```bash
# Enforce deployment gatekeeper
pact-broker can-i-deploy \
  --pact-broker-url="https://broker.synapse-qa.internal" \
  --pacticipant="SynapseWebFrontend" \
  --version="3.2.0" \
  --to-environment="production"
```

If any contract is unverified or broken, the command exits with non-zero code, blocking deployment and preventing live customer-facing API outages.
