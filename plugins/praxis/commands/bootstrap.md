---
description: Prepare this repo for top-tier Claude Code use (new, existing, or legacy CLAUDE.md).
argument-hint: "[path] (optional; defaults to the current project)"
---

Use the `bootstrap` skill to set up this repository for Claude Code.

This normally runs on its own: any session that does real work in a repo praxis
has not set up bootstraps it first, in the same turn. Running the command is the
same setup asked for explicitly, and it is also how you re-run it after the repo
has moved on.

Classify the repo state (new / uninitialised / legacy / managed), then follow the
skill: map the codebase read-only, generate or reconcile the brief hierarchy
(route any legacy file through `@praxis:claudemd-verifier`), propose the settings
guardrails, and propose LSP/MCP wiring via `capability-discovery`.

**Check the workspace mode first** (`config.py status`, or the session audit). In
`owner` mode praxis writes the project's own committed files. In `contributor`
mode the repository is not ours: the brief is `CLAUDE.local.md`, settings are
`.claude/settings.local.json`, knowledge lands under
`.claude/.praxis/knowledge/`, all git-excluded, and the repo itself gets nothing.

Write what does not exist; show the diff and confirm before reconciling anything
praxis did not author.

Target: ${ARGUMENTS:-the current project directory}.
