# 3. Make the green quality report evidence-backed

- Status: accepted
- Date: 2026-07-16

## Context
The Stop gate accepted a "green" report if it existed and matched the change
signature — it trusted that the audit and tests had actually passed. For a tool
that gates "done", that trust was the weakest link (noted in ADR-0001 and the
self-audit).

## Decision
Record the report with evidence via `report.py`: the test command, its observed
exit code, and per-vertical verdicts. The gate requires, when the repo has a
detectable test command, that the report shows a passing run (`test_exit == 0`);
otherwise the report is not accepted and the session keeps working. Repos with no
tests are handled gracefully (no test requirement, with a note about missing
coverage).

## Consequences
- Positive: "green" is now backed by a real, recorded test result rather than a
  promise; failing tests can't satisfy the gate.
- Positive: exposed and fixed a signature bug (state dir perturbing the signature).
- Negative: still not a cryptographic proof the exact recorded exit code came from
  a real run in this session; the deterministic scans remain the backstops. Full
  proof was judged disproportionate (see ROADMAP for coverage-aware regression).

## Alternatives considered
Executing tests inside the hook (rejected — Stop hooks shouldn't run long/mutating
commands, and it couldn't know the right per-package command reliably) and leaving
the report trust-based (rejected — the whole point of v1.0 is to close this gap).
