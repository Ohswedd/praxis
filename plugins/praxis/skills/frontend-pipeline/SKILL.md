---
name: frontend-pipeline
description: "Design and build user-facing front-ends to professional standard — any niche: marketing sites, landing/lead pages, storefronts/e-commerce, SaaS product UI, CRM/CMS, admin panels, dashboards. Use WHENEVER the request creates or substantially changes a user-facing interface (\"build a site for…\", \"make a landing page\", \"add a dashboard\", \"redesign the app\"), or when the user runs /praxis:frontend. Runs the full pipeline: business research (client call, goals, audience, competitors, positioning, messaging) → story-first wireframes → design system → development via the task-orchestrator → optimization with the accessibility and design-consistency verticals → ship. Proportional to task size; small UI fixes inherit the existing design system instead of re-running discovery."
---

# Front-End Pipeline

A website (or storefront, lead page, admin panel, dashboard…) must **solve a
business problem, not just fill a page**. This skill turns a front-end request
into the same disciplined pipeline praxis applies to any change — with the
design work made explicit instead of improvised:

```
RESEARCH → STRATEGY → WIREFRAMES → DESIGN SYSTEM → DEVELOPMENT → OPTIMIZATION → SHIP
```

It **wraps** the task-orchestrator, it does not replace it: the same spec/plan
discipline, the same Stop gate, the same quality rubric — plus the design
phases and two extra vertical auditors for UI surface. Consistency creates
trust; the pipeline is how consistency survives the project.

Two references carry the depth; read them rather than reinventing their content
inline:

- **`reference/playbook.md`** — question banks, narrative patterns, wireframe
  format, design-system checklist, per-niche adaptations, artifact templates.
  Read when executing Phases 1–4.
- **`reference/craft.md`** — the visual judgement the checklists cannot encode:
  the tells of generated UI and what to do instead, hierarchy, typography,
  space, colour, depth, motion, and the detail pass. **Read it before writing
  any markup or styles, and again in Phase 5.** The playbook makes an interface
  correct; craft.md is what makes it designed. Skipping it is how a
  system-compliant page still ships looking generic.

Both live under `${CLAUDE_PLUGIN_ROOT}/skills/frontend-pipeline/reference/`.

---

## Phase 0 — Route and size (proportionality is mandatory)

Open a praxis task (multi-step work) and classify the request:

| Route | When | Phases to run |
| --- | --- | --- |
| `full` | new site/app/storefront, a new product surface, or a redesign | all phases |
| `feature` | a new page, section, screen, or component inside an existing UI | inherit `docs/design/` (brief + system); Phase 1 as a delta check; then 2 → 6 for the new surface. If no brief/system exists yet, establish the minimal missing foundations first (treat those pieces as `full`) |
| `patch` | copy tweak, style fix, small component change | straight to Phase 4 with design-system compliance; UI verticals still run in Phase 5 |

Never run competitor analysis for a button fix; never build a new page without
the wireframe/story pass; never invent one-off styles when a design system
exists. If `docs/design/` exists, it is the source of truth — read it first and
**extend it, never fork it**.

## Phase 1 — Research (know the business before the pixels)

Work through the six research steps, in order. In interactive mode, ask the
user the client-call questions (batched, not one-by-one); in auto-pilot or when
the user has provided materials, derive the answers from what exists and record
every inference under assumptions.

1. **Client call** — understand the business, goals, and challenges: what is
   sold/offered, to whom, what works today, what blocks growth, brand assets
   and content that already exist, technical constraints.
2. **Business goals** — define success measurably: what must this interface
   *achieve* (conversions, sign-ups, booked demos, sales, support deflection —
   or, for internal tools, task time, error rate, adoption). Every page gets a
   primary goal.
3. **Target audience** — who you are talking to and what they care about:
   personas with needs, objections, awareness level, device/context.
4. **Competitor analysis** — study 3–5 direct competitors or comparable tools
   (use WebSearch/WebFetch when available): their messaging, page structure,
   strengths — and the gaps that are your opportunity.
5. **Positioning** — craft the unique value proposition that sets this offer
   apart (formula and worked examples in the playbook).
6. **Messaging** — turn the positioning into copy that connects and converts:
   headline, supporting points, proof, objection handling, voice and tone.

**Artifact:** write `docs/design/BRIEF.md` in the target repo (template in the
playbook). The brief is living knowledge under the docs-living contract — every
later phase traces back to it.

## Phase 2 — Story-first structure (wireframes define what users should *feel*)

Design the story before any visual design:

- **Page map** — every page/screen, its audience, and its single conversion
  goal.
- **Narrative arc per page** — the classic conversion arc for public pages
  (hero → problem → solution → benefits → social proof → objections/FAQ →
  pricing → final CTA) or the task arc for product/admin surfaces (overview →
  drill-down → action). Patterns per niche are in the playbook.
- **Per section, specify four things:** the *message* (one sentence), the
  *feel* (what the visitor should feel or conclude), the *evidence* (what
  proves it), and the *action* (CTA, if any). A section that has none of these
  is cut.
- **Wireframe as a structure spec** — low-fi markdown skeleton (playbook
  format): hierarchy and content priority, not pixels.

**Artifact:** `docs/design/WIREFRAMES.md`. In interactive mode this is a
genuine decision point — present the brief + wireframes for approval before
visual design (mark the praxis task `waiting`). In auto-pilot, proceed and
record the direction under "Decisions taken autonomously".

## Phase 3 — Design system (consistency creates trust)

Define the system before styling any single page, sized to the project (a
landing page needs a lean kit, a product UI needs a real component library):

- **Brand identity** — 3–5 personality adjectives from the brief, translated
  into a visual direction. Every token below traces to one of them: a palette,
  a type family, or a radius you cannot justify from the brief is a default you
  accepted rather than a decision you made (craft.md §1).
- **Typography** — one or two families, a modular scale, line-height and
  measure rules.
- **Color** — base/neutral/accent/semantic roles as tokens, with WCAG AA
  contrast verified at definition time (not discovered later by the auditor).
- **Spacing & shape** — a single spacing scale, radii, borders, elevation.
- **Components** — buttons with variants *and states* (hover, focus, active,
  disabled, loading), forms with validation states, cards, navigation, and the
  niche's workhorses (tables/filters for admin, product cards/cart for
  storefronts), plus empty/loading/error patterns.

**Tokens are the single source of truth**, expressed in the stack's native form
(CSS custom properties, Tailwind theme, framework theme object — derive from
the repo; never impose a foreign convention).

**Artifact:** `docs/design/DESIGN-SYSTEM.md` + the token implementation in
code. If the repo already has a system, this phase is an audit-and-extend of
it, never a parallel one (duplication is a defect).

## Phase 4 — Development (the standard praxis pipeline, with front-end standards)

Hand implementation to the **task-orchestrator** (spec → investigate → plan →
implement → audit), holding the development standards of playbook §11
throughout: semantic HTML with accessibility built in, responsive from the
start, component states shipped (loading/empty/error/disabled), the
performance budget honoured, and **zero hard-coded values where a token
exists** — with the front-end families from the **best-practices** catalog
applied alongside the repo's own conventions. Copy comes from the messaging in
the brief — not lorem ipsum, not improvised.

Hold `craft.md` alongside §11 while you build. §11 keeps the interface correct;
craft.md keeps it from reading as generated — name the focal element of each
screen before you lay it out, take every §1 tell as a defect rather than a
matter of taste, and design each state with real copy rather than leaving the
framework's default. Build with real content at real lengths, including the
long and the empty cases.

## Phase 5 — Optimization & QA (prove it, don't eyeball it)

1. **Run the real thing.** Launch the app/site and walk every flow at the
   breakpoints and states the change claims to support (use the session's
   browser/run tooling when available). Screenshots or observed behaviour beat
   assumptions.
2. **Full quality rubric** — all seven verticals **plus the UI verticals**:
   `@praxis:accessibility-auditor` and `@praxis:design-consistency-auditor`
   (the quality-rubric skill dispatches them automatically for UI-touching
   changes; the perf vertical covers Core Web Vitals for UI scope).
3. **Craft pass** — work the `craft.md` §10 checklist yourself: focal element
   and squint test per screen, headings-only story, no §1 tells, motion that
   explains change, every state designed with real copy, detail pass clean at
   320px / 768px / 1440px / 200% zoom. Each "no" is a finding, not a taste
   argument.
4. **Copy pass** — headlines state the value, CTAs state the action, error
   messages help recovery, voice matches the brief, and no proof (quote, logo,
   rating, metric) is invented.
5. Fix every finding, then record the green report with the extended verticals
   string (see quality-rubric Step 5).

## Phase 6 — Ship & keep the knowledge alive

- **docs-living:** the design artifacts under `docs/design/` are updated to
  match what shipped (no drift), `CHANGELOG.md` gets its `[Unreleased]` entry,
  and an ADR records any significant design decision taken autonomously
  (chosen positioning, visual direction, framework choice).
- **git-delivery** (`/praxis:ship`) when the user wants the change delivered:
  Conventional Commit → branch → PR, human-in-the-loop merge by default.
- Mark the praxis task `done` only when every acceptance criterion from the
  brief is met and the audit is green.

---

## Notes

- **Niche-agnostic:** marketing site, storefront, lead page, SaaS app, CRM,
  CMS, admin panel, dashboard — the pipeline is the same; the playbook maps
  goals/audience/arcs per niche (for internal tools, "conversion" = task
  efficiency and "competitors" = the current workflow). For native/mobile
  surfaces the principles transfer but the web citations don't: map WCAG/ARIA
  and Core Web Vitals to the platform's own accessibility and performance
  guidelines.
- **Stack-agnostic:** derive framework, styling approach, and component idioms
  from the repo and the authoritative docs for the versions in use —
  documentation-first, like every praxis change.
- **Effort-agnostic:** identical behaviour at any effort level; higher effort
  only deepens research and QA. The UI auditors are pinned to Opus/high.
