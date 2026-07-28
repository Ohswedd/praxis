---
name: git-delivery
description: "Deliver a finished change through Git and GitHub to professional standards, and cut releases. Use when the work is complete and audited and it should be committed, pushed, turned into a pull request, or released, or when the user runs /praxis:ship. Covers Conventional Commits, branch naming, PR authoring, SemVer releases, the ban on AI attribution in the project's record, and the review/merge policy: human-in-the-loop by default, autonomous review-and-merge only when opted in. Never merges without a green audit."
---

# Git Delivery

The last mile: turn an audited change into a clean commit and a reviewable pull
request. Delivery is **explicit and only when needed**: praxis does not commit
or push on every edit. Run this once a change is complete and its audit is green.

**Preconditions.** The praxis audit is green, tests pass, and the working tree
holds only the intended change. If secrets are present or the audit is red, stop
and fix, never deliver an unreviewed or unsafe change.

## 1. Commit: Conventional Commits

Match the repo's existing history first; where it already uses
[Conventional Commits](https://www.conventionalcommits.org/), follow it:

```
<type>(<scope>): <subject>

<body: what changed and why, not how>

<footer: BREAKING CHANGE: ...  |  Refs #123>
```

- **type**: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
- **subject**: imperative mood, no trailing period, ≤ 72 characters.
- **body**: motivation and effect; wrap at ~72 columns; omit for trivial changes.
- **BREAKING CHANGE** footer (or `type!:`) for any incompatible change.
- One logical change per commit: stage intentionally; do not bundle unrelated work
  or blindly `git add -A` across a mixed tree.
- **No AI/tool attribution, enforced.** No `Co-Authored-By` trailer for Claude or
  any AI, no "generated with" credit, no robot emoji, in the message, the body, or
  the footer. The history is the project's own. Describing the platform ("praxis
  is a Claude Code plugin") is fine; crediting authorship is not. The PreToolUse
  guard refuses any `git commit`, `git tag`, `gh pr create`, `gh release create`
  or `gh issue` command that carries one, so this is not a matter of remembering:
  the command will simply be blocked, and once a credit is committed it is in the
  history for good.

Never commit secrets, credentials, or local state (respect `.gitignore`). The
PreToolUse guard blocks force-pushes and destructive resets; delivery works within
it.

## 2. Branch

If on the integration branch, create a topic branch before committing:
`<type>/<kebab-summary>` (e.g. `feat/github-delivery`). Keep one PR per branch.

## 3. Pull request

Push the branch and open a PR against the default branch
(`config.py status` reports it) with `gh pr create`. Use the repo's PR
template if one exists; otherwise a structured body:

- **What & why**: the change and its motivation.
- **How it was verified**: the test command and result, and the audit verdicts.
- **Checklist**: tests updated, changelog/docs updated, Conventional Commit title.

Link the issue it closes (`Closes #NN`). Title the PR as a Conventional Commit:
the release automation reads it. The no-attribution rule applies to the PR body,
the release notes, and any issue comment exactly as it does to the commit, and the
guard blocks those commands too.

## 4. Review & merge policy

**Resolve the policy, do not recall it.** Run
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" status`, which reports the
value in force and the source it came from (env `PRAXIS_AUTO_MERGE`, the repo
toggle, `.praxis.toml [git] auto_merge`, or the default). Documentation of a
toggle goes stale the moment the toggle is flipped; the resolved value cannot.
The SessionStart audit states it too, so there is no excuse for acting on the
wrong one.

- **Auto-merge OFF (the default): human-in-the-loop.** Stop after opening the PR.
  Report the PR URL and hand it to the user to review and merge. Do not merge.
- **Auto-merge ON: autonomous.** Only after the audit is green and (when the repo
  has CI) required checks pass: self-review the diff against the PR checklist, then
  `gh pr merge --squash --delete-branch`. Prefer squash to keep the base branch
  linear unless the repo's convention differs. Never bypass branch protection and
  never force-push the base branch. If checks are still running, enable GitHub
  auto-merge (`gh pr merge --auto --squash`) rather than waiting or forcing.

Either way, delivery ends with the PR URL and the merge state stated plainly.

## 5. Release (`/praxis:ship release [version]`)

A release is the same delivery discipline applied to a version boundary, so it
lives here rather than in a command of its own.

1. Review what is pending: `changelog.py show`.
2. Derive the next version from the commits since the last tag and the
   `[Unreleased]` entries, applying SemVer per Conventional Commits: a breaking
   change is MAJOR, `feat` is MINOR, `fix` and `perf` are PATCH. State the
   reasoning rather than just the number, and prefer the user's explicit version
   when they gave one.
3. Finalize the changelog into a dated section: `changelog.py release <version>`.
4. Bump every version file the project keeps in step (package.json,
   pyproject.toml, plugin and marketplace manifests). A release where two
   manifests disagree is a broken release.
5. Show the diff, then prepare the commit `chore(release): v<version>` and the tag
   `v<version>`. Do not push either until the user confirms.

Match the project's own release process where it has one, and never rewrite a
published tag.
