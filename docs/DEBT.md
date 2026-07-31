# Technical debt register

What this project has knowingly borrowed, what it costs, and what repaying it
would take. Recorded debt is a decision; unrecorded debt is a surprise.

Each entry is written when the debt is taken on, not discovered later. praxis's
`debt-auditor` reads this file during review: debt that is listed here is a
decision it will not re-report, and debt it finds that is *not* here is a finding.

Add with `debt.py add`, close with `debt.py paid <n>`.

## 1. The auditor scoping preamble is duplicated in every agent file

- Recorded: 2026-07-28
- Status: repaid 2026-07-29
- Where: plugins/praxis/agents/*.md

**Interest.** Every change to how a review is scoped must be made in ten agent briefs in lockstep, and a missed one silently under-scopes that auditor: it reports PASS on a diff it never read, which is the failure this preamble exists to prevent.

**Principal.** One shared source the agents include. Claude Code agent files have no include mechanism today, so the available fix is a selfcheck assertion that every agent brief still references scope.py, which catches an omission but not a wording drift.

**Why it was taken on.** The preamble had to reach every auditor in this change; ten near-identical blocks was the only way to do that without a mechanism that does not exist yet.

**Repaid by.** Not by the principal recorded above, which rested on a false premise: agent files *do* have an include mechanism, the `skills` frontmatter field, which preloads a skill's full content into a subagent at startup (verified against the Claude Code subagent documentation and accepted by `claude plugin validate`). The rules now live once in the review-scope skill and no agent restates them. What each brief keeps is a six-line pointer, asserted byte for byte by selfcheck, which exists only because a missing skill is skipped with a debug-log warning and the auditors carry Read but not Skill, so a file read is their only fallback. selfcheck fails on all five silent breakages: a reworded pointer, an agent that stops preloading, the skill going missing, a skill that cannot be preloaded, and the wiring on an agent handed a file list rather than a change.

## 2. The contributor-mode changelog check verifies existence, not freshness

- Recorded: 2026-07-31
- Status: repaid 2026-07-31
- Where: plugins/praxis/scripts/knowledge_check.py: check_changelog

**Interest.** In contributor mode with no project CHANGELOG.md, the record lives in git-excluded local knowledge, which no diff can see. The check therefore passes on any non-empty [Unreleased] section, including one written three sessions ago, so a contributor can satisfy it without recording today's work. Owner mode and joined-changelog contributor repos are unaffected: there the check is exact.

**Principal.** Have changelog.py stamp each write into praxis state (path, entry, timestamp, change signature) and have knowledge_check.py require an entry recorded at or after the current review base. Roughly a day, and it needs a state-schema addition that docs/STABILITY.md would have to cover.

**Why it was taken on.** The exact check needs a new state file and a migration, and the weak check already closes the common case (a contributor who wrote no entry at all). Shipping the honest weaker version now, documented in the script and in docs/AUDIT.md, beats delaying the whole living-knowledge gate for the rarer one.

**Repaid by.** Paid in substance, not to the letter, and the difference is recorded as entry 3. changelog.py now records every entry it writes into .claude/.praxis/changelog_log.json (path, type, message, timestamp, branch, head), and knowledge_check asks whether a write happened since common.change_started_at, which is the base commit's time on a branch and HEAD's off one. The two failure modes are told apart because they need different fixes: nothing written at all, versus a record that belongs to earlier work. A write also carries the commit it was made at, and a write made at a commit this branch does not contain is not counted, which stops a sibling branch inheriting another branch's entry. The principal also named the change signature; that part is not implemented, and what it would have bought is entry 3. Three bounded residues: one-second commit-date resolution makes an entry written moments before its commit count as part of it, which is the correct direction; a rebase ages out an earlier entry, where rewriting it is the honest fix; and a base commit dated after this machine's clock is treated as dating nothing, because a change cannot have begun after now.

## 3. The changelog freshness record is anchored to a commit, not to the unit of work

- Recorded: 2026-07-31
- Status: open
- Where: plugins/praxis/scripts/lib/common.py: changelog_writes_since

**Interest.** An entry written before the branch's first commit is anchored at the base that branch shares with its siblings, so a second branch cut from the same base sees it and passes the living-knowledge gate having recorded nothing of its own. Narrow: it needs two branches from one base, the entry written before the first commit, and a switch without recording. The date-and-ancestry test closes every sibling case where the entry follows a commit. Separately, record_changelog_write is a read-modify-write whose publish step alone is atomic, so two praxis processes in one clone can drop one of their records; the cost is a refusal, never a false pass.

**Principal.** Give the record the identity of the work rather than of a commit. task_state.py already binds one task to one branch and one pull request, so stamping the open task's id onto each write and matching on it would be exact for any change praxis drives, with the current date-and-ancestry rule as the fallback for a change with no task. Half a day, plus a task.json schema addition. The concurrency half is a compare-and-swap or a lock around the read-modify-write.

**Why it was taken on.** The reported hole (an entry from three sessions ago answering for today) is closed, and the sibling case is closed wherever the entry follows a commit. What is left needs an identity the write does not currently carry, and inventing one now would be a second mechanism competing with task_state.py rather than using it. Pinned by a test so it stays a known limit instead of becoming a surprise.
