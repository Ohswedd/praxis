---
name: docs-living
description: "Keep the project's /docs tree, CHANGELOG.md, the technical-debt register (docs/DEBT.md), and Architecture Decision Records (docs/adr/) alive and accurate. Use for EVERY change that adds, modifies, or removes behaviour, an API, a config, an architectural decision, or a workflow: read the relevant docs first, then update or create them, and record a changelog entry (and an ADR for significant/autonomous decisions). Also use to establish /docs when a repo lacks it. The project must always have a /docs; treat documentation as part of \"done\", never an afterthought."
---

# Living Docs

A project's `/docs`, its `CHANGELOG.md`, and its ADRs are its institutional
knowledge. Praxis keeps them **current with every change**, with the same
no-regression discipline it applies to code, so the knowledge never drifts or is
lost.

**Rule: every repo has a `/docs`. Documentation is part of "done".** A change is
not complete until the docs, changelog, and (where relevant) an ADR reflect it.

## First: whose repository is this?

The rule above assumes the project is ours to shape. Run
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" status` (the session audit
prints it too) and read the workspace mode before writing anything.

In **`contributor` mode the rule inverts to: join what exists, create nothing
new.** A project with a `CHANGELOG.md` expects a contribution to update it, and a
pull request that skipped it is a worse pull request, so update it in the
project's own style. A project without one has not adopted the convention, and
introducing it is a maintainer's decision, not a contributor's, so that record
goes under `.claude/.praxis/knowledge/`, which mirrors the same layout and is
git-excluded. The same applies to `/docs`, `docs/adr/` and `docs/design/`.

`changelog.py` and `adr.py` resolve this for you and **print the path they
wrote**. Read it, and report what actually happened: claiming the project's
changelog was updated when the entry went to local knowledge is exactly the kind
of quietly wrong statement praxis exists to prevent.

## The /docs contract
Expect and maintain this shape (create what's missing):

```
docs/
  README.md            index of the docs (what lives where)
  ARCHITECTURE.md      high-level design, components, data flow
  DEBT.md              the technical-debt register (what was borrowed, and why)
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
7. **Record the debt you knowingly took on.** If this change took a shortcut, left
   a workaround in place, created duplication something will have to keep in sync
   by hand, or leaned on a deprecated API, write it down as it happens:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/debt.py" add "<what was borrowed>" \
     --interest "<what it costs, and how often>" \
     --principal "<what the real fix is>" --why "<why this was the right call now>" \
     --where "<the file or module>"
   ```
   Debt is not a synonym for bad code. A shortcut taken for a stated reason and
   written down is a decision; the same shortcut taken silently is the defect,
   because the next person meets the consequence without the reason. The
   `debt-auditor` reads this register: what is listed here it will not re-report,
   and what it finds that is *not* here is a finding. `debt.py list` shows the
   register; `debt.py paid <n>` closes an entry when it is repaid.
8. **ADR for significant or autonomous decisions.** When you make an architectural
   or non-obvious design decision, especially any decision taken autonomously in
   auto-pilot: persist it:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/adr.py" new "<decision title>" \
     --status accepted --context "..." --decision "..." --consequences "..."
   ```
   ADRs are a historical record: supersede one with a new ADR, never by rewriting
   what it originally said.
9. **Keep the index current.** Update `docs/README.md` when you add a doc.
10. **Re-run the drift check** before you call the docs done. It is the cheapest
   proof that this change did not introduce a new stale reference.

## Establishing /docs (new/legacy repos, owner mode)
If `/docs` or `CHANGELOG.md` is missing, scaffold them (bootstrap does this):
create `docs/README.md`, `docs/ARCHITECTURE.md` (from what the repo-cartographer
found), an empty `docs/adr/`, and a Keep-a-Changelog `CHANGELOG.md`. Seed
`ARCHITECTURE.md` from the actual code, not assumptions. In `contributor` mode,
scaffold none of it: that tree belongs to the project, and praxis keeps its own
notes locally instead.

## Definition of done for docs
- The touched behaviour/API/config is documented and accurate.
- A `[Unreleased]` entry exists for this change, in the project's `CHANGELOG.md`
  or, in `contributor` mode without one, in local knowledge.
- Any significant/autonomous decision has an ADR.
- Any debt this change knowingly took on is in the register, with its
  interest and principal, rather than in someone's memory.
- `docs/README.md` indexes any new doc.
- Nothing still-valid was lost.
- `drift.py` is clean, or every remaining finding is explained.

`${CLAUDE_PLUGIN_ROOT}` is the plugin root (Claude Code sets it for hooks; in a
shell use the path the plugin was installed under).
