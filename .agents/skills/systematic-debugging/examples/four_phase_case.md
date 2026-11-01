# Example: Four-Phase Investigation of a Timeout Failure

Symptom: `TC-220_ExportReport` fails intermittently with
`TimeoutError: waiting for selector '.export-toast'` after 30s.

## Phase 1 — Root Cause Investigation (NO fixes yet)

- Read the full stack trace: timeout is on the toast selector, not the
  export click itself.
- Reproduce: fails ~1 in 5 runs on large datasets; never on small ones.
  Evidence-gathering, not guessing: the dataset-size correlation is recorded.
- Recent changes: export endpoint moved to a queued job last sprint
  (git log).
- Component-boundary check (run once): UI click reaches the API (201 logged);
  API enqueues the job (job row appears); job worker completes in 8-45s
  depending on dataset size. The UI waits a fixed 30s. Which layer breaks?
  The assumption "export finishes quickly" — not any single component.

## Phase 2 — Pattern Analysis

- Working example: the import flow already polls a job-status endpoint with
  a completion condition instead of waiting on a fixed toast timeout.
- Difference list: export flow waits on a UI toast; import flow polls the
  job resource with a condition. One difference, however small it looks.

## Phase 3 — Hypothesis

> "The failure is caused by waiting on a time-bounded UI toast instead of
> polling the export job status; large datasets exceed the toast window."

Minimal test: poll the job endpoint until `state == 'done'` (condition-based
wait) on the large dataset, 10 consecutive runs. No other change.

## Phase 4 — Implementation

1. RED test: large-dataset export asserts on the polled job state — fails
   against the toast-wait implementation (reproduces the defect honestly).
2. Single fix: replace the toast wait with the condition-based job poll,
   mirroring the import flow pattern. Toast assertion kept as a secondary
   visible-feedback check (never cut existing validation).
3. Verify: RED test passes; full project suite re-run — output quoted in
   the report; lessons recorded via `tools/cache_resolver.py record-lesson`.
4. Anti-pattern rejected: bumping the timeout to 90s would have hidden the
   root cause and broken the small-dataset UX latency signal.
