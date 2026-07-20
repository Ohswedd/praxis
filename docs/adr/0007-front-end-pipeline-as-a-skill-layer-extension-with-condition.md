# 7. Front-end pipeline as a skill-layer extension with conditional UI verticals

- Status: accepted
- Date: 2026-07-20

## Context
Praxis handled security, consistency, and back-end quality but had no discipline for front-end work: no research/wireframe/design-system workflow, and no accessibility or design-consistency auditing. Front-end requests span every niche (marketing sites, storefronts, lead pages, SaaS UI, CRM/CMS, admin panels, dashboards) and range from full builds to one-line style fixes, so a fixed heavyweight process would violate KISS while no process leaves design quality to chance.

## Decision
Encode the pipeline (research → strategy → wireframes → design system → development → optimization → ship) as a new frontend-pipeline skill that wraps the existing task-orchestrator rather than forking it, with a reference playbook for the deep material and full/feature/patch proportionality routing. Add two read-only vertical auditors — accessibility-auditor (WCAG 2.2 AA) and design-consistency-auditor — dispatched by the quality-rubric only for UI-touching changes and recorded in the evidence report as accessibility=pass,design-consistency=pass (report.py already accepts arbitrary vertical names, so no gate/script changes). Design artifacts live in the target repo under docs/design/ per the docs-living contract. The repo-wide scanner keeps its seven code dimensions: its shard ledger, tests, and coverage accounting are dimension-count-sensitive, and UI dimensions only apply to UI shards; sweeping an existing UI is served by the pipeline's feature route instead.

## Consequences
Praxis covers front-end work end-to-end with the same gates and no new scripts or state files; UI changes cannot go green without the two UI verticals; non-UI changes are unaffected. The always-run vertical set stays at seven, so scan docs remain accurate. Extending /praxis:scan with UI dimensions is deliberate future work if demand appears.
