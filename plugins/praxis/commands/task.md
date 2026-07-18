---
description: Run the full praxis pipeline on a request (restructure → plan → implement → audit → report).
argument-hint: "<what to fix / add / integrate>"
---

Use the `task-orchestrator` skill to deliver this request end-to-end:

> ${ARGUMENTS}

Don't jump to editing. Run every phase in order: restructure into a spec
(prompt-architect), investigate the code and confirm the CLAUDE.md, plan in plan
mode before touching files, implement to code-craft standard, run the full quality
rubric (all verticals incl. completeness) fixing every finding, and finish with the
canonical structured report. Nothing left implicit: no placeholders, no silent
scope cuts, no missing pieces.
