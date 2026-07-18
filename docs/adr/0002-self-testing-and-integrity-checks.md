# 2. Ship a test suite and a self-integrity check

- Status: accepted
- Date: 2026-07-16

## Context
Praxis enforces "no regression" and "completeness" on the projects it manages, but
until v0.7.0 it validated itself only with ad-hoc manual checks. A tool that
demands rigor must demonstrate it, and enterprise adopters expect CI-verified
integrity.

## Decision
Add a stdlib-only `tests/` suite (unittest) that exercises the deterministic core
by running the scripts as subprocesses, plus a `selfcheck.py` that validates the
plugin's structural integrity (manifests, version agreement, hook→script
references, frontmatter, compilation). Both run in CI on every push, and
`selfcheck` is surfaced in `/praxis:doctor`.

## Consequences
- Positive: regressions in the guards, gate, and helpers are caught automatically;
  the plugin can't ship with a broken manifest or a dangling hook reference.
- Negative: contributors must keep tests green (documented in CONTRIBUTING.md).

## Alternatives considered
Relying on manual verification (rejected — not repeatable) and adding pytest
(rejected — would introduce a third-party dependency, against the stdlib-only
rule).
