---
name: git-delivery
description: "Deliver a finished change through Git and GitHub to professional standards, and cut releases. Use when the work is complete and audited and it should be committed, pushed, turned into a pull request, or released, or when the user runs /praxis:ship. Covers Conventional Commits, branch naming, PR authoring, SemVer releases, the ban on AI attribution in the project's record, contributing to a repository you do not own (match its conventions, ship nothing praxis authored, stop at the PR), and the review/merge policy: human-in-the-loop by default, autonomous review-and-merge only when opted in. Never merges without a green audit."
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
it, and it also refuses to stage `CLAUDE.local.md`, `.claude/.praxis/` or
`.claude/settings.local.json`, which describe your machine rather than the
project and belong in no repository's history.

## 2. Branch, and the unit of delivery

If on the integration branch, create a topic branch before committing:
`<type>/<kebab-summary>` (e.g. `feat/github-delivery`).

**One task is one branch is one pull request.** Whatever the user asked for in a
prompt (which praxis may have decomposed into several subtasks) is delivered as a
single reviewable unit, so the version history matches the work rather than being
reconstructed from it afterwards.

- **A task with subtasks**: one commit per subtask, on the task's branch, and one
  pull request for the task. The PR's commit list should read as the plan. Record
  each as it lands, so the mapping survives the session:
  ```bash
  git commit -m "<type>(<scope>): <the subtask>"
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py" subtask done <n>
  ```
  `subtask done` captures the commit and warns when a subtask shares one with the
  previous subtask, because at that point the tracking has quietly gone.
- **A single-step task**: one commit, one pull request. The rule is the same
  shape, with a plan of one.
- **Never** let two unrelated tasks share a branch. If the user asks for something
  new while a task is open, that is a second task and a second branch: finish or
  park the first, do not fold it in. A pull request that does two things cannot be
  reviewed, cannot be reverted cleanly, and cannot be versioned honestly.

Record the delivery on the task so the report can state it:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py" delivery --pr <url>
```
`task_state.py done` says so when a task closes with no pull request recorded.

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

## 3b. Contributing to a repository that is not yours

`config.py status` reports the workspace mode. When it says `contributor`, the
project's maintainers own the standards and the merge button, and delivery
changes shape:

- **The commit carries the change and nothing else.** No `CLAUDE.md`, no
  `.praxis.toml`, no `/docs` tree, no `CHANGELOG.md`, no `.gitignore` edit that
  praxis wanted. Those are praxis's setup, and praxis keeps them out of git
  through `$GIT_COMMON_DIR/info/exclude` so `git add -A` cannot reach them. Review
  `git status` and `git diff --staged` before committing anyway: the guard is a
  backstop, not a substitute for looking.
- **Match their conventions, not ours.** Read `CONTRIBUTING.md`, the PR template,
  and the last several merged commits, and follow what you find: their commit
  format even if it is not Conventional Commits, their branch naming, their
  changelog expectation, their test command, their sign-off requirement
  (`git commit -s` where DCO applies). praxis's house rules that are about *not*
  adding noise (no AI attribution, no em dashes) still hold, because they never
  conflict with a project's own style.
- **Fork or branch as the project expects**, and push to your fork when you do
  not have write access. Never push to their default branch.
- **Stop at the pull request.** Auto-merge does not apply here whatever the local
  toggle says: merging someone else's project is not a decision praxis or you get
  to make. Report the PR URL and what still needs their review.
- **Say where the knowledge went.** If the project has no `CHANGELOG.md` and the
  entry landed in `.claude/.praxis/knowledge/`, say so rather than implying the
  PR updated a changelog it did not.

## 4. Review & merge policy

**Resolve the policy, do not recall it.** Run
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" status`, which reports the
value in force and the source it came from (env `PRAXIS_AUTO_MERGE`, the repo
toggle, `.praxis.toml [git] auto_merge`, or the default). Documentation of a
toggle goes stale the moment the toggle is flipped; the resolved value cannot.
The SessionStart audit states it too, so there is no excuse for acting on the
wrong one.

- **`contributor` mode: never.** Section 3b applies and outranks the toggle.
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
lives here rather than in a command of its own. It is an `owner`-mode activity:
versioning someone else's project is theirs to do.

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
