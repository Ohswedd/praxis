---
description: Run the full praxis quality rubric on the current change (vertical + horizontal).
argument-hint: "[optional scope, e.g. a path or 'staged']"
---

Use the `quality-rubric` skill.

Scope the current change ${ARGUMENTS:+(focus: $ARGUMENTS)} and dispatch every
vertical auditor (doc-reference, duplication, regression, adversarial, edge-case,
performance, completeness) plus the horizontal consistency pass. Fix every FAIL,
re-run the affected auditor, and record the green report once all pass. End with a
compact verdict table.
