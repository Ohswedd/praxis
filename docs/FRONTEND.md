# The Front-End Pipeline (`/praxis:frontend`)

Praxis treats front-end work the way agencies that ship converting sites do:
**the interface solves a business problem, not fills a page.** The
`frontend-pipeline` skill encodes that discipline for any UI niche — marketing
sites, landing/lead pages, storefronts, SaaS product UI, CRM/CMS, admin
panels, dashboards — with the same gates, auditors, and living-knowledge
contract as every other praxis change.

```
RESEARCH → STRATEGY → WIREFRAMES → DESIGN SYSTEM → DEVELOPMENT → OPTIMIZATION → SHIP
```

## The three phases

**Phase 1 — Research.** The six steps that anchor the build in the business:
client call (business, goals, challenges) → measurable business goals →
target audience personas → competitor analysis (gaps and opportunities) →
positioning (the unique value proposition) → messaging (copy that connects
and converts). Output: `docs/design/BRIEF.md` in the target repo.

**Phase 2 — Story first.** Wireframes define what users should *feel*, not
just what they should see. Each page gets a conversion (or task) goal and a
narrative arc — hero, problem, solution, benefits, social proof, pricing,
CTA for public pages; overview → drill-down → action for admin surfaces —
and every section specifies message / feel / evidence / action. Output:
`docs/design/WIREFRAMES.md`.

**Phase 3 — Execute. Consistency creates trust.** A design system (brand
identity, typography and spacing scales, color tokens with contrast verified
at definition, components with full states) becomes the single source of
truth — then development runs through the standard task-orchestrator with the
front-end best-practices, then optimization, then ship. Output:
`docs/design/DESIGN-SYSTEM.md` + tokens in code.

## How it maps to the praxis layers

| Layer | Front-end addition |
| --- | --- |
| Output style | "Front-end: design before pixels" doctrine, always on |
| Skills | `frontend-pipeline` (+ its reference playbook: question banks, narrative arcs per niche, wireframe format, design-system checklist, artifact templates) |
| Subagents | `accessibility-auditor` (WCAG 2.2 AA) and `design-consistency-auditor` (tokens, scales, component reuse, states, responsiveness, story fidelity) — read-only, Opus, dispatched by the quality-rubric for any UI-touching change; the performance vertical covers Core Web Vitals for UI scope |
| Hooks | unchanged — the same Stop gate refuses to finish an unreviewed change; the rubric records UI changes with `accessibility=pass,design-consistency=pass` in the evidence report (guided and gated by the report, like every vertical — see FLOWS.md §9) |

## Proportionality (no cargo-cult discovery)

The pipeline routes each request before running anything:

- **full** — new site/app/storefront or a redesign: all phases.
- **feature** — a new page/screen/component in an existing UI: inherit
  `docs/design/`, delta-check the brief, then wireframe → build → optimize.
- **patch** — a small UI fix: straight to development with design-system
  compliance; the UI verticals still run.

Competitor analysis for a button fix is as much a defect as a missing design
system for a new product.

## The artifacts are living knowledge

`docs/design/BRIEF.md`, `WIREFRAMES.md`, and `DESIGN-SYSTEM.md` live in the
*target* repo under the docs-living contract: read before every UI change,
updated when the design evolves, never allowed to drift from what shipped.
They are how the next feature stays consistent with the last one — and they
make design decisions auditable (auto-pilot records significant ones as ADRs).

## Scope notes

- The repo-wide scanner (`/praxis:scan`) keeps its seven code dimensions; the
  UI verticals run in the change audit. To sweep an existing UI for
  accessibility/consistency debt, run `/praxis:frontend` in `feature` mode on
  the surface in question (see ADR-0007).
- Internal tools count: for a CRM or dashboard, the "audience" is operator
  roles, "conversion" is task completion, and "competitors" are the
  spreadsheets and legacy tools users would fall back to.
- Stack-agnostic by construction: the skill derives framework, styling idiom,
  and token format from the repo and the authoritative docs — praxis ships the
  workflow, the model supplies the stack specifics at runtime.
