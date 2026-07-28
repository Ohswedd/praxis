# 23. One task is one pull request, and each subtask is one commit

- Status: accepted
- Date: 2026-07-28

## Context
A prompt containing four improvements was one praxis task: one opaque unit of work whose progress nobody could see, ending in a pull request nobody could review and a report that could not say which part was finished. Nothing tied the work to a branch, nothing recorded which commit delivered which piece, and a task could close having quietly become a smaller piece of work than it started as.

## Decision
A task carries an ordered plan of subtasks and a delivery binding. prompt-architect decomposes any request with more than one deliverable into subtasks that are independently completable and worth exactly one commit each, ordered by dependency; where one change forces another they stay one subtask, because splitting them produces a commit that does not work alone. Delivery follows the plan: one task is one branch is one pull request, each subtask lands as its own commit, and the pull request's commit list should read as the plan. task_state.py refuses to close a task while a subtask is unfinished, records the commit each subtask landed on, and warns when a subtask shares a commit with the previous one.

## Consequences
Progress is visible to the user and to the gate, which reports the plan and the next step on every refusal. The version history matches the work, so a change can be reviewed commit by commit and reverted cleanly. The refusal to close with an unfinished subtask makes a plan a commitment rather than a note, with --force as the explicit, reportable escape. Costs: more commits, which is the point; a re-plan is needed when the work genuinely changes shape, and doing that honestly (task_state.py plan) rather than forcing past a skipped subtask is a discipline the tool can encourage but not enforce. This decision is what made ADR-0022 necessary: committing per subtask would otherwise have blinded the audit.

## Alternatives considered
One commit per task with a squashed history was rejected: it is reviewable only as a whole, and for a multi-improvement prompt that is precisely the pull request nobody reads. Separate branches per subtask were rejected: they fragment a single user request across several pull requests, and the reviewer loses the thread that connects them. Enforcing a commit at each subtask boundary was rejected as too rigid, since work legitimately spans a boundary; the warning surfaces it without blocking.
