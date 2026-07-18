# 5. GitHub delivery: PR-first, human-in-the-loop by default

- Status: accepted
- Date: 2026-07-18

## Context
Praxis produced audited changes but had no delivery step, so committing, pushing, and opening PRs were ad hoc and inconsistent. Merging to an integration branch is irreversible and outward-facing; automating it by default would remove human oversight from the one step that most warrants it.

## Decision
Add an explicit delivery step (git-delivery skill + /praxis:ship) that writes a Conventional Commit, branches, pushes, and opens a PR with a structured body. The merge is human-in-the-loop by default: praxis stops at the PR. An opt-in git.auto_merge toggle (config key, PRAXIS_AUTO_MERGE env, git_delivery.py) lets praxis review and merge its own PR, but only on a green audit and passing checks, using squash-and-delete, and never by force-pushing or bypassing branch protection. Delivery is explicit and only-when-needed, not run on every edit.

## Consequences
Delivery follows the same discipline as the rest of the pipeline and dogfoods conventional commits. The default keeps humans on the irreversible step; teams that want full autonomy opt in per repo. The existing PreToolUse guard already blocks force-push/destructive git, so auto-merge composes safely. Adds two config keys, one env var, one state file, one helper CLI, one command, and one skill to the stable surface.

## Alternatives considered
Auto-commit-and-push on every green change (rejected: violates only-when-needed and removes human control). Merge by default with an opt-out (rejected: the safe default must be the conservative one). A dedicated toggle command instead of a config key (rejected: keeps the command surface lean; the config key plus env and helper CLI mirror the autopilot pattern).
