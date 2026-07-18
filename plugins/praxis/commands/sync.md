---
description: Update the CLAUDE.md hierarchy for recent changes, regression-verified.
argument-hint: "[optional: what changed]"
---

Use the `claudemd-living` skill.

Reconcile the root and nested CLAUDE.md files with the current state of the code
${ARGUMENTS:+(context: $ARGUMENTS)}. Pick the correct scope for each change, draft
minimal edits, verify them with `claudemd_check.py` plus `@praxis:claudemd-verifier`
so no still-valid instruction is lost or contradicted, then show the diff and the
verifier verdict before writing.
