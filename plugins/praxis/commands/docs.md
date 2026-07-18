---
description: Update the project's living knowledge (/docs, CHANGELOG, ADRs) for recent changes.
argument-hint: "[optional: what changed]"
---

Use the `docs-living` skill.

Reconcile the `/docs` tree, `CHANGELOG.md`, and ADRs with the current code
${ARGUMENTS:+(context: $ARGUMENTS)}. Read the existing docs first, then update or
create the right ones (no regression — don't drop still-valid content), add a
`[Unreleased]` changelog entry, and record an ADR for any significant or autonomous
decision. Keep `docs/README.md` indexed; scaffold `/docs` or `CHANGELOG.md` if
missing.
