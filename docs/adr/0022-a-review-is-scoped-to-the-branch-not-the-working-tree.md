# 22. A review is scoped to the branch, not the working tree

- Status: accepted
- Date: 2026-07-28

## Context
praxis defined 'the change' as the working tree: the unstaged diff, the staged diff, and untracked files. Every consumer was built on that definition: the placeholder and house-style scanners, the UI-vertical resolution, the change signature, and the Stop gate's dirty-tree question. The definition has a hole, and it is not a corner case: one git commit empties every diff it reads. The tree goes clean, changed_files returns nothing, the scanners find nothing, the auditors review nothing, and the gate opens. Deciding that each subtask should land as its own commit (ADR-0023) would therefore have switched the entire audit apparatus off for most of a task's life, so the better the delivery discipline got, the less praxis would have seen.

## Decision
The review scope is the branch: every commit since it left its merge-base with the integration branch, plus whatever is still uncommitted, plus untracked files. common.review_base() resolves the base and changed_files, added_line_pairs, change_signature and the new review_pending all cover the range, so every existing consumer sees committed work without being changed. The Stop gate's question becomes 'is there anything to review' rather than 'is the tree dirty'. scope.py prints the base, the commits, the files and the diff commands so the rubric and each subagent work from one resolved answer, and every auditor now resolves the scope before judging and states the base it used. On the integration branch there is no range and the behaviour is exactly as before.

## Consequences
A change stays reviewable through however many commits it takes, which is what makes one-commit-per-subtask safe. The signature keys on the range rather than HEAD alone, so a report recorded against three commits is valid for those three and not for a fourth. The audit reads more on a long branch, which is correct: that is the change. Costs: review_base is one merge-base call, memoised per process; a long-lived branch that has drifted far from its base presents a large scope, which is honest but slower to audit; and a repo that works directly on the integration branch sees no behaviour change at all, which also means it gets no benefit.

## Alternatives considered
Keeping the working-tree definition and requiring the audit to run before each commit was rejected: it makes the gate depend on the model remembering the order, which is the class of guarantee praxis exists to replace. Diffing against the previous commit rather than the merge-base was rejected: it reviews the last commit rather than the change, and a three-commit branch would never be reviewed as a whole. Reviewing against origin/HEAD directly was rejected because it makes the scope depend on how stale the local remote ref is.
