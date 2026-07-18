---
name: git-delivery
description: "Deliver a finished change through Git and GitHub to professional standards. Use when the work is complete and audited and it should be committed, pushed, or turned into a pull request, or when the user runs /praxis:ship. Covers Conventional Commits, branch naming, PR authoring, and the review/merge policy: human-in-the-loop by default, autonomous review-and-merge only when opted in. Never merges without a green audit."
---

# Git Delivery

The last mile: turn an audited change into a clean commit and a reviewable pull
request. Delivery is **explicit and only when needed** — praxis does not commit
or push on every edit. Run this once a change is complete and its audit is green.

**Preconditions.** The praxis audit is green, tests pass, and the working tree
holds only the intended change. If secrets are present or the audit is red, stop
and fix — never deliver an unreviewed or unsafe change.

## 1. Commit — Conventional Commits

Match the repo's existing history first; where it already uses
[Conventional Commits](https://www.conventionalcommits.org/), follow it:

```
<type>(<scope>): <subject>

<body: what changed and why — not how>

<footer: BREAKING CHANGE: ...  |  Refs #123>
```

- **type**: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
- **subject**: imperative mood, no trailing period, ≤ 72 characters.
- **body**: motivation and effect; wrap at ~72 columns; omit for trivial changes.
- **BREAKING CHANGE** footer (or `type!:`) for any incompatible change.
- One logical change per commit — stage intentionally; do not bundle unrelated work
  or blindly `git add -A` across a mixed tree.

Never commit secrets, credentials, or local state (respect `.gitignore`). The
PreToolUse guard blocks force-pushes to protected branches and destructive resets;
delivery works within it.

## 2. Branch

If on the integration branch, create a topic branch before committing:
`<type>/<kebab-summary>` (e.g. `feat/github-delivery`). Keep one PR per branch.

## 3. Pull request

Push the branch and open a PR against the default branch
(`git_delivery.py status` reports it) with `gh pr create`. Use the repo's PR
template if one exists; otherwise a structured body:

- **What & why** — the change and its motivation.
- **How it was verified** — the test command and result, and the audit verdicts.
- **Checklist** — tests updated, changelog/docs updated, Conventional Commit title.

Link the issue it closes (`Closes #NN`). Title the PR as a Conventional Commit —
the release automation reads it.

## 4. Review & merge policy

Check the toggle: `git_delivery.py status`, env `PRAXIS_AUTO_MERGE`, or
`.praxis.toml [git] auto_merge`.

- **Auto-merge OFF (default) — human-in-the-loop.** Stop after opening the PR.
  Report the PR URL and hand it to the user to review and merge. Do not merge.
- **Auto-merge ON — autonomous.** Only after the audit is green and (when the repo
  has CI) required checks pass: self-review the diff against the PR checklist, then
  `gh pr merge --squash --delete-branch`. Prefer squash to keep the base branch
  linear unless the repo's convention differs. Never bypass branch protection and
  never force-push the base branch. If checks are still running, enable GitHub
  auto-merge (`gh pr merge --auto --squash`) rather than waiting or forcing.

Either way, delivery ends with the PR URL and the merge state stated plainly.
