---
description: "Run the full praxis pipeline on a request (restructure, plan, implement, audit, report). Prefix spec: to stop at the spec."
argument-hint: "<what to fix / add / integrate>  |  spec: <request>"
---

Use the `task-orchestrator` skill to deliver this request end-to-end:

> ${ARGUMENTS}

**Spec-only mode.** If the request starts with `spec:`, or asks for a spec, a plan,
or an estimate rather than a change, run Phase 1 alone: use the `prompt-architect`
skill to produce goal, in-scope, out-of-scope/non-goals, acceptance criteria,
assumptions, and open questions, then stop and present it. Surface ambiguity and
any scope you would exclude; never narrow it silently. Ask only genuinely blocking
questions, and otherwise state the assumption you would proceed under. Keep it
proportional to the task.

**Otherwise run every phase in order.** Do not jump to editing: restructure into a
spec (prompt-architect), investigate the code and confirm the CLAUDE.md, plan in
plan mode before touching files, implement to code-craft standard, run the full
quality rubric (every vertical including completeness) fixing each finding, update
the living knowledge, and finish with the canonical structured report.

Nothing is left implicit: no placeholders, no silent scope cuts, no missing
pieces. If the request touches user-facing surface, the `frontend-pipeline` skill
wraps these phases and the report is not green without the two UI verticals.
