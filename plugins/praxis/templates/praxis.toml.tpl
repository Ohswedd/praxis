# Praxis per-repo configuration (optional). Commit this to version it with the repo.
# All keys are optional; shown values are the defaults.
#
# A second copy of this file at .claude/.praxis/praxis.toml is read afterwards and
# overrides it. That one is git-excluded, so it is where a personal or per-clone
# choice belongs, and it is the only one praxis writes in contributor mode.

[workspace]
# Whose repository is this?
#   "owner"       praxis maintains CLAUDE.md, .claude/settings.json, /docs,
#                 CHANGELOG.md and ADRs as this project's own committed files.
#   "contributor" the repo is not ours: the brief is CLAUDE.local.md, settings are
#                 .claude/settings.local.json, and /docs, CHANGELOG.md, docs/adr/
#                 and docs/design/ are updated only if the project already has
#                 them, otherwise kept in .claude/.praxis/knowledge/. Everything
#                 praxis authors is excluded from git and can never be staged.
#   "auto"        infer it: a repo with a remote and real history that contains no
#                 commit from your git address is somebody else's project.
mode = "auto"

[bootstrap]
# Set an unmanaged repo up on its own, in the first turn that does real work,
# before that work starts. Off leaves the repo without a brief or guardrails until
# /praxis:bootstrap is run by hand.
auto = true

[gate]
# Master switch for the Stop quality/task gate.
enabled = true
# Require passing test evidence in the green report when the repo has a test command.
require_tests = true
# Require the accessibility and design-consistency verdicts when the change touches
# user-facing surface (markup, styles, components, docs/design/).
require_ui_verticals = true

[autopilot]
# Start sessions in auto-pilot (no questions; decide by best-practice, log decisions).
default = false

[audit]
# Informational depth hint for the auditors: "high" | "max".
depth = "high"

[git]
# Auto-review and merge praxis's own PRs after a green audit. Off (default) opens
# the PR and hands it to a human to review and merge: the loop stays gated.
auto_merge = false
# PR base branch. Empty auto-detects from origin/HEAD, then main/master.
default_branch = ""

[style]
# Refuse em dashes in authored text. A colon, a comma, parentheses, or two
# sentences always say it more precisely.
ban_em_dash = true
# Refuse AI co-author trailers and "generated with" credits in commits, tags,
# PRs, releases, and issues. The history belongs to the project.
ban_ai_attribution = true
