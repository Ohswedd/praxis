---
description: "Run the front-end pipeline: research → story wireframes → design system → development → optimization → ship."
argument-hint: "<what to build / redesign / improve>"
---

Use the `frontend-pipeline` skill end-to-end on:

> ${ARGUMENTS}

Route it first (full / feature / patch — proportional to the request), then run
the phases in order: business research (client call, goals, audience,
competitors, positioning, messaging → `docs/design/BRIEF.md`), story-first
wireframes (`docs/design/WIREFRAMES.md`), design system
(`docs/design/DESIGN-SYSTEM.md` + tokens in code), development via the
task-orchestrator with the front-end best-practices, optimization with the full
quality rubric **including** `@praxis:accessibility-auditor` and
`@praxis:design-consistency-auditor`, and delivery on request.

The interface must solve a business problem, not fill a page: every page has a
goal, every section has a message/feel/evidence/action, and everything visual
comes from the design system — no magic values, no one-off variants, no lorem
ipsum.
