---
name: review-scope
description: "How to scope a code review before judging it: resolve the branch's base, read what it committed as well as what it has not, and never scope with git diff alone. Preloaded into every praxis review auditor via the `skills` frontmatter field, so the rule exists once. Use whenever you are about to audit, review, or reason about 'the change' in a repository."
---

# Scope it before you judge it

`git diff` alone is not the change. On a branch that has committed anything it is
empty, and an audit scoped that way reads nothing, finds nothing, and reports
PASS. That failure is silent: the verdict looks identical to a genuine clean
review, and it gets worse the better the delivery discipline is, because one
commit per subtask means most of a task's life is spent in exactly that state.

So establish the real scope first:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scope.py"    # base, commits, files
```

It prints the review base, the commits on this branch, the files under review,
and the exact commands below with the base filled in.

## Read all of it

- `git diff <base>...HEAD` for what the branch has already committed.
- `git diff` and `git diff --staged` for what it has not.
- The untracked files, which appear in **no** diff at all. Read them directly;
  new files are where unfinished work most often lives.

If `scope.py` reports that it could not resolve a base, say so in your verdict.
A review whose scope was narrower than the change is not a passing review, and
the reader cannot tell the difference unless you tell them.

## State the base you used

Every verdict names the base it compared against and how much it read. A verdict
whose scope is unstated cannot be trusted by the next reader, and "I reviewed the
working tree" on a branch with commits means the review did not happen.

## When your scope is a repo shard

`/praxis:audit repo` hands you a file list rather than a diff. There is no base
and nothing above applies: audit the files as they stand, and hunt the same
hazards as they exist latently rather than as something a change introduced.
