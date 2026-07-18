---
description: Find or create a missing capability (tool / MCP / skill / plugin) for the task at hand.
argument-hint: "[what you need, e.g. 'query the database']"
---

Use the `capability-discovery` skill.

Precisely name the missing capability ${ARGUMENTS:+($ARGUMENTS)}. Search for an
existing one first — already configured, in a marketplace, or a repo script —
before scaffolding anything, to avoid reinventing. If nothing fits, create the
smallest right primitive (command / skill / subagent / MCP / hook), keep it lean,
reference any secrets via environment variables, and offer to promote it to a
shared plugin if broadly useful.
