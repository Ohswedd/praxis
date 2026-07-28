---
description: Audit the current change with the full quality rubric, or the whole repository with "repo".
argument-hint: "[ blank = current change | repo | <path> | repo --report-only ]"
---

Two scopes, one command. Read `${ARGUMENTS}` and pick:

**Blank, `staged`, or a narrow focus** goes to the `quality-rubric` skill on the
current change. Scope it with `scope.py` (never `git diff` alone: on a branch
that has committed anything it is empty), then dispatch every vertical auditor
(doc-reference,
duplication, regression, adversarial, edge-case, performance, completeness, plus
accessibility and design-consistency whenever the change touches user-facing
surface) and the horizontal consistency pass. Fix every FAIL, re-run the affected
auditor, and record the green report once all pass. End with a compact verdict
table.

**`repo`, `all`, or a path** goes to the `repo-audit` skill over the whole
codebase or that subtree. Run the full pipeline: inventory and shard ledger
(`repo_scan.py init`), starting report, forward audit of every shard against every
vertical dimension, reverse audit of each finding via `@praxis:finding-verifier`,
fixes applied in audited change-sets (defer architectural and breaking items with
a remediation plan; `--report-only` skips fixing entirely), then the
coverage-honest final report and the living-knowledge updates.

Coverage comes from the ledger, not from memory: no shard skipped, no dimension
sampled, no finding acted on unverified, and any gap stated explicitly.
