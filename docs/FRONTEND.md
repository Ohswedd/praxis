# The Front-End Pipeline

Praxis treats front-end work the way agencies that ship converting sites do:
**the interface solves a business problem, not fills a page.** The
`frontend-pipeline` skill encodes that discipline for any UI niche: marketing
sites, landing/lead pages, storefronts, SaaS product UI, CRM/CMS, admin
panels, dashboards, with the same gates, auditors, and living-knowledge
contract as every other praxis change.

```
RESEARCH → STRATEGY → WIREFRAMES → DESIGN SYSTEM → DEVELOPMENT → OPTIMIZATION → SHIP
```

## There is no command for this

The pipeline is engaged by the *surface a change touches*, never by a word the
user typed. Three mechanisms do it, and every one of them works from files:

1. the prompt router recognises UI language and UI file names in the request;
2. the task-orchestrator wraps its phases around this pipeline whenever the work
   will add or alter markup, templates, components, styles, tokens, or
   `docs/design/`;
3. the Stop gate resolves the same question from the changed file list and
   refuses a report without `accessibility=pass` and `design-consistency=pass`.

Praxis 2.x also had a `/praxis:frontend` command. It was removed in 3.0 because a <!-- praxis:ack: naming the removed command is the point of this paragraph -->
fourth entry point could only ever be used wrongly: typed after the design
decisions had already been made, or, far more often, not typed at all for the
"fix the checkout bug" that was front-end work all along. See ADR-0020.

## The three phases

**Phase 1: Research.** The six steps that anchor the build in the business:
client call (business, goals, challenges) → measurable business goals →
target audience personas → competitor analysis (gaps and opportunities) →
positioning (the unique value proposition) → messaging (copy that connects
and converts). Output: `docs/design/BRIEF.md` in the target repo.

**Phase 2: Story first.** Wireframes define what users should *feel*, not
just what they should see. Each page gets a conversion (or task) goal and a
narrative arc: hero, problem, solution, benefits, social proof, pricing,
CTA for public pages; overview → drill-down → action for admin surfaces,
and every section specifies message / feel / evidence / action. Output:
`docs/design/WIREFRAMES.md`.

**Phase 3: Execute. Consistency creates trust.** A design system (brand
identity, typography and spacing scales, color tokens with contrast verified
at definition, components with full states) becomes the single source of
truth, then development runs through the standard task-orchestrator with the
front-end best-practices, then optimization, then ship. Output:
`docs/design/DESIGN-SYSTEM.md` + tokens in code.

## How it maps to the praxis layers

| Layer | Front-end addition |
| --- | --- |
| Output style | "Front-end: design before pixels" doctrine, always on |
| Skills | `frontend-pipeline` + two references: **`playbook.md`** (question banks, narrative arcs per niche, wireframe format, design-system checklist, artifact templates) and **`craft.md`** (the visual judgement checklists can't encode, the tells of generated UI and what to do instead, hierarchy, typography, space, colour, depth, motion, the detail pass). The playbook makes an interface correct; craft.md is what makes it designed |
| Subagents | `accessibility-auditor` (WCAG 2.2 AA) and `design-consistency-auditor` (tokens, scales, component reuse, states, responsiveness, story fidelity): read-only, Opus, dispatched by the quality-rubric for any UI-touching change; the performance vertical covers Core Web Vitals for UI scope |
| Hooks | unchanged (the same Stop gate refuses to finish an unreviewed change; the rubric records UI changes with `accessibility=pass,design-consistency=pass` in the evidence report (guided and gated by the report, like every vertical) see FLOWS.md §9) |

## Proportionality (no cargo-cult discovery)

The pipeline routes each request before running anything:

- **full**: a new site, app, or storefront, or a redesign. Every phase runs.
- **feature**: a new page/screen/component in an existing UI: inherit
  `docs/design/`, delta-check the brief, then wireframe → build → optimize.
- **patch**: a small UI fix. Straight to development with design-system
  compliance; the UI verticals still run.

Competitor analysis for a button fix is as much a defect as a missing design
system for a new product.

## The artifacts are living knowledge

`docs/design/BRIEF.md`, `WIREFRAMES.md`, and `DESIGN-SYSTEM.md` live in the
*target* repo under the docs-living contract: read before every UI change,
updated when the design evolves, never allowed to drift from what shipped.
They are how the next feature stays consistent with the last one, and they
make design decisions auditable (auto-pilot records significant ones as ADRs).

In `contributor` mode they follow the same rule as the rest of the living
knowledge: the repo's `docs/design/` is joined if it exists, and otherwise the
artifacts are kept under `.claude/.praxis/knowledge/docs/design/`, which is
git-excluded. A project that does not keep design artifacts did not ask a
contributor to introduce them; the tokens still ship in code either way. See
[MODES.md](MODES.md).

## Scope notes

- The repo-wide scanner (`/praxis:audit repo`) keeps its eight code dimensions; the
  UI verticals run in the change audit. To sweep an existing UI for
  accessibility/consistency debt, ask for the surface in question by name
  ("audit the checkout screens for accessibility"): the router sends it through
  this pipeline in `feature` mode (see ADR-0007).
- Internal tools count: for a CRM or dashboard, the "audience" is operator
  roles, "conversion" is task completion, and "competitors" are the
  spreadsheets and legacy tools users would fall back to.
- Stack-agnostic by construction: the skill derives framework, styling idiom,
  and token format from the repo and the authoritative docs: praxis ships the
  workflow, the model supplies the stack specifics at runtime.
