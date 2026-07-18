# Praxis

**The disciplined practice of engineering, applied automatically — inside Claude Code.**

> *Praxis* is the enactment of theory into practice. This is what the tool does:
> it turns engineering principles and best-practices into production-grade software,
> autonomously, while keeping your project's knowledge alive and regression-free.

_Stable — v1.0. Public surface follows SemVer ([`docs/STABILITY.md`](docs/STABILITY.md)); CI-verified integrity and tests._

## Quickstart

```
/plugin marketplace add Ohswedd/praxis     # or a local path
/plugin install praxis@praxis
/output-style praxis-quality                # turn on the mindset
/praxis:bootstrap                           # set up the repo (CLAUDE.md, /docs, guardrails)
```
Then just describe what you want — *"fix the pagination bug"*, *"integrate Stripe"* —
and pick your effort (`/effort high` or `ultracode`). Optional: `/praxis:autopilot on`.

Praxis turns a batch of engineering checks you'd otherwise retype into every
prompt — *documentation-first, no reinvention, no duplication, adversarial audit,
regression, performance, edge cases, vertical + horizontal analysis* — into
**permanent, automatic behaviour** that lives in the Claude Code lifecycle
instead of your prompts.

It also **bootstraps any repository** (brand-new, existing-without-setup, or one
with a legacy `CLAUDE.md`) to a top-tier Claude Code configuration, keeps the
`CLAUDE.md` hierarchy **continuously updated and regression-verified**, and
maintains your project's **living knowledge** — a `/docs` tree, a `CHANGELOG.md`,
and Architecture Decision Records — current with every change.

**From a one-line prompt to a production-ready change.** Ask *"fix this"* or
*"integrate X"* and Praxis runs the whole pipeline for you:

```
restructure the request → investigate the code-base → plan (plan mode)
   → implement (professional code-craft) → full audit → update docs & changelog → structured report
```

No jumping straight to edits, no placeholders or stubs, no silently narrowed
scope, no "missing" pieces you were never told about — and a precise, structured
report at the end.

**You state the macro idea; Claude does the rest.** praxis sizes each request
(trivial / standard / substantial) and applies the right amount of machinery
automatically — for large multi-step tasks it even proposes a ready-to-run
`/goal` so the session self-drives to completion. It composes with your habitual
`/effort high` or `/effort ultracode`. See [`docs/MODES.md`](docs/MODES.md).

> Designed for quality over cost. It runs entirely **in the interactive session**
> so a Claude **Pro/Max subscription** covers it — see
> [`docs/USAGE.md`](docs/USAGE.md) for why the harness deliberately avoids the
> headless/`-p` path.

---

## What it does

| Capability | How |
| --- | --- |
| **End-to-end task engine** | `task-orchestrator` skill runs restructure → investigate → plan → implement → audit → report |
| **Prompt restructuring** | `prompt-architect` skill turns a vague prompt into goal / scope / non-goals / acceptance criteria |
| **Always-on, no keywords** | the workflow is carried by an always-injected SessionStart directive + output style, and enforced by change-based gates — it applies however you phrase the request, deterministically |
| **Best-practices, by need** | `best-practices` skill selects and applies the minimal relevant families (SOLID, DDD, REST, ACID/CAP, OWASP, testing, clean code, performance…) for the change's domains, from a curated catalog |
| **Living knowledge** | maintains the project's `/docs`, `CHANGELOG.md`, and ADRs — read/searched/updated/created for every change, no regression, always current |
| **Git/GitHub delivery** | `git-delivery` skill: Conventional Commit → branch → push → PR. Human-in-the-loop merge by default; opt-in `git.auto_merge` reviews and merges autonomously (never without a green audit) |
| **Auto-pilot** | zero questions: praxis does its own QA, resolves every design decision by the best-practice that fits, and logs each under "Decisions taken autonomously" (safety guards stay active) |
| **Plan-first** | output style + orchestrator require a plan (plan mode) before any file is edited |
| **Professional code-craft** | `code-craft` skill: comments that explain *why*, self-documenting names, no debug/dead code |
| **Completeness enforcement** | `completeness-auditor` subagent + `scan_placeholders.py`: no TODOs/stubs/placeholders, no silently narrowed scope |
| **Always-on quality mindset** | `praxis-quality` output style modifies the system prompt every turn |
| **Universal bootstrap** | `bootstrap` skill classifies repo state and sets up / migrates CLAUDE.md + guardrails |
| **Living CLAUDE.md** | `claudemd-living` skill updates root + nested files, regression-verified, never overwriting valid instructions |
| **Auto-discovery of capabilities** | `capability-discovery` skill finds an existing MCP/skill/plugin before scaffolding a new one |
| **Vertical review** | seven read-only Opus subagents: adversarial, regression, duplication, performance, edge-case, doc-reference, completeness |
| **Horizontal review + orchestration** | `quality-rubric` skill runs the cross-cutting pass and loops until green |
| **Deterministic gates** | hooks: secret/destructive-command guard (works even under `--dangerously-skip-permissions`), auto-format on edit, and a **Stop gate** that won't let a turn finish while code is unreviewed |
| **Structured reporting** | canonical report: what changed, criteria met, audit table, tests, out-of-scope, assumptions |
| **Session orientation** | `SessionStart` hook injects a repo health report + standing directives into context |

## Commands

- `/praxis:task <request>` — run the full pipeline end-to-end on a request
- `/praxis:spec <request>` — restructure a request into an explicit spec
- `/praxis:bootstrap` — set up / migrate this repo
- `/praxis:audit` — run the full quality rubric on the current change
- `/praxis:sync` — update the CLAUDE.md hierarchy, regression-verified
- `/praxis:docs` — update the living knowledge (/docs, CHANGELOG, ADRs)
- `/praxis:ship` — deliver the change: Conventional Commit, push, open a PR (merge only if auto-merge is on)
- `/praxis:release` — cut a release (SemVer bump + changelog finalize)
- `/praxis:discover` — find or create a missing capability
- `/praxis:autopilot [on|off]` — toggle no-questions auto-pilot mode
- `/praxis:doctor` — diagnose setup health and drift

> You usually don't need `/praxis:task` explicitly — the always-on directive
> applies the pipeline to implementation work automatically, and praxis's Stop
> gate keeps the session working until the task is done (no `/goal` needed).

## Install

```bash
# 1. Register the marketplace (from GitHub once published, or a local path)
/plugin marketplace add Ohswedd/praxis      # or:  /plugin marketplace add ./praxis

# 2. Install the plugin
/plugin install praxis@praxis

# 3. (recommended) enable the always-on quality mindset
/output-style praxis-quality
```

For auto-update, add the marketplace to your settings with `autoUpdate: true`
(see [`docs/INSTALL.md`](docs/INSTALL.md)).

## Requirements & compatibility
- **Claude Code** v2.1.139+ recommended (the optional `/goal` power-tool needs it;
  Praxis's own loop does not).
- **Python 3.8+** on `PATH` (`python3`). Hooks are **standard-library only** — no
  pip installs, no third-party supply-chain surface.
- **OS:** macOS and Linux out of the box. On Windows, ensure `python3` resolves
  (or change the hook commands in `hooks/hooks.json` to `python`).
- Verified by CI on every push: JSON manifests, plugin self-integrity
  (`selfcheck.py`), and the full test suite (`tests/`).

See [`SECURITY.md`](SECURITY.md) for the security posture and
[`CONTRIBUTING.md`](CONTRIBUTING.md) to develop Praxis itself.

## How it fits together

```
output style ──▶ mindset on every turn (plan-first, doc-first, complete, structured)
skills ────────▶ task-orchestrator + prompt-architect + best-practices + code-craft +
                 bootstrap + quality-rubric + claudemd-living + docs-living + capability-discovery
subagents ─────▶ deep vertical audits in isolated context (read-only, Opus)
hooks ─────────▶ SessionStart directive + PreToolUse guard + Stop task/quality gate
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design,
[`docs/FLOWS.md`](docs/FLOWS.md) for diagrams, worked examples, edge cases and a
requirement→component traceability matrix, [`docs/MODES.md`](docs/MODES.md) for
effort/`ultracode`/`/goal`/auto-mode recipes, [`docs/KNOWLEDGE.md`](docs/KNOWLEDGE.md)
for the living-knowledge model, and [`docs/USAGE.md`](docs/USAGE.md) for day-to-day
use, and [`docs/STABILITY.md`](docs/STABILITY.md) for the stable v1.0 surface.
The [`docs/`](docs/) index lists everything.

## Safety model

Installing any plugin runs its code on your machine (hooks, scripts). praxis is
deliberately conservative:

- **Read-only auditors.** The seven vertical subagents are restricted to read-only
  tools (`Read, Grep, Glob`; doc-reference also has `WebSearch`/`WebFetch`).
- **Propose, don't overwrite.** Bootstrap and CLAUDE.md changes are shown as diffs
  and confirmed; valid instructions are never silently dropped.
- **Fail-open hooks.** If a hook script errors, the session continues.
- **Clear escapes.** The Stop gate can be disabled per-repo
  (`touch .claude/.praxis/skip-gate`) or per-session (`PRAXIS_GATE=off`).
- **No shipped secrets / no live MCP.** MCP wiring is a template that references
  environment variables.

## License

MIT — see [LICENSE](LICENSE).
