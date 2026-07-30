---
name: task-orchestrator
description: The end-to-end workflow for any implementation or change request. Use this WHENEVER the user asks to fix, add, implement, integrate, refactor, update, migrate, optimize, or otherwise change the code-base, even from a one-line prompt like "fix this" or "integrate X". It restructures the request into a spec, investigates the code-base, plans before coding, implements to production standard, runs the full audit (including completeness/no-regression), and returns a precise structured report. Use this instead of jumping straight to editing files.
---

# Task Orchestrator

This is praxis's spine. It turns a terse request into a complete,
production-ready change with nothing left implicit. Run the phases in order; do
not skip ahead to editing. Prioritise correctness and completeness over speed.

The golden rule: **nothing may be silently dropped, stubbed, or left
out-of-scope.** If something cannot be done, it is stated explicitly in the
report, never hidden behind a placeholder.

"Out of scope / follow-ups" is for what the user excluded or what genuinely
belongs to another change. It is not a place to move work you started and did not
finish, and it is not a way to hand back a first pass. Everything the spec puts in
scope, including the error paths, the empty and failure states, the validation,
and the tests, ships in this change.

The second golden rule: **state only what you verified.** Every phase below
produces claims (this passes, that is covered, the docs are updated), and a claim
that turns out on a second look to be untrue costs more than the work it was
meant to save, because it is believed. Run the command instead of predicting its
output, read the file before citing it, and when something could not be checked,
say so in the report. praxis measures what it can: `report.py` runs the tests,
the runtime harness and the scanners itself, and refuses a vertical citation that
does not resolve. What it cannot measure is on you.

Two house rules apply to every phase, and both are enforced deterministically, so
they are not worth testing: **no em dashes** in anything you write (code,
comments, docs, commit messages, or your reply to the user), and **no AI
attribution** in the project's record. Use a colon, a comma, parentheses, or two
sentences instead of the dash, and never add a co-author trailer or a "generated
with" credit.

---

## Phase 1: Restructure the request (spec)
Use the **prompt-architect** skill to convert the request into an explicit spec:
- **Goal**: the outcome, in one or two sentences.
- **In scope**: concrete deliverables.
- **Out of scope / non-goals**: what you will deliberately not do (surface this;
  never narrow scope silently).
- **Acceptance criteria**: testable conditions for "done".
- **Affected areas**: files/subsystems likely touched (fill after Phase 2).
- **Assumptions**: anything you inferred that the user did not state.
- **Open questions**: genuine ambiguities. Ask them now if they block correct
  work; otherwise state the assumption you will proceed under.

Keep the spec tight. Show it to the user when the request was ambiguous or large;
for small unambiguous asks, state the spec briefly and proceed.

**User-facing UI work** runs the **frontend-pipeline** skill around these phases:
business research → story-first wireframes → design system, proportional to the
task. Its artifacts (`docs/design/BRIEF.md`, `WIREFRAMES.md`, `DESIGN-SYSTEM.md`)
become part of the spec, and the audit gains the accessibility and
design-consistency verticals.

Decide this from the *surface the change touches*, not from how the request was
phrased. If the work will add or alter markup, templates, components, styles,
design tokens, or `docs/design/`, it is front-end work even when the prompt said
"fix the checkout bug" or named only a file path. The gate resolves the same
question from the changed file list and rejects the report without both UI
verdicts, so deciding late costs a full re-audit.

## Phase 0: Is praxis set up here, and is this repo ours?

Two questions come before the spec, because both change what the rest of the run
is allowed to do. The session audit answers both, and
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" status` reprints them.

- **Not set up** (`repo_state` is anything but `managed`): run the **bootstrap**
  skill first, in this turn, then continue to Phase 1 without pausing. It writes
  what is absent and only stops to ask when reconciling a brief praxis did not
  author. This is a step of the pipeline, not a command the user has to remember.
- **`contributor` mode**: this repository is not ours. Everything praxis authors
  stays local and git-excluded (`CLAUDE.local.md`, `.claude/settings.local.json`,
  `.claude/.praxis/knowledge/`), the repo's `/docs`, `CHANGELOG.md` and
  `docs/adr/` are joined **only if they already exist** and then on the project's
  terms, and the change you deliver contains nothing but the work the user asked
  for. Do not create a `CLAUDE.md`, a `.praxis.toml`, a `/docs` tree or a
  `CHANGELOG.md`, and do not edit `.gitignore`.

## Phase 2: Investigate (read before you write)
- Confirm the brief hierarchy exists and is accurate (Phase 0 has already
  bootstrapped it if it did not). If memory is stale, run **claudemd-living**.
- **Trust the resolved configuration over any document.** The SessionStart audit
  prints the live values (gate, auto-pilot, auto-merge, base branch, house style);
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" status` reprints them on
  demand. Where a doc contradicts them, the doc is the bug: run
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/drift.py"` and fix what it reports as
  part of Phase 5b.
- **Read the actual code** in the affected areas. Dispatch
  `@praxis:repo-cartographer` for unfamiliar code and
  `@praxis:doc-reference-finder` to pin the authoritative docs and existing
  in-repo patterns. Never code against an unread codebase.
- Fill in **Affected areas** and refine acceptance criteria with what you learned.
- If this is a **monorepo**, identify which package(s) the change belongs to
  (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workspaces.py"`) and use that package's
  build/test commands, not just the repo root's.

## Phase 3: Plan first (plan mode)
Produce a concrete, ordered plan: the steps, the files each touches, the tests to
add/update, and the risks. **Enter plan mode and do not modify files until the
plan is set.** For anything non-trivial, present the plan to the user for
approval; for trivial changes, state the plan in a sentence or two and continue.

A good plan names: the change per file, the new/updated tests, the rollback/road
if something fails, and how each acceptance criterion will be met.

## Phase 4: Implement to the plan
- Follow the plan; if reality forces a deviation, note it and update the plan
  rather than drifting.
- Apply the **best-practices** relevant to this change (use the `best-practices`
  skill's selection table: REST / DDD / OWASP / ACID-CAP / testing / performance
  as the domains require): the minimal fitting set, consistent with existing repo
  patterns, no cargo-culting.
- Apply **code-craft** standards: self-documenting names, comments that explain
  *why* (not *what*), no debug leftovers, no commented-out code, consistent style
  with the surrounding file.
- Reuse existing utilities (no reinvention/duplication), and add only what this
  change needs, no speculative abstractions, parameters, config, or unused
  surface (KISS/YAGNI). Handle the edge cases and errors that are in scope: do not
  stub them.
- Add or update tests alongside the change.

## Phase 5: Audit (prove it's done)
Run the **quality-rubric** skill in full. Scope it with
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scope.py"` first: on a branch that has
already committed subtasks, `git diff` is empty, and an audit scoped that way
reviews nothing and passes everything.
- vertical auditors: doc-reference, duplication, regression, adversarial,
  edge-case, performance, **debt** (`@praxis:debt-auditor`: what this change
  costs later, and whether any of it was recorded), **and completeness**
  (`@praxis:completeness-auditor` + `scan_placeholders.py`);
- horizontal consistency pass;
- **record each verdict with its evidence as the auditor finishes**
  (`report.py vertical <name> --verdict pass --summary "..." --evidence
  "file:line,..."`). Citations are verified to resolve, so a reference you did
  not read is refused at the moment you write it rather than believed;
- fix every FAIL and actionable note, then re-run the affected auditor;
- confirm the test command passes and no regression was introduced;
- **run the product, not only its tests**, for anything a person or another
  system interacts with (the `runtime-verification` skill). A green unit suite
  does not say the page renders or the command exits zero;
- confirm **zero** unacknowledged placeholders/TODOs/stubs and **zero** silently
  narrowed scope;
- run the four deterministic scanners and clear every finding:
  `scan_placeholders.py` (unfinished work, including in untracked new files),
  `scan_style.py` (em dashes, AI attribution), `knowledge_check.py` (the docs
  and changelog this change owes, and any documentation it removed),
  `drift.py` (docs that this change just made untrue);
- confirm the relevant best-practices were actually applied (not just cited).
Record the green quality report so the Stop gate can pass. `report.py record`
runs the tests, the runtime harness and the scanners itself, so a report is
evidence of what happened rather than a summary of what you intended.

## Phase 5b: Update the living knowledge (mandatory)
Documentation is part of "done". Using the `docs-living` skill:
- Update or create the relevant docs under `/docs` for anything this change
  touched (read/search them first; no regression). Seed `/docs` if the repo lacks
  it.
- Add a `[Unreleased]` entry to `CHANGELOG.md`:
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/changelog.py" add --type <added|changed|fixed|removed> "<desc>"`.
- Record any debt this change knowingly took on:
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/debt.py" add "<what>" --interest "<cost>" --principal "<the real fix>" --why "<why now>" --where "<where>"`.
  A shortcut with a written reason is a decision; the same shortcut unrecorded is
  a defect the next person meets without the reason.
- Record an ADR for any significant or autonomously-taken decision:
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/adr.py" new "<title>" --status accepted --context "..." --decision "..." --consequences "..."`.
- Keep `docs/README.md` indexed.
- Check it, rather than believing it:
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/knowledge_check.py"`. It asks whether
  the changelog recorded this change, whether any document moved with the
  behaviour, and whether this change *removed* documentation. The third is the
  one nobody catches by reading a diff, because every other scan reads added
  lines. `report.py record` runs it too, so an unresolved finding here is a
  report that will not go green.

In `contributor` mode the rule is *join what exists, create nothing new*: update
the project's `/docs` and `CHANGELOG.md` if it has them, on its terms, and let
`changelog.py` and `adr.py` place the rest under `.claude/.praxis/knowledge/`.
Both print the path they wrote; read it and report it accurately rather than
claiming the project's changelog was updated when it was not. The guard now
refuses the write outright: creating a `CHANGELOG.md`, a `/docs` skeleton or a
`CLAUDE.md` that the project never had is blocked at the file tool, at the shell,
and at the index, because a pull request carrying one asks reviewers to accept a
convention they never discussed.

## Phase 6: Report (precise, linear, structured)
End with the canonical praxis report. Keep it scannable and complete:

```
## <Task title>

### What changed
- <file/area>: <one-line description of the change>

### How it meets the request
- <acceptance criterion> → <how it is satisfied>

### Quality audit
| Vertical        | Verdict | Notes                    |
| --------------- | ------- | ------------------------ |
| doc-reference   | PASS    | ...                      |
| duplication     | PASS    | ...                      |
| regression      | PASS    | tests: <cmd> green       |
| adversarial     | PASS    | ...                      |
| edge-case       | PASS    | ...                      |
| performance     | PASS    | ...                      |
| debt            | PASS    | what it costs later      |
| completeness    | PASS    | no placeholders/stubs    |

(Add `accessibility` and `design-consistency` rows whenever the change touched
user-facing surface. The report is not green without them.)

### Best-practices applied
- <family> → <how it was applied> (e.g. "REST idempotency → POST uses an idempotency key")

### Decisions taken autonomously
- <decision> → <chosen option>: <one-line best-practice rationale>
  (this section is where auto-pilot records what it would otherwise have asked;
   empty if the user was consulted)

### Tests
- <what was added/updated>; result of <test command>.

### Verified by running it
- <what you actually executed or drove, and what you observed>
- <anything you could NOT verify, and why> (say this plainly; an honest gap is
  actionable, a vague "verified" is a defect the user meets later)

### Docs & knowledge
- Docs updated: <files under /docs>
- CHANGELOG: <the [Unreleased] entry added>
- ADR: <ADR filename, or "none needed">
- Debt recorded: <register entry, or "none taken on">

### Delivery
- Branch / PR: <one per task>
- Subtasks → commits: <n>/<n>, each on its own commit

### Out of scope / follow-ups
- <anything deliberately not done, and why> (empty if none)

### Assumptions made
- <assumptions the user should verify> (empty if none)
```

If any item could not be completed, it goes under **Out of scope / follow-ups**
with the reason: explicitly, never as a hidden gap.

## Phase 7: Deliver (optional, only when needed)
Delivery is a separate, explicit step: praxis does not commit or push on every
edit. When the change is complete and its audit is green, use the `git-delivery`
skill (or `/praxis:ship`) to turn it into a Conventional Commit and a pull request.

Resolve the merge policy rather than recalling it: `config.py status` reports the
value in force and where it came from. With auto-merge off the merge is
human-in-the-loop and praxis stops at the PR; with it on, praxis self-reviews and
merges, but never without a green audit and passing checks, and never by
force-pushing the base branch. In `contributor` mode praxis never merges at all:
it opens the pull request in the project's own style and stops. No commit, tag,
PR, or release carries an AI co-author trailer or a "generated with" credit; the
guard blocks the command.

---

## Autonomous execution: praxis drives the loop, not you

The user states the idea and picks an effort level; everything else is automatic.
Own the whole lifecycle: self-question, investigate, plan, implement, QA, audit,
regression-check, report, without asking the user to drive each step. Interrupt
**only** at a genuine decision point.

**For any multi-step task, open a praxis task at spec time.** This is what makes
the session self-drive to completion: it is praxis's built-in equivalent of
`/goal`, enforced deterministically by the Stop gate. You do **not** ask the user
to run `/goal`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py" open "<task title>" \
  --criteria "criterion 1" "criterion 2" "tests pass" \
  --subtasks "first step" "second step" "third step" --max <turns>
```

Choose `--max` by task size (a normal task ~15, a large migration ~40).

**Give a large task its plan.** A request with more than one deliverable is
decomposed by `prompt-architect` into ordered subtasks, and they go in at `open`
time. The plan is not decoration: the gate reports which subtask is in flight and
what remains, and `task_state.py done` refuses while any of them is unfinished,
so a plan cannot quietly become a smaller piece of work. Re-plan honestly with
`task_state.py plan ...` if the shape of the work genuinely changed; do not
`--force` past a subtask you decided to skip without saying so.

**One task is one unit of delivery.** The task binds to a branch when it opens,
each subtask lands as its own commit, and the whole task becomes one pull
request. That is what makes the work reviewable and the version history
meaningful:

```bash
git checkout -b <type>/<kebab-summary>        # once, at task open
# ... work subtask 1 ...
git commit -m "<type>(<scope>): <subtask 1>"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py" subtask done 1
```

`subtask done` records the commit it landed on, and warns when a subtask shares a
commit with the one before it, because that is the tracking disappearing. Aim for
a pull request whose commit list reads as the plan. See `git-delivery` for the
branch, commit and PR mechanics.

While the task is open, the Stop gate keeps you working turn after turn. Then:

- **Genuine decision point** (real ambiguity, irreversible choice, conflicting
  requirements): run `task_state.py waiting`, then stop and ask the user. Resume
  with `task_state.py resume` after they answer.
  - **In auto-pilot** (`config.py status` / env `PRAXIS_AUTOPILOT`): do NOT
    stop to ask. Resolve the decision yourself with the `best-practices` decision
    procedure, record it under "Decisions taken autonomously", and continue.
    Reserve `waiting` for a hard external blocker you cannot resolve at all (e.g.
    a missing credential), and even then state the assumption you'd proceed under.
- **Finished**: only when EVERY criterion is met and the praxis audit is green,
  run `task_state.py done`. This releases the loop.

The gate has a hard turn cap and standard escapes (`skip-gate`, `PRAXIS_GATE=off`),
so it can never trap the session.

**`/goal` is optional and manual.** The native `/goal` command is a separate
power-tool for handing off a very long, cross-session autonomous run, and can be
paired with auto mode. You never need it for normal work: praxis's task loop
already provides the continuation. Only mention it if the user explicitly wants an
unattended multi-hour run.

## Notes
- Language- and framework-agnostic: derive commands, patterns, and idioms from
  the repo itself.
- **Effort:** praxis is effort-agnostic, it behaves identically whether the
  session is at `/effort high` or `/effort ultracode`; higher effort only deepens
  execution. The vertical auditors are pinned to Opus / high in their frontmatter,
  so audits stay deep regardless. Do not change the user's effort setting.
