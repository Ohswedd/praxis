# 1. Enforce quality via a deterministic Stop-gate rather than native LLM hooks

- Status: accepted
- Date: 2026-07-16

## Context
Praxis must guarantee that a change is reviewed and complete before a turn ends.
Claude Code exposes `prompt` and `agent` hook handler types that could run an LLM
review directly in the Stop event, but their configuration schema is less
universally documented and varies across versions. Praxis also needs the "keep
working until done" loop to be reliable regardless of model behaviour.

## Decision
Enforce the quality bar and the task-completion loop with a deterministic
`command`-type Stop hook (`quality_gate.py`) that reads state files — a signed
green quality report and a `task.json` — rather than an LLM verdict. The LLM
reasoning (the vertical audits) is driven by skills and read-only subagents; the
gate only checks that it happened.

## Consequences
- Positive: works on every Claude Code version that supports `command` hooks;
  deterministic; not gameable by prompt phrasing; bounded by a turn cap.
- Negative: the green report is trust-based (the gate verifies existence/signature,
  not that the audit reasoning was genuine); mitigated by deterministic backstops
  (placeholder scan, secret/destructive guards).

## Alternatives considered
Native `prompt`/`agent` Stop hooks (documented in ARCHITECTURE as a drop-in
alternative) and relying on `/goal` (rejected as the default because it requires
the user to invoke it and its evaluator only reads the transcript).
