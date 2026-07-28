# Technical debt register

What this project has knowingly borrowed, what it costs, and what repaying it
would take. Recorded debt is a decision; unrecorded debt is a surprise.

Each entry is written when the debt is taken on, not discovered later. praxis's
`debt-auditor` reads this file during review: debt that is listed here is a
decision it will not re-report, and debt it finds that is *not* here is a finding.

Add with `debt.py add`, close with `debt.py paid <n>`.

## 1. The auditor scoping preamble is duplicated in every agent file

- Recorded: 2026-07-28
- Status: open
- Where: plugins/praxis/agents/*.md

**Interest.** Every change to how a review is scoped must be made in ten agent briefs in lockstep, and a missed one silently under-scopes that auditor: it reports PASS on a diff it never read, which is the failure this preamble exists to prevent.

**Principal.** One shared source the agents include. Claude Code agent files have no include mechanism today, so the available fix is a selfcheck assertion that every agent brief still references scope.py, which catches an omission but not a wording drift.

**Why it was taken on.** The preamble had to reach every auditor in this change; ten near-identical blocks was the only way to do that without a mechanism that does not exist yet.
