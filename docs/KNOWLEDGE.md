# Living Knowledge

Praxis treats a project's knowledge as a first-class, always-current artifact,
not documentation you write once and abandon. Three stores, kept in sync with
every change, with the same no-regression discipline Praxis applies to code.

## The three stores

1. **`/docs`**: the human-readable knowledge of the system: architecture,
   subsystem/feature docs, and an index (`docs/README.md`). Every repo Praxis
   manages has a `/docs`; if one is missing, bootstrap scaffolds it from what the
   code actually is (seeded by the `repo-cartographer`), never from assumptions.

2. **`CHANGELOG.md`** (repo root): the running history of *what changed*, in
   [Keep a Changelog](https://keepachangelog.com/) format. Every change adds an
   entry under `[Unreleased]` as it happens, so the project's history is never
   lost. Change types map to Conventional Commits (feat→Added, fix→Fixed, …).

3. **`docs/adr/`**: Architecture Decision Records: *why* a significant decision
   was made. In auto-pilot, every non-trivial autonomous decision is persisted
   here, so the reasoning survives beyond the session that made it.

## Why this matters

- **No regression of knowledge.** Docs are updated, never silently dropped; the
  same verifier discipline that protects `CLAUDE.md` protects `/docs`.
- **Onboarding & audit.** A new engineer (or a future Praxis session) can
  reconstruct the system and the reasoning behind it from these three stores.
- **Enterprise fit.** ADRs + a disciplined changelog + current docs are what
  review, compliance, and handover expect.

## The failure mode this is built against

Knowledge does not usually rot by being deleted. It rots by staying still while
the thing it describes moves, and the most reliable way to produce a wrong
document is to state configuration as if it were a constant.

"Praxis opens the PR and a human merges" is true until someone sets
`auto_merge = true`. From that moment the sentence is wrong, nothing about it
looks wrong, and every session that reads it repeats the wrong policy back to the
user with complete confidence. The same happens to a build command that was
renamed, a module that moved, and a slash command that was folded into another.

Two habits and one check address it:

- **Write the conditional, not the constant.** "With auto-merge off, which is the
  default, praxis stops at the PR" survives the toggle being flipped; name the
  setting that decides and the command that reports its live value.
- **Prefer the resolved value at read time.** The SessionStart audit prints the
  settings actually in force, so a session never has to infer policy from prose.
- **`drift.py`** compares every assertion in the instruction documents against the
  live configuration and checks that documented commands, slash commands, and
  links still resolve. It runs at SessionStart, in `/praxis:doctor`, and as the
  first and last step of `/praxis:docs`.

## How it's enforced

- The **`docs-living` skill** runs the drift check → read → update/create →
  changelog → ADR workflow for every change.
- The **task-orchestrator** makes "update living knowledge" a mandatory phase
  (5b) before the report.
- The **completeness-auditor** fails a change whose docs/changelog weren't
  updated: missing documentation is an incomplete change.
- **`session_audit`** and **`doctor`** report when `/docs` or `CHANGELOG.md` is
  missing, and list any drift they find.
- **ADRs are append-only.** A decision that no longer holds is superseded by a new
  ADR; the original is never rewritten, because the record of what was decided
  and why is the artifact.

## Helpers

- `scripts/changelog.py add --type <t> "msg"`: add an `[Unreleased]` entry.
- `scripts/changelog.py release <version>`: cut a dated release section.
- `scripts/adr.py new "title" --context … --decision … --consequences …`: record
  a decision.
- `scripts/drift.py [--json]`: report documents that contradict the live
  configuration, and references that no longer resolve.
