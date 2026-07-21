# 10. The quality report runs the tests itself

- Status: accepted
- Date: 2026-07-21

## Context
ADR 0003 made the report evidence-backed by recording a test command and exit code, but the exit code was supplied by the caller via --tests-exit. A claim is not evidence: an unverified 'green' report satisfied the Stop gate and closed the loop on a change whose tests had never been run — the mechanism behind regressions surviving a supposedly green audit.

## Decision
report.py executes the test command itself, records the real exit code plus a test_verified flag and a failing run's output tail. The gate rejects any report lacking a verified run when the repo has a detectable test command — including pre-1.5 reports, which are not grandfathered. --tests-exit is still accepted so existing invocations do not break, but it is ignored and says so.

Executing the command opened three further holes, all closed here: a substituted command (`--tests true`, `pytest || true`) is recorded as such and does not satisfy the gate on its own, since running *a* command proves nothing; a report with no vertical verdicts is 'fail' rather than vacuously green; and a `--tests` value naming a sensitive path is refused, so report.py cannot become the clean path around guard_paths. The run itself is bounded properly — its own process group, killed as a tree on timeout, output streamed to a temp file rather than buffered in memory — and secrets in the persisted output tail are redacted.

## Consequences
A green report cannot be asserted, only earned. ADR 0003 rejected running tests inside the Stop hook because hooks should not run long or mutating commands; that reasoning still holds — the tests run in report.py, a CLI the model invokes deliberately, not in the hook. Recording a report now takes as long as the suite, bounded by a 900s default timeout (--timeout to override). report.py also stopped failing open: a crash there used to exit 0, implying a report that was never written.
