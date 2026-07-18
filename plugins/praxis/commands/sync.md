---
description: Update the CLAUDE.md hierarchy for recent changes, regression-verified.
argument-hint: "[optional: what changed]"
---

Use the `claudemd-living` skill.

Reconcile the root and nested CLAUDE.md files with the current code
${ARGUMENTS:+(context: $ARGUMENTS)}. Pick the right scope per change, draft minimal
edits, and verify them with `claudemd_check.py` plus `@praxis:claudemd-verifier` so
no still-valid instruction is lost or contradicted. Show the diff and the verifier
verdict before writing.
