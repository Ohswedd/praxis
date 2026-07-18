---
description: Deliver the finished change — Conventional Commit, push a branch, open a PR (merge only if auto-merge is on).
argument-hint: "[optional: PR title or issue to close]"
---

Use the `git-delivery` skill to deliver the current change.

Precondition: the praxis audit is green and the tree holds only the intended
change ${ARGUMENTS:+($ARGUMENTS)}. Write a Conventional Commit, branch if on the
default branch, push, and open a PR with a structured body. Merge only when
auto-merge is enabled (`git_delivery.py status`) and the audit and any required
checks are green; otherwise stop at the PR and hand it to the user to merge.
Finish by reporting the PR URL and the merge state.
