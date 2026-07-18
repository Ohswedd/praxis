---
description: Prepare this repo for top-tier Claude Code use (new, existing, or legacy CLAUDE.md).
argument-hint: "[path] (optional; defaults to the current project)"
---

Use the `bootstrap` skill to set up this repository for Claude Code.

Classify the repo state first (new / uninitialised / legacy / managed), then
follow the skill: map the codebase read-only, generate or reconcile the CLAUDE.md
hierarchy (routing any legacy file through `@praxis:claudemd-verifier`), propose
`.claude/settings.json` guardrails, and propose LSP/MCP wiring via
`capability-discovery`. Everything is shown as a diff and confirmed before writing.

Target: ${ARGUMENTS:-the current project directory}.
