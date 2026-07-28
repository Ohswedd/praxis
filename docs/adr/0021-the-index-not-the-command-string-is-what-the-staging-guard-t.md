# 21. The index, not the command string, is what the staging guard trusts

- Status: accepted
- Date: 2026-07-28

## Context
Contributor mode's guarantee is that nothing praxis authors reaches a project's history. The first implementation enforced it by matching the Bash command against the artifact names. An adversarial audit produced clean bypasses in minutes: git -C .claude add -f settings.local.json never contains the literal .claude/settings.local.json; a shell glob expands after the hook has read the command; --pathspec-from-file names nothing; git update-index --add writes the index directly and ignores exclude rules entirely; and once any of those had staged the file, git commit was never inspected at all. The exclude file could not cover it either, because git add --force exists specifically to override an exclusion.

## Decision
Keep the string-level checks as an early, legible refusal, and add the layer that actually holds: before any command that publishes the index (commit, push, stash), ask git what is staged (git diff --cached --name-only) and refuse while a praxis artifact is in it, however it got there. Separately, refuse a forced stage-everything outright rather than verifying an exclusion that --force is designed to defeat, and distinguish an already-tracked artifact (which no exclusion can hide, and whose remedy is git rm --cached) from a missing exclusion.

## Consequences
The guarantee no longer depends on enumerating command shapes, which is an unwinnable game: the set of ways to write a path is open, the set of ways to publish an index is small and closed. The cost is one git invocation on commit/push/stash, which is negligible against what those commands already do. The string checks stay because they fail earlier and explain better, and because a refusal at git add is cheaper for the user than one at git commit. False positives on commit messages that merely name these files were removed at the same time: quoted text is stripped before the artifact search, since praxis's own history is full of such messages and a blocked commit is not cheap to retry.

## Alternatives considered
Enumerating more command shapes was rejected: it is what produced the bypasses, and each addition invites the next. Blocking every git add in contributor mode was rejected as unusable. Making the artifacts read-only on disk was rejected: praxis has to write them, and it would not stop a commit of an already-staged copy.
