# Example: Walking the Ladder for a Real Request

Request: "In the login test suite, when login fails we need a readable message that includes the actual error returned by the app."

## Descent

| Rung | Checked | Result |
|:---:|---|---|
| 0 | Does it need to exist? | Yes — failure messages currently say only `Login failed`, which hides the app's actual error. Core job: include the returned error text. |
| 1 | Already in the codebase? | YES — the login Page Class already builds an error context object with the app message; the assertion just never prints it. |
| 2-4 | stdlib / platform / dependency | Not needed — rung 1 already solves it. |
| 5-6 | One line / minimum | The fix becomes a one-line assertion change reusing the existing context object. |

## Lean diff (the whole change)

```text
- expect(page).toHaveText('Login failed');
+ expect(page).toHaveText(`Login failed: ${errorContext.message}`);
```

Plus the completeness rule: one new test asserts the message embeds the app
error for a rejected-credentials fixture, so the non-trivial path is covered.

## Anti-example (what the ladder forbids)

```text
+ class RetryableErrorContextFormatterFactory { ... }   // Rung 0 violation
+ npm install fancy-string-utils                        // Rung 4 violation
+ config option: errorMessageTemplateStyle: 'verbose' | 'compact'  // nobody asked
```

## Never-cut check (Rung floor)

The shorter assertion still validates at the trust boundary (the app's
returned error is rendered before being asserted), leaks no credentials into
the failure message, and the fixture error text is sanitized synthetic data.
Leanness changed the size of the diff, not the safety of the test.
