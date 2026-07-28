---
description: "Update all of the project's living knowledge for recent changes: /docs, CHANGELOG, ADRs, and the CLAUDE.md hierarchy."
argument-hint: "[optional: what changed]"
---

Reconcile every piece of the project's knowledge with the current code
${ARGUMENTS:+(context: $ARGUMENTS)}. Start from what is already there: read before
writing, and never drop still-valid content.

1. **Find the drift first.** Run
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/drift.py"`. It reports docs that
   contradict the live configuration (the classic case: a doc still says a human
   merges every PR long after this repo turned auto-merge on) and references that
   no longer resolve. Every finding is in scope for this command.
2. **`/docs`, `CHANGELOG.md`, ADRs** with the `docs-living` skill: update or create
   the right documents, add a `[Unreleased]` changelog entry, record an ADR for any
   significant or autonomously-taken decision, and keep `docs/README.md` indexed.
   Scaffold `/docs` or `CHANGELOG.md` if the repo lacks them.
3. **The CLAUDE.md hierarchy** with the `claudemd-living` skill whenever a
   convention, command, dependency, or architectural pattern moved. Pick the right
   file for each change, draft minimal edits, and verify them with
   `claudemd_check.py` plus `@praxis:claudemd-verifier` so nothing still valid is
   lost or contradicted. Show the diff and the verifier verdict before writing.

Prefer stating configurable behaviour as configurable ("with auto-merge off,
praxis stops at the PR") rather than as a constant. A sentence that asserts one
side of a toggle is drift waiting to happen.

