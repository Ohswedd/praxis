# Privacy Policy

**Praxis — a Claude Code plugin.** Last updated: 2026-07-22.

## Summary

Praxis collects nothing, transmits nothing, and has no servers. It is a set of
local scripts and instructions that run on your machine, inside your Claude Code
session. There is no account, no registration, no telemetry, and no analytics.

## What Praxis does not do

- **No data collection.** Praxis has no backend and no operator-controlled
  endpoint. Nothing about you, your machine, or your code is sent to the author
  of this plugin.
- **No network access.** The plugin's code makes no network calls of any kind.
  It imports no HTTP or socket library, and every script runs offline.
- **No telemetry or analytics.** No usage counters, no crash reporting, no
  identifiers of any kind are created or transmitted.
- **No third-party services.** Praxis integrates with no external service and
  ships no MCP server.

## What Praxis reads

Locally, and only to do its job:

- Files in the repository you are working in, to audit changes, detect the
  project's conventions and test command, and scan for accidentally committed
  secrets.
- Your Git metadata (branch, status, commit history) via the `git` command.
- An optional `.praxis.toml` in your repository.

Secret scanning is a safety feature that runs entirely on your machine. When it
finds something, it reports the finding — never the secret's value — and
deliberately does not read flagged files into the conversation.

## What Praxis writes

Only inside the repository you are working in:

- `.claude/.praxis/` — small JSON state files recording task progress, the
  quality report, and gate counters. This directory is git-ignored by default.
- The files Claude edits at your instruction, under your normal Claude Code
  permissions.

Nothing is written outside your workspace. No system, global, or user-level
configuration is modified.

If a test run fails, Praxis stores the last 20 lines of its output in
`.claude/.praxis/quality_report.json` so the failure can be diagnosed. That
output is scanned and any recognised secret is replaced with a redaction marker
before it is written to disk.

## What reaches Anthropic

This is the part worth stating plainly, because it is the one place information
leaves your machine — and it is Claude Code's own data flow, not a channel
Praxis controls or has access to.

Praxis works by injecting text into your Claude Code conversation: a repository
health summary at session start, routing instructions per prompt, and audit
findings. As with anything in a Claude Code session, that text is sent to
Anthropic as part of the conversation so the model can act on it. In practice
this means file paths, code excerpts under review, and findings such as "a
possible secret was detected in this file" may appear in your conversation.

Anthropic's handling of that conversation is governed by
[Anthropic's Privacy Policy](https://www.anthropic.com/legal/privacy) and your
own account terms, not by this document.

One subagent, `doc-reference-finder`, may use Claude Code's `WebSearch` and
`WebFetch` tools to consult a library's official documentation. Those requests
are made by Claude Code under your existing permissions, not by Praxis code, and
go to the search or documentation provider — not to the author of this plugin.

## Children

Praxis is a developer tool and is not directed at children.

## Changes

Material changes to this policy will be recorded in
[`CHANGELOG.md`](CHANGELOG.md) and reflected in the date above.

## Contact

Questions about this policy: open an issue at
<https://github.com/Ohswedd/praxis/issues>.
