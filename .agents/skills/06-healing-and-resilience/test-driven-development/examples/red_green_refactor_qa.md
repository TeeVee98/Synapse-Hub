# Example: RED-GREEN-REFACTOR for a Test Utility Retry Helper

Task: "Our Playwright API calls occasionally race the dev server; add retry
to the request helper."

## RED — write the failing test first

```typescript
test('retries a failing request up to 3 attempts then succeeds', async () => {
  let attempts = 0;
  const flakyCall = async () => {
    attempts += 1;
    if (attempts < 3) throw new Error('ECONNRESET');
    return { status: 200 };
  };

  const result = await requestWithRetry(flakyCall);

  expect(result.status).toBe(200);
  expect(attempts).toBe(3);
});
```

## Verify RED — MANDATORY

```text
$ npx vitest run tests/unit/retry.spec.ts
FAIL: requestWithRetry is not a function
```

Fails for the right reason: the feature does not exist yet. (An error like
"cannot read properties of undefined" would mean a typo — fix the test
before writing code.)

## GREEN — minimal implementation

```typescript
export async function requestWithRetry<T>(
  call: () => Promise<T>,
  maxAttempts = 3,
): Promise<T> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      return await call();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}
```

## Verify GREEN — MANDATORY

```text
$ npx vitest run tests/unit/retry.spec.ts
PASS 1/1
$ npm test            # the PROJECT suite, not just this file
PASS 214/214
```

A green single file is not a green suite — the project command is the
acceptance run, and its output is quoted in the report.

## REFACTOR — while green

No duplication to remove yet; the next failing test (e.g. "gives up after 3
attempts and rethrows") starts the next cycle. Adding exponential backoff NOW
would be speculative — nobody asked for it.

## Honesty check

- The test uses real behavior (a counting closure), not a mock asserting on
  itself.
- Gate 8 wiring: `tools/micro_mutator.py` inverts the attempt boundary — the
  test must survive the mutant (kill it), keeping Mutation Score >= 80%.
- `tools/infer_linter.py` finds both assertions present and meaningful.
