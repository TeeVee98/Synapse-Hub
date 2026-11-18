---
name: api-design
description: >
  RESTful API design and contract testing skill: define resource schemas, HTTP
  method semantics, status code conventions, versioning, and OpenAPI 3.1 contracts.
  Use when designing a new API endpoint, reviewing an existing API, or implementing
  consumer-driven contract tests.
version: 1.0.0
attribution: Adapted from ECC (affaan-m/ecc, Apache 2.0). Extended by Thế Vị (@TeeVee98).
---

# API Design Skill (`api-design`)

## Overview

Well-designed APIs are **stable contracts** between producers and consumers. This skill enforces RESTful naming conventions, correct HTTP semantics, proper status code usage, and consumer-driven contract testing to prevent breaking changes.

> [!IMPORTANT]
> Never change a published API response schema without versioning. Breaking changes
> in an unversioned endpoint are a production incident, not a "minor fix."

## When to Activate

- Designing a new REST endpoint from scratch.
- Reviewing an existing endpoint for HTTP semantic correctness.
- Writing Pact/OpenAPI contract tests for a producer-consumer pair.
- Versioning an API that has breaking schema changes.

## HTTP Method Semantics

| Method | Idempotent | Safe | Use For |
|--------|-----------|------|---------|
| GET | ✅ | ✅ | Retrieve resource(s) — never mutate |
| POST | ❌ | ❌ | Create new resource or trigger action |
| PUT | ✅ | ❌ | Full replace of resource (complete representation) |
| PATCH | ❌ | ❌ | Partial update (only specified fields) |
| DELETE | ✅ | ❌ | Remove resource |

## Status Code Conventions

```
200 OK           — Successful read (GET) or update (PUT/PATCH with response body)
201 Created      — Successful creation (POST); include Location header
204 No Content   — Successful deletion or update with no response body
400 Bad Request  — Client sent invalid input (include error schema in body)
401 Unauthorized — Missing or invalid authentication credentials
403 Forbidden    — Authenticated but not authorized for this resource
404 Not Found    — Resource does not exist (never 200 with empty body)
409 Conflict     — State conflict (e.g. duplicate creation, optimistic lock failure)
422 Unprocessable — Validation error on semantically correct but invalid data
429 Too Many Requests — Rate limit exceeded (include Retry-After header)
500 Internal Server Error — Unexpected server failure (never expose stack traces)
```

## URL Design Rules

```
✅ /api/v1/users              — collection
✅ /api/v1/users/{id}         — single resource
✅ /api/v1/users/{id}/orders  — sub-resource collection
✅ /api/v1/orders?status=open — filtering via query params

❌ /api/v1/getUser            — verb in path (use GET + /users/{id})
❌ /api/v1/users/create       — action in path (use POST + /users)
❌ /api/v1/Users              — PascalCase (use kebab-case or snake_case)
```

## OpenAPI 3.1 Contract Template

```yaml
# openapi/users.yaml
openapi: "3.1.0"
info:
  title: Users API
  version: "1.0.0"
paths:
  /users/{id}:
    get:
      summary: Get user by ID
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string, format: uuid }
      responses:
        "200":
          description: User found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/User"
        "404":
          description: User not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ErrorResponse"
components:
  schemas:
    User:
      type: object
      required: [id, email, created_at]
      properties:
        id: { type: string, format: uuid }
        email: { type: string, format: email }
        created_at: { type: string, format: date-time }
    ErrorResponse:
      type: object
      required: [error, message]
      properties:
        error: { type: string }
        message: { type: string }
```

## Versioning Strategy

Synapse Hub mandates **URI versioning** (`/api/v1/`, `/api/v2/`):

1. Never break a `v1` contract — add `v2` for incompatible changes.
2. Run `v1` and `v2` in parallel for a minimum 6-month deprecation window.
3. Announce deprecation via `Deprecation` and `Sunset` response headers.

## Contract Testing with Pact

```python
# tests/api/test_users_contract.py — Consumer-driven contract test
# Run via: pytest tests/api/test_users_contract.py
import pytest

def test_get_user_contract(pact_session):
    pact_session.given("user 'abc-123' exists").upon_receiving(
        "a request for user abc-123"
    ).with_request(method="GET", path="/api/v1/users/abc-123").will_respond_with(
        status=200,
        body={"id": "abc-123", "email": "test@example.com"},
    )
    with pact_session:
        response = api_client.get("/api/v1/users/abc-123")
        assert response.status_code == 200
        assert "email" in response.json()
```

## Non-Goals

- Do not design GraphQL schemas under this skill (use a dedicated GraphQL design skill).
- Do not use `GET` for operations with side effects.
- Do not expose internal database IDs — use UUID or opaque token identifiers.
