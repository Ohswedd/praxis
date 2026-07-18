---
description: Run the full praxis quality rubric on the current change (vertical + horizontal).
argument-hint: "[optional scope, e.g. a path or 'staged']"
---

Use the `quality-rubric` skill now.

Scope the current change ${ARGUMENTS:+(focus: $ARGUMENTS)}, dispatch every vertical
auditor (doc-reference, duplication, regression, adversarial, edge-case,
performance), run the horizontal consistency pass, fix every FAIL and re-run the
affected auditor, and record the green quality report when all passes are green.
Prioritise thoroughness over speed. Present a compact verdict table at the end.
