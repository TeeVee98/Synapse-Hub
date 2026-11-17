# Example: Surgical Change vs Scope Creep

Request: "The `verifyKPI` step in the report test is flaky because it asserts on a live-computed percentage; make it deterministic."

## GOOD — every line traces to the request

```text
Changed:
- tests/TC-305_ExportReport: replace live percentage comparison with a
  fixture-backed expected value passed via test data.
- Test data: add deterministic expected KPI values for the report fixture.

Removed (orphans of this change):
- unused import of the random helper previously used for sample values.
```

Why it passes: two touched files, both directly required by the request; the
orphan removed was created by this very change.

## BAD — scope creep

```text
Changed:
- tests/TC-305_ExportReport: deterministic assertion (requested)
- tests/TC-118_Login: "improved" waiting strategy while passing by
- page objects: reformatted indentation and reworded comments
- tools/distill_log.py: renamed a variable that "looked confusing"
```

Why it fails the Surgical Changes test:
- TC-118 was not part of the request — a drive-by change hides risk inside an
  unrelated diff.
- Comment/formatting rewrites bloat the diff and bury the actual fix in review.
- Renaming inside a hub tool was not requested; pre-existing code is left
  alone and mentioned in the report instead.

## Assumption surfacing (Think Before Coding)

Before implementing, the GOOD flow states:

> "Assumption: the fixture data can express the expected KPI as an exact value.
> If the report computes values the fixture cannot predict, I will need a
> fixture extension — confirming before I change the test data schema."

The BAD flow silently assumes the fixture is sufficient and discovers the
schema gap after the diff is already written.
