---
name: task-orchestrator
description: The end-to-end workflow for any implementation or change request. Use this WHENEVER the user asks to fix, add, implement, integrate, refactor, update, migrate, optimize, or otherwise change the code-base — even from a one-line prompt like "fix this" or "integrate X". It restructures the request into a spec, investigates the code-base, plans before coding, implements to production standard, runs the full audit (including completeness/no-regression), and returns a precise structured report. Use this instead of jumping straight to editing files.
---

# Task Orchestrator

This is praxis's spine. It turns a terse request into a complete,
production-ready change with nothing left implicit. Run the phases in order; do
not skip ahead to editing. Prioritise correctness and completeness over speed.

The golden rule: **nothing may be silently dropped, stubbed, or left
out-of-scope.** If something cannot be done, it is stated explicitly in the
report — never hidden behind a placeholder.

---

## Phase 1 — Restructure the request (spec)
Use the **prompt-architect** skill to convert the request into an explicit spec:
- **Goal** — the outcome, in one or two sentences.
- **In scope** — concrete deliverables.
- **Out of scope / non-goals** — what you will deliberately not do (surface this;
  never narrow scope silently).
- **Acceptance criteria** — testable conditions for "done".
- **Affected areas** — files/subsystems likely touched (fill after Phase 2).
- **Assumptions** — anything you inferred that the user did not state.
- **Open questions** — genuine ambiguities. Ask them now if they block correct
  work; otherwise state the assumption you will proceed under.

Keep the spec tight. Show it to the user when the request was ambiguous or large;
for small unambiguous asks, state the spec briefly and proceed.

## Phase 2 — Investigate (read before you write)
- Confirm the **CLAUDE.md** hierarchy exists and is accurate. If the session
  audit flagged `new/uninitialised/legacy`, run **bootstrap** first. If memory is
  stale, run **claudemd-living**.
- **Read the actual code** in the affected areas. Dispatch
  `@praxis:repo-cartographer` for unfamiliar code and
  `@praxis:doc-reference-finder` to pin the authoritative docs and existing
  in-repo patterns. Never code against an unread codebase.
- Fill in **Affected areas** and refine acceptance criteria with what you learned.
- If this is a **monorepo**, identify which package(s) the change belongs to
  (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workspaces.py"`) and use that package's
  build/test commands — not just the repo root's.

## Phase 3 — Plan first (plan mode)
Produce a concrete, ordered plan: the steps, the files each touches, the tests to
add/update, and the risks. **Enter plan mode and do not modify files until the
plan is set.** For anything non-trivial, present the plan to the user for
approval; for trivial changes, state the plan in a sentence or two and continue.

A good plan names: the change per file, the new/updated tests, the rollback/road
if something fails, and how each acceptance criterion will be met.

## Phase 4 — Implement to the plan
- Follow the plan; if reality forces a deviation, note it and update the plan
  rather than drifting.
- Apply the **best-practices** relevant to this change (use the `best-practices`
  skill's selection table — REST / DDD / OWASP / ACID-CAP / testing / performance
  as the domains require): the minimal fitting set, consistent with existing repo
  patterns, no cargo-culting.
- Apply **code-craft** standards: self-documenting names, comments that explain
  *why* (not *what*), no debug leftovers, no commented-out code, consistent style
  with the surrounding file.
- Reuse existing utilities (no reinvention/duplication), and add only what this
  change needs — no speculative abstractions, parameters, config, or unused
  surface (KISS/YAGNI). Handle the edge cases and errors that are in scope — do not
  stub them.
- Add or update tests alongside the change.

## Phase 5 — Audit (prove it's done)
Run the **quality-rubric** skill in full:
- vertical auditors: doc-reference, duplication, regression, adversarial,
  edge-case, performance, **and completeness** (`@praxis:completeness-auditor`
  + `scan_placeholders.py`);
- horizontal consistency pass;
- fix every FAIL and actionable note, then re-run the affected auditor;
- confirm the test command passes and no regression was introduced;
- confirm **zero** unacknowledged placeholders/TODOs/stubs and **zero** silently
  narrowed scope;
- confirm the relevant best-practices were actually applied (not just cited).
Record the green quality report so the Stop gate can pass.

## Phase 5b — Update the living knowledge (mandatory)
Documentation is part of "done". Using the `docs-living` skill:
- Update or create the relevant docs under `/docs` for anything this change
  touched (read/search them first; no regression). Seed `/docs` if the repo lacks
  it.
- Add a `[Unreleased]` entry to `CHANGELOG.md`:
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/changelog.py" add --type <added|changed|fixed|removed> "<desc>"`.
- Record an ADR for any significant or autonomously-taken decision:
  `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/adr.py" new "<title>" --status accepted --context "..." --decision "..." --consequences "..."`.
- Keep `docs/README.md` indexed.

## Phase 6 — Report (precise, linear, structured)
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
| completeness    | PASS    | no placeholders/stubs    |

### Best-practices applied
- <family> → <how it was applied> (e.g. "REST idempotency → POST uses an idempotency key")

### Decisions taken autonomously
- <decision> → <chosen option> — <one-line best-practice rationale>
  (this section is where auto-pilot records what it would otherwise have asked;
   empty if the user was consulted)

### Tests
- <what was added/updated>; result of <test command>.

### Docs & knowledge
- Docs updated: <files under /docs>
- CHANGELOG: <the [Unreleased] entry added>
- ADR: <ADR filename, or "none needed">

### Out of scope / follow-ups
- <anything deliberately not done, and why> (empty if none)

### Assumptions made
- <assumptions the user should verify> (empty if none)
```

If any item could not be completed, it goes under **Out of scope / follow-ups**
with the reason — explicitly, never as a hidden gap.

## Phase 7 — Deliver (optional, only when needed)
Delivery is a separate, explicit step — praxis does not commit or push on every
edit. When the change is complete and its audit is green, use the `git-delivery`
skill (or `/praxis:ship`) to turn it into a Conventional Commit and a pull request.
By default the merge is **human-in-the-loop**: praxis opens the PR and hands it
back. Only when auto-merge is enabled (`.praxis.toml [git] auto_merge`, env
`PRAXIS_AUTO_MERGE`, or `git_delivery.py on`) does praxis review and merge its own
PR — and never without a green audit and passing checks, never by force-pushing
the base branch.

---

## Autonomous execution — praxis drives the loop, not you

The user states the idea and picks an effort level; everything else is automatic.
Own the whole lifecycle: self-question, investigate, plan, implement, QA, audit,
regression-check, report — without asking the user to drive each step. Interrupt
**only** at a genuine decision point.

**For any multi-step task, open a praxis task at spec time.** This is what makes
the session self-drive to completion — it is praxis's built-in equivalent of
`/goal`, enforced deterministically by the Stop gate. You do **not** ask the user
to run `/goal`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/task_state.py" open "<task title>" \
  --criteria "criterion 1" "criterion 2" "tests pass" --max <turns>
```

Choose `--max` by task size (a normal task ~15, a large migration ~40). While the
task is open, the Stop gate keeps you working turn after turn. Then:

- **Genuine decision point** (real ambiguity, irreversible choice, conflicting
  requirements): run `task_state.py waiting`, then stop and ask the user. Resume
  with `task_state.py resume` after they answer.
  - **In auto-pilot** (`autopilot.py status` / env `PRAXIS_AUTOPILOT`): do NOT
    stop to ask. Resolve the decision yourself with the `best-practices` decision
    procedure, record it under "Decisions taken autonomously", and continue.
    Reserve `waiting` for a hard external blocker you cannot resolve at all (e.g.
    a missing credential) — and even then state the assumption you'd proceed under.
- **Finished**: only when EVERY criterion is met and the praxis audit is green,
  run `task_state.py done`. This releases the loop.

The gate has a hard turn cap and standard escapes (`skip-gate`, `PRAXIS_GATE=off`),
so it can never trap the session.

**`/goal` is optional and manual.** The native `/goal` command is a separate
power-tool for handing off a very long, cross-session autonomous run, and can be
paired with auto mode. You never need it for normal work — praxis's task loop
already provides the continuation. Only mention it if the user explicitly wants an
unattended multi-hour run.

## Notes
- Language- and framework-agnostic: derive commands, patterns, and idioms from
  the repo itself.
- **Effort:** praxis is effort-agnostic — it behaves identically whether the
  session is at `/effort high` or `/effort ultracode`; higher effort only deepens
  execution. The vertical auditors are pinned to Opus / high in their frontmatter,
  so audits stay deep regardless. Do not change the user's effort setting.
