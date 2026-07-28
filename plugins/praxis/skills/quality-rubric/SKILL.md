---
name: quality-rubric
description: Run praxis's full quality review on a code change. Use this whenever you finish a non-trivial edit, before declaring work done, when the Stop gate reports an unreviewed change, or when the user asks for a review, audit, or quality check. Dispatches the vertical auditors (adversarial, regression, duplication, performance, edge-case, doc-reference, completeness, plus accessibility and design-consistency on UI changes) and a horizontal consistency pass, then records a green report so the quality gate can pass. Always use this before finishing coding work.
---

# Quality Rubric

This skill is praxis's review engine. It turns "did we check everything?" from
a per-prompt checklist into a repeatable, gated workflow. Invoke it via
`/praxis:audit` or automatically after meaningful code changes.

Prefer maximum thoroughness: run high effort, and do not shortcut the vertical
passes. Quality is the priority over speed.

## Step 1: Scope the change
Identify exactly what changed and what it touches:
- `git diff` (and `git diff --staged`) for the current change set.
- Map the blast radius: callers, callees, shared state, public contracts, tests,
  and docs affected by the diff.

## Step 2: Vertical analysis (dispatch the auditors)
Run each concern as its own read-only subagent so their (verbose) analysis stays
out of the main context. Dispatch them and collect verdicts. Use the plugin
agents:

- `@praxis:doc-reference-finder`: confirm the change follows authoritative
  docs and existing in-repo patterns; flag any reinvented wheel.
- `@praxis:duplication-scanner`: find duplicated or near-duplicated logic,
  existing utilities that should have been reused, and over-engineering the change
  doesn't need (speculative abstractions, unused surface, needless indirection).
- `@praxis:regression-sentinel`: find behaviours/contracts/tests the change
  may have broken.
- `@praxis:adversarial-auditor`: try to break it on security, abuse, unsafe
  states, injection, and unvalidated input.
- `@praxis:edge-case-hunter`: enumerate boundary/null/concurrency/error cases
  and check each is handled.
- `@praxis:perf-scalability-analyst`: complexity, hot paths, N+1, growth.
- `@praxis:completeness-auditor`: no placeholders/stubs/TODOs, no debug or
  dead code, and no scope silently dropped relative to the spec; every acceptance
  criterion met. Back it with the deterministic scan:
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scan_placeholders.py --json`. That scan
  covers the unstaged diff, the staged diff, **and** every untracked file, so a
  brand-new file is not invisible to it.

**UI-touching changes** (markup/templates, components, styles, `docs/design/`,
client-side view logic) additionally dispatch the two UI verticals. These are not
optional and not a judgement call: the gate resolves "does this change touch UI"
from the changed file list, and a report without both verdicts is rejected.

- `@praxis:accessibility-auditor`: WCAG semantics, keyboard, focus, contrast,
  forms, ARIA, media, and motion.
- `@praxis:design-consistency-auditor`: design-token adherence (no magic
  values), scale discipline, component reuse, state completeness, responsive
  coverage, story fidelity per `docs/design/`.

Each auditor returns `PASS`, `PASS WITH NOTES`, or `FAIL` plus specifics. If an
auditor is not available as a subagent in the current surface, perform its pass
inline using the same checklist (see each agent file for the checklist).

## Step 2b: The deterministic checks (run them, do not reason about them)

Three scanners answer questions no amount of reading a diff answers reliably.
Run all three and treat every finding as a `FAIL`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scan_placeholders.py"   # unfinished work
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scan_style.py"          # em dashes, AI credits
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/drift.py"               # docs vs live config
```

`scan_style.py` covers the house rules that prose alone has repeatedly failed to
hold: no em dash anywhere in authored text, and no AI co-author or "generated
with" credit. `drift.py` catches the documentation that this change just made
untrue. All three also run inside the Stop gate, so skipping them here only moves
the work later.

## Step 3: Horizontal pass
With the vertical verdicts in hand, do one cross-cutting review yourself:
- Consistency: does the change read as one coherent whole across every file it
  touches, and with the surrounding system?
- Use-case coverage: are the real user scenarios satisfied end-to-end, not just
  the happy path?
- Guideline compliance: lint/style/tests/CI expectations met.
- Best-practices: the relevant families (via the `best-practices` skill) were
  actually applied for this change's domains, not merely cited, and not
  over-applied.
- Living knowledge: `/docs`, `CHANGELOG.md`, ADRs and the CLAUDE.md hierarchy
  still describe reality after this change, and `drift.py` is clean.
- Small things: names, messages, types, comments, docs updated.

## Step 4: Resolve, don't defer
For every `FAIL` or actionable note: fix it, then re-run the affected auditor.
Keep iterating until all verticals are `PASS` (or `PASS WITH NOTES` that the user
has explicitly accepted). Do not mark the work done with an open `FAIL`.

This iterate-until-green loop is enforced automatically: praxis's Stop gate
(a Stop hook) refuses to end the turn while the change is unreviewed, so you keep
working without the user re-prompting. That is praxis's own persistence
mechanism and needs no command. The native `/goal` command is a *separate,
optional* layer for driving a whole multi-step task to a user-defined finish line
across many turns (see the task-orchestrator skill). Use it for large tasks, not
for closing out a single change here.

## Step 5: Record the green report (with evidence)
Record it **last**, after the docs/CHANGELOG/ADR updates and any other write the
change needs. The report is keyed to the change signature, so a file written
afterwards re-keys it and the gate will correctly reject the audit as stale:
costing you a full re-run.

When all passes are green: 

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" record \
  --verticals "doc-reference=pass,duplication=pass,regression=pass,adversarial=pass,edge-case=pass,performance=pass,completeness=pass"
```

`report.py` **runs the project's test command itself** and records the real exit
code: it does not accept one you report. That is deliberate: a self-reported
pass is a claim, and the gate's guarantee is only as strong as its weakest input.
It auto-detects the command; pass `--tests "<cmd>"` to override it (e.g. the
specific package in a monorepo) and `--timeout <seconds>` for a slow suite.

Expect the record step to take as long as the suite does, and read its output: if
it prints a non-zero exit, the report is written as `fail` and the gate will keep
you working. Fix the failure: do not re-record around it.

When the change touches user-facing surface, extend the string with
`,accessibility=pass,design-consistency=pass`. `report.py` resolves that from the
changed files itself and records the report as `fail` if the two verdicts are
missing, so the only way past it is to actually run the two auditors.

If the repo genuinely has no test command, the report is recorded without a test
requirement; say so to the user and note the missing coverage.

## Output to the user
Give a compact verdict table with one row per vertical (doc-reference,
duplication, regression, adversarial, edge-case, performance, completeness:
plus accessibility and design-consistency when the change touched UI), the
horizontal summary, the fixes applied, and any accepted notes. Keep it scannable.
When this rubric runs as part of a full task, fold the table into the
task-orchestrator's canonical report rather than duplicating it.
