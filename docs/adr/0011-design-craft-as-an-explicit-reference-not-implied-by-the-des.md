# 11. Design craft as an explicit reference, not implied by the design system

- Status: accepted
- Date: 2026-07-21

## Context
The front-end pipeline made interfaces correct — tokens, states, contrast, semantics, budgets — and assumed craft would follow from that discipline. It does not. A page can satisfy every checklist item and still read as generated, because the checklists constrain mistakes without supplying judgement. The reported symptom was UI that was consistently and accessibly generic: centered everything, a violet gradient hero, three equal cards, stock icons standing in for evidence, framework-default accents, lorem ipsum. Consistency auditing could not catch it, because a uniformly generic page is perfectly consistent.

## Decision
Add reference/craft.md as a peer of the playbook, named as required reading before any markup or styles and again in the Phase 5 craft pass. It states the tells of generated UI with the design decision each one replaces, then the judgement behind them: hierarchy and the squint test, typographic and spatial discipline, colour restraint, earned depth, a motion budget, content-shaped states, and a detail pass. The design-consistency-auditor gains a matching craft vertical so the tells are FAILs rather than taste arguments, and invented proof (a fabricated quote, logo, rating, or metric) is a hard FAIL.

## Consequences
Generic output becomes a citable defect with a named fix instead of a vague dissatisfaction. The premise is explicit — generic is a decision too, and almost always the wrong one — so every accepted default now needs a justification traceable to the brief. Risk: craft guidance is more opinionated than a checklist and could be cargo-culted into places it does not fit, so craft.md states that a brief-justified choice resembling a tell is a documented divergence, not drift.
