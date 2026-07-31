---
name: quality-rubric
description: Run praxis's full quality review on a code change. Use this whenever you finish a non-trivial edit, before declaring work done, when the Stop gate reports an unreviewed change, or when the user asks for a review, audit, or quality check. Dispatches the vertical auditors (adversarial, regression, duplication, performance, edge-case, doc-reference, technical debt, completeness, plus accessibility and design-consistency on UI changes) and a horizontal consistency pass, then records a green report so the quality gate can pass. Always use this before finishing coding work.
---

# Quality Rubric

This skill is praxis's review engine. It turns "did we check everything?" from
a per-prompt checklist into a repeatable, gated workflow. Invoke it via
`/praxis:audit` or automatically after meaningful code changes.

Prefer maximum thoroughness: run high effort, and do not shortcut the vertical
passes. Quality is the priority over speed.

## Step 1: Scope the change (the branch, not the working tree)

A change does not stop being a change by being committed. Scope it as everything
this branch has done since it left its base, plus whatever is still uncommitted:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scope.py"     # base, commits, files, stats
```

That prints the review base and the exact commands for the diff. Use them:

- `git diff <base>...HEAD` for what the branch has already committed, and
  `git log <base>..HEAD` for the commits themselves. Reviewing commit by commit
  is often faster than one large diff, and it shows the *order* the work was
  done in, which is where an accidental revert or a fix-up of a bug this same
  branch introduced becomes obvious.
- `git diff` and `git diff --staged` for what is not committed yet.
- Untracked files: they are part of the change and appear in no diff at all.

**Never scope a review with `git diff` alone.** On a branch that has committed
anything, it is empty, and every auditor then reviews nothing and reports PASS.
Praxis's own helpers (`changed_files`, the scanners, the change signature, the
Stop gate) all use the branch scope, so a review that used the working tree alone
would be narrower than the gate that judges it.

Then map the blast radius: callers, callees, shared state, public contracts,
tests, and docs affected by the change.

**Pass the scope into every dispatch.** The auditors are read-only (`Read`,
`Grep`, `Glob`) and have no shell, so they cannot run `scope.py` or `git`
themselves: the base is a fact you hand them, not one they can discover. Every
auditor prompt must state the base commit, the commits on the branch, and the
files under review. An auditor told only "review the staged change" will read the
working tree, find nothing on a branch that has committed its work, and return
PASS. If you cannot resolve a base, say so in the prompt so the auditor reports
the gap instead of reporting clean.

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
- `@praxis:debt-auditor`: what this change will cost later. Shortcuts and
  workarounds, coupling and hand-synchronised duplication it creates,
  abstractions it has made wrong, deprecated or pinned dependencies it leans on,
  tests that lock in implementation, and whether debt it knowingly took on was
  **recorded** (`debt.py add`) or left silent. Recording is usually the cheapest
  correct resolution: this vertical is not a demand to refactor what the change
  did not come to fix.
- `@praxis:completeness-auditor`: no placeholders/stubs/TODOs, no debug or
  dead code, and no scope silently dropped relative to the spec; every acceptance
  criterion met. Back it with the deterministic scan:
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/scan_placeholders.py --json`. That scan
  covers the branch's commits, the working tree, **and** every untracked file, so
  neither a committed subtask nor a brand-new file is invisible to it.

**UI-touching changes** (markup/templates, components, styles, `docs/design/`,
client-side view logic) additionally dispatch the two UI verticals. These are not
optional and not a judgement call: the gate resolves "does this change touch UI"
from the changed file list, and a report without both verdicts is rejected.

- `@praxis:accessibility-auditor`: WCAG semantics, keyboard, focus, contrast,
  forms, ARIA, media, and motion.
- `@praxis:design-consistency-auditor`: design-token adherence (no magic
  values), scale discipline, component reuse, state completeness, responsive
  coverage, story fidelity per `docs/design/`.

Each auditor returns `PASS`, `PASS WITH NOTES`, or `FAIL` plus specifics.

**Record each verdict as its auditor finishes, with the evidence behind it.**
This is not bookkeeping: a verdict nobody had to substantiate is a verdict nobody
had to reach, and a `file:line` that does not resolve is the signature of an
audit that did not happen.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" vertical regression \
  --verdict pass \
  --summary "Every caller of parse_range() re-checked; the two in cli.py pass \
pre-validated input, and the new bound is inclusive as before." \
  --evidence "src/parse.py:88-114,src/cli.py:230"
```

`report.py vertical` **refuses a citation that does not resolve**: a file that
does not exist, a line past the end of one. That refusal is deliberate and it is
the point. An auditor that read the code can name what it read for free; an audit
that was assumed cannot, and inventing a reference is caught at the only moment
it is still cheap to check. `report.py record` then refuses to claim a verdict
the ledger does not carry (`gate.require_evidence`).

If an auditor is not available as a subagent in the current surface, perform its
pass inline using the same checklist (see each agent file), and record it the
same way: doing the work inline is fine, asserting it is not.

## Step 2b: The deterministic checks (run them, do not reason about them)

Four scanners answer questions no amount of reading a diff answers reliably.
Run them and treat every finding as a `FAIL`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scan_placeholders.py"   # unfinished work
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scan_style.py"          # em dashes, AI credits
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/knowledge_check.py"     # docs that did not move
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/drift.py"               # docs vs live config
```

`scan_style.py` covers the house rules that prose alone has repeatedly failed to
hold: no em dash anywhere in authored text, and no AI co-author or "generated
with" credit. `knowledge_check.py` asks whether the changelog and the docs moved
with the behaviour, and whether this change *removed* documentation, which is the
one regression a diff of added lines cannot see. `drift.py` catches documentation
that this change just made untrue.

`report.py record` runs the first three itself and records what they found, so
these are not a checklist you can tick: a report is not green while any of them
has an unresolved finding. Running them here is how you find out before the
report does.

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

## Step 4b: Run the thing, not only its tests

A change to anything a person or another system interacts with is verified
against the running product before it is called done. A passing unit suite says a
function returns what its test expects; it does not say the page renders, the
route answers, or the command exits zero. Use the **runtime-verification** skill:
it picks the right execution for this project, drives a browser when the surface
is visual, and says what to do when the project has no harness.

`report.py` runs the project's end-to-end harness itself when the change touches
user-facing files and one exists (`gate.require_runtime`), so this is measured
rather than reported, exactly like the test suite.

## Step 5: Record the green report (with evidence)
Record it **last**, after the docs/CHANGELOG/ADR updates and any other write the
change needs. The report is keyed to the change signature, so a file written
afterwards re-keys it and the gate will correctly reject the audit as stale:
costing you a full re-run.

When all passes are green: 

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" record \
  --verticals "doc-reference=pass,duplication=pass,regression=pass,adversarial=pass,edge-case=pass,performance=pass,debt=pass,completeness=pass"
```

**Nothing in that command is taken on trust.** `report.py` runs the project's
test command, the end-to-end harness where one is owed, and the three
deterministic scanners, and records their real results; then it checks that every
verdict in `--verticals` has a matching ledger entry from Step 2. A self-reported
pass is a claim, and the gate's guarantee is only as strong as its weakest input.

- `--tests "<cmd>"` overrides the auto-detected suite (the specific package in a
  monorepo), `--timeout <seconds>` for a slow one. An override is recorded as a
  substitution and does not buy a green gate on its own.
- `--runtime "<cmd>"` overrides the detected end-to-end command,
  `--runtime-timeout <seconds>` for a slow one.
- `--knowledge-ack "<reason>"` is the only escape from a living-knowledge
  finding, and it records the reason in the report rather than dropping it. Use
  it when the change genuinely needed no document, never to move on.

Expect the record step to take as long as the suite does, and read its output: if
anything comes back non-zero or unresolved, the report is written as `fail` and
the gate will keep you working. Fix the cause: do not re-record around it.

When the change touches user-facing surface, extend the string with
`,accessibility=pass,design-consistency=pass`. `report.py` resolves that from the
changed files itself and records the report as `fail` if the two verdicts are
missing, so the only way past it is to actually run the two auditors.

If the repo genuinely has no test command, the report is recorded without a test
requirement; say so to the user and note the missing coverage.

## Output to the user
Give a compact verdict table with one row per vertical (doc-reference,
duplication, regression, adversarial, edge-case, performance, debt,
completeness: plus accessibility and design-consistency when the change touched
UI), the
horizontal summary, the fixes applied, and any accepted notes. Keep it scannable.
When this rubric runs as part of a full task, fold the table into the
task-orchestrator's canonical report rather than duplicating it.
