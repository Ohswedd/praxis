---
name: capability-discovery
description: Detect and close capability gaps just-in-time. Use whenever a task would benefit from a tool, MCP server, skill, or plugin you don't currently have — for example the work needs database access, browser control, an issue tracker, or a repeated specialised workflow. Always search for an existing capability (already configured, or in a marketplace) before scaffolding a new one, to avoid reinventing or duplicating. Also use to update a capability that has gone stale. Use when the user runs /praxis:discover.
---

# Capability Discovery

Close the gap between "this task needs X" and "I have X" — without reinventing
what already exists. Claude Code does not auto-install capabilities, so this
skill provides the disciplined workflow to do it deliberately.

## Step 1 — Name the gap precisely
State exactly what is missing and why the task needs it, e.g. "needs to query the
project's Postgres to validate the migration", "needs to drive the browser to
verify the UI change", "this three-step release check recurs and should be a
command".

## Step 2 — Search existing first (no reinvention)
In order, check:
1. **Already available** — is there a configured MCP server or an installed
   plugin/skill that covers it? (`/mcp`, `/plugin list`, the available tools.)
2. **In a marketplace** — is there a maintained plugin/MCP for it? Prefer a
   well-maintained existing one over building your own.
3. **In the repo** — is there already a script or Make target that does this?

Only proceed to create something if all three come up empty.

## Step 3 — Choose the smallest right primitive
- Recurring *prompt* → a slash command.
- Real domain logic or a multi-step workflow with helper files → a **skill**.
- Isolated, parallel, or read-limited work → a **subagent**.
- Access to an external system over a protocol → an **MCP server** (reference
  credentials via environment variables; never hard-code secrets).
- A rule to enforce deterministically → a **hook**.

## Step 4 — Scaffold ad-hoc, cleanly
Create the minimal working version in `.claude/` (fast to iterate). Give it a
crisp, "pushy" description so it triggers when relevant. Keep it small — every
component adds always-on context. Document how to use it.

## Step 5 — Update stale capabilities
If the gap is an existing capability that has drifted (renamed API, changed
schema, new auth), update it in place and re-verify rather than adding a
parallel one.

## Step 6 — Offer to promote
If the new capability is broadly useful and the user wants to share it across
repos or a team, offer to package it as a plugin (versioned, marketplace-
distributed) rather than leaving it as a private `.claude/` file.
