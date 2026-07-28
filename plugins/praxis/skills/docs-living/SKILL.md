---
name: docs-living
description: "Keep the project's /docs tree, CHANGELOG.md, and Architecture Decision Records (docs/adr/) alive and accurate. Use for EVERY change that adds, modifies, or removes behaviour, an API, a config, an architectural decision, or a workflow: read the relevant docs first, then update or create them, and record a changelog entry (and an ADR for significant/autonomous decisions). Also use to establish /docs when a repo lacks it. The project must always have a /docs; treat documentation as part of \"done\", never an afterthought."
---

# Living Docs

A project's `/docs`, its `CHANGELOG.md`, and its ADRs are its institutional
knowledge. Praxis keeps them **current with every change**, with the same
no-regression discipline it applies to code, so the knowledge never drifts or is
lost.

**Rule: every repo has a `/docs`. Documentation is part of "done".** A change is
not complete until the docs, changelog, and (where relevant) an ADR reflect it.

## The /docs contract
Expect and maintain this shape (create what's missing):

```
docs/
  README.md            index of the docs (what lives where)
  ARCHITECTURE.md      high-level design, components, data flow
  adr/                 Architecture Decision Records (NNNN-title.md)
  <domain>.md          per-subsystem/feature docs as needed
CHANGELOG.md           at the repo root (Keep a Changelog)
```

## Workflow for every change
1. **Read & search first.** Before editing, read the docs relevant to the area
   you're touching (grep `/docs` for the feature/module). Never write docs blind.
2. **Check for drift, then fix what you find.**
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/drift.py"
   ```
   It reports two things prose review reliably misses: documents that assert the
   opposite of the repo's live configuration, and references (a build command, a
   link, a slash command) that no longer resolve. Drift found while you are in
   these files is in scope for this change, not a separate errand.
3. **Update or create.** Reflect the change in the right doc: update an existing
   one, or create a new `docs/<topic>.md` if a new subsystem/feature appeared.
   Keep it accurate and concise; docs are read often.
4. **Never state configurable behaviour as a constant.** This is where docs rot
   fastest. "Praxis opens the PR and a human merges" is true only while
   `auto_merge` is off, and it survives, unread and wrong, for every session after
   someone flips it. Write the conditional ("with auto-merge off, praxis stops at
   the PR"), name the setting that decides, and point at the command that reports
   the live value.
5. **No regression.** Do not drop still-valid documentation. If you remove doc
   content, it must be because it's genuinely obsolete: say why. (Same discipline
   as the CLAUDE.md verifier.)
6. **Changelog entry (always).** Record the change under `[Unreleased]`:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/changelog.py" add --type <added|changed|fixed|removed|security|deprecated> "<concise description>"
   ```
   Map to Conventional Commits: feature→added, bugfix→fixed, breaking→changed/removed.
7. **ADR for significant or autonomous decisions.** When you make an architectural
   or non-obvious design decision, especially any decision taken autonomously in
   auto-pilot: persist it:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/adr.py" new "<decision title>" \
     --status accepted --context "..." --decision "..." --consequences "..."
   ```
   ADRs are a historical record: supersede one with a new ADR, never by rewriting
   what it originally said.
8. **Keep the index current.** Update `docs/README.md` when you add a doc.
9. **Re-run the drift check** before you call the docs done. It is the cheapest
   proof that this change did not introduce a new stale reference.

## Establishing /docs (new/legacy repos)
If `/docs` or `CHANGELOG.md` is missing, scaffold them (bootstrap does this):
create `docs/README.md`, `docs/ARCHITECTURE.md` (from what the repo-cartographer
found), an empty `docs/adr/`, and a Keep-a-Changelog `CHANGELOG.md`. Seed
`ARCHITECTURE.md` from the actual code, not assumptions.

## Definition of done for docs
- The touched behaviour/API/config is documented and accurate.
- `CHANGELOG.md` has an `[Unreleased]` entry for this change.
- Any significant/autonomous decision has an ADR.
- `docs/README.md` indexes any new doc.
- Nothing still-valid was lost.
- `drift.py` is clean, or every remaining finding is explained.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root (Claude Code sets it for hooks; in a
shell use the path the plugin was installed under).
