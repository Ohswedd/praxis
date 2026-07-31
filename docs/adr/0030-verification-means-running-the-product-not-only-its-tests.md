# 30. Verification means running the product, not only its tests

- Status: accepted
- Date: 2026-07-31

## Context
praxis could prove that a test suite passed and nothing else. A green unit suite says a function returns what its test expects; it does not say the page renders, the route answers, the migration applies, or the command exits zero, and that gap is where a change passes every check and is still broken for the person using it. Users reported exactly this: work declared done that had never been exercised.

## Decision
common.detect_runtime_command finds the end-to-end harness a project already has (an e2e script in package.json, a Playwright or Cypress config). report.py runs it when the change touches user-facing files and records the real exit code, exactly as it does for the tests, gated by gate.require_runtime. The runtime-verification skill covers the rest: what running it means per project shape, driving a real browser through the Chrome tools when available, choosing Playwright when a harness must be added, and what may not be added to a repository that is not ours.

## Consequences
A user-facing change in a project with a harness now pays for an e2e run at record time, which is the cost of the guarantee. A project with no harness gets a stated gap and an instruction to verify by hand and report what was exercised, rather than an invented command or a dependency nobody agreed to. Detection covers the harnesses with one documented invocation; anything else has to be named with --runtime, which is honest about the limit rather than guessing at a command that could do anything.
