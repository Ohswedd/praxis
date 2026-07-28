---
description: "Deliver the finished change as a Conventional Commit, branch and PR; release cuts a version instead."
argument-hint: "[ blank | PR title or issue to close | release [version] ]"
---

Use the `git-delivery` skill. Read `${ARGUMENTS}` to pick the mode.

**Default: deliver the current change.** Precondition: the praxis audit is green
and the tree holds only the intended change. Write a Conventional Commit, branch
if on the default branch, push, and open a PR with a structured body. Check the
live merge policy with `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" status`
and follow it: merge only when auto-merge is ON and the audit and any required
checks are green, otherwise stop at the PR and hand it to the user. Finish by
reporting the PR URL and the merge state.

**`release [version]`: cut a release.**

1. Review what is pending: `changelog.py show`.
2. Determine the next version, unless one was given, from the commits since the
   last tag and the `[Unreleased]` entries, applying SemVer per Conventional
   Commits: breaking to MAJOR, `feat` to MINOR, `fix`/`perf` to PATCH. State your
   reasoning.
3. Finalize the changelog into a dated section: `changelog.py release <version>`.
4. Bump every version file the project uses (package.json, pyproject.toml, plugin
   and marketplace manifests) so they agree.
5. Prepare, without pushing until the user confirms, the commit
   `chore(release): v<version>` and the tag `v<version>`. Show the diff first.

Match the project's existing release process where it has one. Scripts live under
`${CLAUDE_PLUGIN_ROOT}/scripts/`.

Never add an AI co-author trailer or a "generated with" credit to a commit, tag,
PR body, or release note. The PreToolUse guard blocks the command outright.
