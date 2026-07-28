---
name: review-scope
description: "What 'the change' means in a review, and how an auditor establishes it: the branch's commits since its base as well as what is still uncommitted, never the working tree alone. Preloaded into every praxis review auditor through the `skills` frontmatter field, so the rule exists once. Use whenever you are about to audit, review, or reason about a change in a repository."
---

# Scope the change before you judge it

The working tree is not the change. On a branch that has committed anything,
`git diff` is empty, and a review scoped that way reads nothing, finds nothing,
and returns PASS. That failure is silent: the verdict is indistinguishable from a
genuine clean review, and it gets *more* likely the better the delivery
discipline is, because one commit per subtask means most of a task's life is
spent in exactly that state.

So a review has a **base**, and everything from that base to now is in scope:
what the branch has committed, what is staged, what is merely edited, and the
untracked files that appear in no diff at all.

## Where your scope comes from

**It is given to you.** Whoever dispatched you resolves it first with
`scripts/scope.py` and states it in your prompt: the base commit, the commits on
the branch, and the files under review. Work from that.

You are a read-only auditor: your tools are `Read`, `Grep` and `Glob`, with no
shell. You cannot run `git` and you cannot resolve a base yourself. That is
deliberate, and it means the scope is a fact you are handed rather than one you
discover.

## When you were not given one

Say so, in the verdict, in words. Then:

- Audit what you can reach with `Read`, `Grep` and `Glob`, and **state exactly
  what that was**: the files you actually examined.
- Do not describe the result as clean. A review whose scope was narrower than the
  change is not a passing review, and the reader cannot tell the difference
  unless you tell them. Return `FAIL` if the scope gap makes your verdict
  meaningless, and `PASS WITH NOTES` naming the gap if it does not.
- Never infer the change from what happens to be modified on disk. That is the
  working-tree assumption this whole rule exists to break.

## State the base in your verdict

Every verdict names the base it was given and what it read. A verdict whose scope
is unstated cannot be trusted by the next reader, and "I reviewed the working
tree" on a branch with commits means the review did not happen.

## When your scope is a repo shard

`/praxis:audit repo` hands you a file list rather than a change. There is no base
and none of the above applies: audit the files as they stand, and hunt the same
hazards as they exist latently rather than as something a change introduced.
