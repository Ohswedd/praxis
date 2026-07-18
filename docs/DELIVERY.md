# Git & GitHub Delivery

Praxis delivers a finished change the way a disciplined engineer would: a clean
[Conventional Commit](https://www.conventionalcommits.org/), a topic branch, and a
reviewable pull request — with the merge decision explicit and, by default, left
to a human.

Delivery is **explicit and only when needed**. Praxis never commits or pushes on
every edit; you invoke it once a change is complete and its audit is green, via
`/praxis:ship` (or the `git-delivery` skill inside the task pipeline). The
mechanics live in the skill; this page is the contract.

## The default: human-in-the-loop

Out of the box, praxis:

1. writes a Conventional Commit (`type(scope): subject`, imperative, ≤72-char
   subject, body explaining what and why);
2. branches (`type/kebab-summary`) if you're on the integration branch;
3. pushes and opens a PR (`gh pr create`) with a structured body — what & why, how
   it was verified (tests + audit verdicts), and a checklist — using the repo's PR
   template when present;
4. **stops** and hands you the PR URL to review and merge.

It does **not** merge to the integration branch. You stay in the loop for the one
irreversible step.

## The toggle: autonomous review-and-merge

Turn on auto-merge and praxis also reviews and merges its own PR — but only after
the audit is green and any required CI checks pass:

```
git_delivery.py on        # this repo
git_delivery.py off       # clear the toggle (config/env still override)
git_delivery.py status    # show state + base branch
```

Equivalent controls (checked in this order): env `PRAXIS_AUTO_MERGE=on`, the
`.claude/.praxis/auto-merge` toggle file, and `.praxis.toml`:

```toml
[git]
auto_merge = true         # default false
default_branch = ""       # PR base ("" auto-detects origin/HEAD, then main/master)
```

When on, praxis prefers a squash merge (`gh pr merge --squash --delete-branch`) to
keep the base branch linear, or enables GitHub auto-merge when checks are still
running. It never bypasses branch protection and never force-pushes the base
branch — and the PreToolUse guard backs that up, blocking `--admin` merges,
force-pushes, and destructive resets in every mode.

## Safety

- Delivery runs only on a green audit and a tree holding just the intended change.
- Secrets and local state are never committed (`.gitignore` is respected; the
  secret guard still fires).
- Force-pushes to protected branches, destructive resets, and `--admin` PR merges
  stay blocked by the PreToolUse guard, in every mode.

See [MODES.md](MODES.md) for how delivery fits the autonomy model and
[STABILITY.md](STABILITY.md) for the stable surface.
