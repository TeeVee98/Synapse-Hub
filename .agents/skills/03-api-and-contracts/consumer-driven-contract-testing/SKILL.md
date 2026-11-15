---
name: consumer-driven-contract-testing
description: "Standardize Consumer-Driven Contract (CDC) testing with Pact and OpenAPI Bidirectional Contract Testing. Detect and prevent breaking schema changes, payload drift, and microservice integration failures. Use when implementing contract testing, verifying CDC providers, or preventing breaking API schema changes."
category: verification_and_resilience
version: "3.2.0"
policies:
  network: localhost-only
  shell: workspace-sandbox
  filesystem: workspace-sandbox
---
# Consumer-Driven Contract (CDC) Testing — Schema Drift & Integration Sentinel

> **Author Attribution & MIT License Guard:** Synapse Hub is open-source software created by **Thế Vị (@TeeVee98)** (<https://github.com/TeeVee98/Synapse-Hub>) under the MIT License.

---

## 1. Trigger & Activation

- **Trigger Clause:** Use when implementing consumer-driven contract testing, verifying microservice API provider implementations, validating bidirectional contracts (BDCT), or preventing breaking API schema changes before deployment.
- **Activation Scope:**
  - Microservice integration boundaries where frontend (Web/Mobile) or BFF consumers interface with backend services.
  - Multi-repo or monorepo environments maintaining OpenAPI 3.0/3.1 specifications or Pact contract ledgers.
  - Pre-deployment CI/CD pipelines executing compatibility promotion gates (`can-i-deploy`).

---

## 2. Non-Goals & Boundary Constraints

- **What NOT to do:**
  - Do NOT use CDC testing as a substitute for unit tests or deep domain business logic validation.
  - Do NOT hardcode non-hermetic, unresolvable internal domains (e.g. `https://broker.synapse-qa.internal`); use hermetic local brokers (`http://localhost:1234` or mock server instances).
  - Do NOT use lazy ellipsis or truncation (`{ ... }`) in contract payloads; define explicit, valid request and response bodies.
  - Do NOT execute active network requests outside `localhost` in restricted environments.
- **Sibling Skill Boundaries:**
  - `api-spec-to-e2e-matrix`: Focuses on compiling comprehensive functional E2E test matrices from OpenAPI specs.
  - `api-network-mocking-interception`: Focuses on client-side route stubbing and chaos fault injection within browser test runners.
  - `consumer-driven-contract-testing` (this skill): Owns consumer expectations, broker publishing, provider verification, and deployment gatekeeping.

---

## 3. Ordered Execution Workflow

### Phase 1: Architecture & Contract Invariants

Consumer-Driven Contract (CDC) Testing shifts integration verification left by formalizing expectations between API consumers and API providers into explicit, machine-readable contracts.

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

### Phase 2: Bi-Directional Contract Testing (BDCT) & Breaking Change Rules

The contract verifier executes automated schema diffing against the provider's authoritative specification:

#### Breaking Changes Checklist (Strictly Blocked by Gatekeeper):
- ❌ **Removing an existing field** that any consumer contract depends on.
- ❌ **Adding a new mandatory (`required`) field** to a request body without a default value.
- ❌ **Mutating property data types** (e.g., `id: string` changed to `id: integer`, or `amount: number` to `amount: string`).
- ❌ **Narrowing enum values** (removing an enum value that consumers submit or expect).
- ❌ **Altering response status codes** (e.g., changing HTTP 201 Created to HTTP 200 OK without consumer migration).
- ❌ **Tightening validation rules** (e.g., lowering `maxLength` below existing consumer field lengths).

#### Non-Breaking Changes (Permitted):
- ✅ Adding optional fields (`required: false`) to response bodies.
- ✅ Adding new endpoints without touching existing routes.
- ✅ Loosening validation rules (e.g., increasing `maxLength` or expanding enum options).

### Phase 3: Consumer Contract Authoring (TypeScript / Pact DSL)

Consumer contracts must use flexible matchers rather than hardcoded static values to prevent flakiness:

<!-- classification: illustrative -->
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
        // Native fetch client implementation with hermetic mock provider target
        const response = await fetch(`${mockserver.url}/api/v1/orders`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-contract-token',
          },
          body: JSON.stringify({
            customerId: 'CUST_1001',
            items: [
              { sku: 'SKU_ITEM_01', quantity: 1, price: 49.99 }
            ]
          }),
        });
        const data = await response.json();
        expect(response.status).toBe(201);
        expect(data.status).toBe('CONFIRMED');
      });
  });
});
```

### Phase 4: Provider Verification Protocol

Providers verify all registered consumer contracts against their local test instances:

<!-- classification: illustrative -->
```bash
# Verify provider implementation against contracts registered in local mock/broker
pact-verifier \
  --provider-base-url="http://localhost:8080" \
  --pact-broker-url="http://localhost:1234" \
  --provider="OrderService" \
  --publish-verification-results \
  --provider-app-version="3.2.0" \
  --provider-version-branch="main"
```

### Phase 5: Automated CI/CD Deployment Verification (`can-i-deploy`)

Before triggering promotion in CI/CD, the release pipeline invokes the compatibility ledger:

<!-- classification: illustrative -->
```bash
# Enforce deployment gatekeeper against hermetic broker
pact-broker can-i-deploy \
  --pact-broker-url="http://localhost:1234" \
  --pacticipant="SynapseWebFrontend" \
  --version="3.2.0" \
  --to-environment="production"
```

---

## 4. Verification Points & DoD

1. **Consumer Contract Generation:** Pact contract file (`pacts/*.json`) is generated and contains valid JSON with no missing fields or unresolved `{ ... }` truncations.
2. **Schema Conformance:** Consumer expectation matches provider OpenAPI schema with 0 breaking change violations.
3. **Hermetic Target Validation:** Broker and provider URLs point to localhost or hermetic mock addresses, never unresolvable internal domains.
4. **Deploy Gate Check:** `can-i-deploy` verification exits with code 0 before promotion.

---

## 5. Handoff Protocol

- **Deliverables:**
  - Signed Pact contract JSON (`pacts/<consumer>-<provider>.json`).
  - OpenAPI verification report and breaking changes diff summary.
- **Next Subagent:** Pass contract artifacts to `api-engineer` for provider stub generation or `quality-gatekeeper` for CI/CD promotion gate clearance.
- **Output Format:** Machine-readable JSON contract with SemVer compatibility tag.
