# Modes, Effort & Autonomy

The contract is simple:

> **You write the prompt and choose the effort level. praxis handles the goals,
> workflows, and subagents automatically.**

No magic keywords, no deciding when to run `/goal`, no manual orchestration.

---

## What you control vs what praxis controls

| You | praxis (automatic) |
| --- | --- |
| Write the prompt in chat | Restructure it into a spec, plan, implement |
| Pick the effort (`high`, `ultracode`, …) | Dispatch the right skills & subagents |
| Answer at genuine decision points | Run QA / audit / regression / completeness |
| — | Keep working until the task is done (the loop) |
| — | Enforce no secrets, no destructive ops, no placeholders |

---

## Effort — the one knob you set

praxis is **effort-agnostic**: it behaves identically at any level. Effort only
changes how deeply Claude *executes* the same workflow — it never changes whether
the workflow, subagents, or gates run.

- `/effort high` — great everyday baseline.
- `/effort ultracode` — xhigh every turn **plus** Claude's own automatic parallel
  sub-agent orchestration. This composes with praxis: you get ultracode's
  parallelism *and* praxis's named vertical auditors. Nothing conflicts.
- `ultrathink` (a word in one prompt) — max thinking for that single turn only,
  then it reverts. Use it for one unusually hard step.

Whatever you pick, praxis's auditors stay pinned to Opus / high effort in their
own frontmatter, so audits are always deep — even if your session is lower.

**So: set `high` or `ultracode` as your habit and forget about it.** Everything
else still works.

---

## Autonomy — praxis runs the loop, you don't run `/goal`

Continuation is handled deterministically inside praxis, driven by a task-state
file (`.claude/.praxis/task.json`) — not by a prompt keyword and not by you
typing `/goal`.

How it works for a multi-step request:

1. At spec time Claude opens a task with acceptance criteria and a turn cap
   (`task_state.py open …`).
2. praxis's **Stop gate** keeps the session working turn after turn while the
   task is open — self-driving to the finish.
3. When Claude hits a **genuine decision point**, it marks the task `waiting` and
   stops to ask you. You answer; it resumes. (So you're never trapped, and you're
   never left out of real decisions.)
4. When **every criterion is met and the audit is green**, Claude marks it `done`
   and the loop releases.
5. A hard turn cap and the escapes (`skip-gate`, `PRAXIS_GATE=off`) mean the loop
   can never run away.

For a single small change there's no task loop — the per-change quality gate simply
refuses to let the turn end while the change is unreviewed. Either way you don't
manage it.

### Is `/goal` ever needed? No — it's optional.

The native `/goal` command still exists and is a fine power-tool for handing off a
very long, **unattended, cross-session** run (pair it with auto mode). But for
normal work you never need it: praxis's task loop already provides the
continuation. If you *do* use `/goal`, it coexists with praxis — both keep the
session going, and praxis feeds its audit results into the transcript the `/goal`
evaluator reads.

---

## auto mode (optional, for unattended runs)

If you want a truly hands-off run, enable **auto mode** (approves tool calls
without prompting). It's safe under praxis because the guards are deterministic
and independent of permission mode:

- secret-file access and destructive commands are still **denied** (PreToolUse);
- the quality/task gate still runs every turn;
- the placeholder scan still catches unfinished work.

Still include a turn cap in the task and be ready to `Ctrl+C`.

---

## Determinism summary

| Concern | Mechanism | Deterministic? |
| --- | --- | --- |
| Does the workflow engage? | always-on directive (SessionStart) + output style; enforced by the change/task gate | Yes — keyed on real file changes, not prompt text |
| Keep working until done | Stop gate + `task.json` (turn cap, `waiting`, `done`) | Yes |
| No secrets / destructive ops | PreToolUse guard (holds even in auto mode) | Yes |
| No placeholders / stubs | `scan_placeholders.py` on the diff | Yes |
| Depth of reasoning | your `/effort` setting | You choose |

There is **no** prompt-keyword classifier deciding your fate. The workflow is
carried by an always-injected directive and enforced by change-based gates, so it
applies regardless of how you phrase the request.

---

## Auto-pilot — zero questions

Turn it on and praxis asks you **nothing** about design or approach. It does its
own QA and resolves each decision by the best-practice that fits, then records
every non-trivial choice under **"Decisions taken autonomously"** in the report —
so nothing is hidden; you review after, not during.

```
/praxis:autopilot on      # this repo
/praxis:autopilot off
```

Or pin it globally by exporting `PRAXIS_AUTOPILOT=on` in your shell profile.

The decision procedure (from the `best-practices` skill), in priority order:
correctness & safety → the applicable best-practice → repo consistency →
simplicity (KISS/YAGNI) → reversibility.

Safety is unchanged in auto-pilot: the PreToolUse guard still blocks secrets and
destructive commands, and the quality/task gate still runs. The only thing praxis
will ever stop for is a **hard external blocker it cannot resolve itself** (e.g. a
credential you must provide) — and even then it states the assumption it would use.

## Best-practices — applied by need

praxis follows established engineering best-practices, choosing the **minimal
relevant set** for the change's domains rather than applying everything. The
`best-practices` skill has a selection table (HTTP endpoint → REST/idempotency/
OWASP; DB change → transactions/indexing/N+1; domain model → DDD; hot path →
Big-O/caching; …) and a full catalog it consults on demand. It respects KISS and
YAGNI, so it won't over-engineer, and it notes which practices it applied in the
report.

## The whole workflow, from your side

1. Set your effort once (`/effort high` or `/effort ultracode`).
2. (Optional) `/praxis:autopilot on` — or set `PRAXIS_AUTOPILOT=on` once.
3. Type the idea: *"migra l'intero layer di pagamento a Stripe."*
4. In auto-pilot: just read the final report (with the decisions it made). Without
   it: answer only genuine questions.

That's it.
