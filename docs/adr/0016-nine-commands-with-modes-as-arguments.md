# 16. Nine commands, with modes as arguments

- Status: accepted
- Date: 2026-07-28

## Context
The plugin exposed thirteen slash commands. Several were a single phase of another (spec is task's phase 1), a different scope of another (scan is audit over a repository rather than a diff), a sibling concern (sync is docs for the CLAUDE.md hierarchy), or a one-line toggle (autopilot). A large palette makes the right entry point harder to find, not easier, and every extra command is another surface that can drift out of step with the skill behind it.

## Decision
Fold five commands into four that already own the concern: spec into task spec:, scan into audit repo, sync into docs, release into ship release, and autopilot into a new config command that also toggles auto-merge and the gate and reports where each resolved value came from. autopilot.py and git_delivery.py merge into config.py. selfcheck.py now fails when any plugin content references a /praxis: command or a script that does not exist, so a future rename cannot leave the instructions pointing at nothing.

## Consequences
Nine commands, each owning one concern, with the mode carried by an argument the command file explains. No workflow was removed: the same skills run behind fewer entry points. This is breaking for anyone who typed the old names or called the two scripts, so it lands in 2.0.0 with a migration table in the README and in STABILITY.md. The selfcheck addition makes the class of drift it fixes impossible to reintroduce.

## Alternatives considered
Keeping thin alias commands for the old names, which preserves compatibility but defeats the purpose, since the palette stays the same size. Deprecating them over a release cycle, which is the right call for a widely-adopted plugin and disproportionate here. Leaving the surface alone, which the user reported as the problem.
