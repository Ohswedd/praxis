---
description: Update the project's living knowledge (/docs, CHANGELOG, ADRs) for recent changes.
argument-hint: "[optional: what changed]"
---

Use the `docs-living` skill.

Reconcile the project's `/docs` tree, `CHANGELOG.md`, and ADRs with the current
state of the code ${ARGUMENTS:+(context: $ARGUMENTS)}. Read and search the existing
docs first, then update or create the right ones (no regression — don't drop
still-valid content), add a `[Unreleased]` changelog entry, and record an ADR for
any significant or autonomously-taken decision. Keep `docs/README.md` indexed.
If `/docs` or `CHANGELOG.md` is missing, scaffold them.
