# Praxis

**The disciplined practice of engineering, applied automatically — inside Claude Code.**

> *Praxis* is the enactment of theory into practice. That is what this tool does:
> it turns engineering principles and best-practices into production-grade software,
> autonomously, while keeping your project's knowledge alive and regression-free.

_Stable public surface under SemVer — see [`docs/STABILITY.md`](docs/STABILITY.md).
Every push is CI-verified: JSON manifests, plugin self-check, and the full test suite._

## Quickstart

```
/plugin marketplace add Ohswedd/praxis     # or a local path
/plugin install praxis@praxis              # the praxis-quality mindset turns on automatically
/praxis:bootstrap                          # set up the repo (CLAUDE.md, /docs, guardrails)
```

Then just describe what you want — *"fix the pagination bug"*, *"integrate Stripe"* —
and pick your effort (`/effort high` or `ultracode`). Optional: `/praxis:autopilot on`
for a hands-off run, and `/praxis:ship` to open a reviewable PR when the change is done.

The `praxis-quality` output style activates automatically once the plugin is enabled,
so the doctrine is on from the first turn — no command to remember.

Praxis turns a batch of engineering checks you would otherwise retype into every
prompt — *documentation-first, no reinvention, no over-engineering, adversarial audit,
regression, performance, edge cases, vertical + horizontal analysis* — into
**permanent, automatic behaviour** that lives in the Claude Code lifecycle instead
of your prompts.

It also **bootstraps any repository** (brand-new, existing-without-setup, or one
with a legacy `CLAUDE.md`) to a top-tier Claude Code configuration, keeps the
`CLAUDE.md` hierarchy **continuously updated and regression-verified**, and maintains
your project's **living knowledge** — a `/docs` tree, a `CHANGELOG.md`, and
Architecture Decision Records — current with every change.

**From a one-line prompt to a production-ready change.** Ask *"fix this"* or
*"integrate X"* and Praxis runs the whole pipeline for you:

```
restructure the request → investigate the code-base → plan (plan mode)
   → implement (professional code-craft) → full audit → update docs & changelog
   → structured report → (optional) ship a reviewable PR
```

No jumping straight to edits, no placeholders or stubs, no silently narrowed scope,
no "missing" pieces you were never told about — and a precise, structured report at
the end.

**You state the macro idea; Claude does the rest.** Praxis sizes each request
(trivial / standard / substantial) and applies the right amount of machinery
automatically — for large multi-step tasks it opens a self-driving task so the
session runs to completion without you managing `/goal`. It composes with your
habitual `/effort high` or `/effort ultracode`. See [`docs/MODES.md`](docs/MODES.md).

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
| **Git/GitHub delivery** | `git-delivery` skill (`/praxis:ship`): Conventional Commit → branch → push → PR. Human-in-the-loop merge by default; opt-in `git.auto_merge` reviews and merges autonomously — never without a green audit |
| **Professional code-craft** | `code-craft` skill: comments that explain *why*, self-documenting names, simplicity/YAGNI (no over-engineering, no reinvention), no debug or dead code |
| **Auto-pilot** | zero questions: Praxis does its own QA, resolves every design decision by the best-practice that fits, and logs each under "Decisions taken autonomously" (safety guards stay active) |
| **Plan-first** | output style + orchestrator require a plan (plan mode) before any file is edited |
| **Completeness enforcement** | `completeness-auditor` subagent + `scan_placeholders.py`: no TODOs/stubs/placeholders, no silently narrowed scope |
| **Always-on quality mindset** | `praxis-quality` output style modifies the system prompt every turn — auto-enabled with the plugin, layered on top of Claude Code's built-in engineering instructions |
| **Universal bootstrap** | `bootstrap` skill classifies repo state and sets up / migrates CLAUDE.md + guardrails |
| **Living CLAUDE.md** | `claudemd-living` skill updates root + nested files, regression-verified, never overwriting valid instructions |
| **Auto-discovery of capabilities** | `capability-discovery` skill finds an existing MCP/skill/plugin before scaffolding a new one |
| **Vertical review** | nine read-only Opus subagents: adversarial, regression, duplication (incl. over-engineering), performance, edge-case, doc-reference, completeness — plus accessibility and design-consistency for UI-touching changes |
| **Front-end pipeline** | `frontend-pipeline` skill (`/praxis:frontend`): business research (client call → goals → audience → competitors → positioning → messaging) → story-first wireframes → design system → development → optimization → ship, for any UI niche (sites, storefronts, lead pages, SaaS UI, CRM/CMS, admin panels, dashboards) — proportional to task size, with design artifacts kept as living knowledge (`docs/design/`) |
| **Repo-wide scanner** | `repo-audit` skill (`/praxis:scan`): shard-ledger inventory of the whole codebase, every vertical auditor over every shard, adversarial reverse-audit of each finding (`finding-verifier`), fixes in audited change-sets — coverage-honest starting & final reports, resumable on large repos |
| **Horizontal review + orchestration** | `quality-rubric` skill runs the cross-cutting pass and loops until green |
| **Deterministic gates** | hooks: a secret/destructive-command guard (blocks force-pushes, destructive resets, and secret exfiltration — even under `--dangerously-skip-permissions`), auto-format on edit, and a **Stop gate** that won't let a turn finish while code is unreviewed |
| **Structured reporting** | canonical report: what changed, criteria met, audit table, tests, out-of-scope, assumptions |
| **Session orientation** | `SessionStart` hook injects a repo health report + standing directives into context |

## Commands

- `/praxis:task <request>` — run the full pipeline end-to-end on a request
- `/praxis:frontend <request>` — run the front-end pipeline: research → story wireframes → design system → build → optimize → ship
- `/praxis:spec <request>` — restructure a request into an explicit spec
- `/praxis:bootstrap` — set up / migrate this repo
- `/praxis:audit` — run the full quality rubric on the current change
- `/praxis:scan [path] [--report-only]` — audit, reverse-audit, and fix the entire repo (coverage-honest, resumable)
- `/praxis:sync` — update the CLAUDE.md hierarchy, regression-verified
- `/praxis:docs` — update the living knowledge (/docs, CHANGELOG, ADRs)
- `/praxis:ship` — deliver the change: Conventional Commit, push, open a PR (merge only if auto-merge is on)
- `/praxis:release` — cut a release (SemVer bump + changelog finalize)
- `/praxis:discover` — find or create a missing capability
- `/praxis:autopilot [on|off]` — toggle no-questions auto-pilot mode
- `/praxis:doctor` — diagnose setup health and drift

> You usually don't need `/praxis:task` explicitly — the always-on directive
> applies the pipeline to implementation work automatically, and Praxis's Stop
> gate keeps the session working until the task is done (no `/goal` needed).

## Configuration

Per-repo settings live in an optional, version-controlled `.praxis.toml` (all keys
optional; defaults shown):

```toml
[gate]
enabled = true          # the Stop quality/task gate
require_tests = true     # a green report must record a passing test run

[autopilot]
default = false          # start sessions in auto-pilot

[audit]
depth = "high"           # auditor depth hint: "high" | "max"

[git]
auto_merge = false       # off: open the PR and let a human merge; on: review + merge
default_branch = ""      # PR base ("" auto-detects origin/HEAD, then main/master)
```

Session escapes: `PRAXIS_GATE=off`, `PRAXIS_AUTOPILOT=on`, `PRAXIS_AUTO_MERGE=on`,
and `touch .claude/.praxis/skip-gate`. The full stable surface is in
[`docs/STABILITY.md`](docs/STABILITY.md).

## Install

```bash
# 1. Register the marketplace (from GitHub, or a local path)
/plugin marketplace add Ohswedd/praxis      # or:  /plugin marketplace add ./praxis

# 2. Install the plugin — the praxis-quality output style turns on automatically
/plugin install praxis@praxis
```

The `praxis-quality` output style auto-enables with the plugin (`force-for-plugin`)
and layers its doctrine on top of Claude Code's built-in engineering instructions
(`keep-coding-instructions`). It overrides your `outputStyle` while Praxis is
enabled; disable the plugin to opt out. (The `/output-style` command was removed in
Claude Code v2.1.91; output styles are now set via `/config` or the `outputStyle`
setting.)

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
                 frontend-pipeline + bootstrap + quality-rubric + repo-audit +
                 claudemd-living + docs-living + capability-discovery + git-delivery
subagents ─────▶ deep vertical audits in isolated context (read-only, Opus)
hooks ─────────▶ SessionStart directive + PreToolUse guard + PostToolUse format +
                 Stop task/quality gate
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design,
[`docs/FLOWS.md`](docs/FLOWS.md) for diagrams, worked examples, edge cases and a
requirement→component traceability matrix, [`docs/MODES.md`](docs/MODES.md) for
effort / `ultracode` / `/goal` / auto-mode recipes, [`docs/DELIVERY.md`](docs/DELIVERY.md)
for the Git/GitHub delivery model, [`docs/KNOWLEDGE.md`](docs/KNOWLEDGE.md) for the
living-knowledge model, [`docs/USAGE.md`](docs/USAGE.md) for day-to-day use, and
[`docs/STABILITY.md`](docs/STABILITY.md) for the stable public surface. The
[`docs/`](docs/) index lists everything.

## Safety model

Installing any plugin runs its code on your machine (hooks, scripts). Praxis is
deliberately conservative:

- **Deterministic guardrails.** A PreToolUse guard blocks secret-file access,
  force-pushes, destructive resets, `rm -rf` on broad paths, and secret
  exfiltration — and holds even under `--dangerously-skip-permissions`. It is a
  best-effort backstop; your permission settings remain the primary control.
- **Read-only auditors.** The nine vertical subagents are restricted to read-only
  tools (`Read, Grep, Glob`; doc-reference also has `WebSearch`/`WebFetch`).
- **Propose, don't overwrite.** Bootstrap and CLAUDE.md changes are shown as diffs
  and confirmed; valid instructions are never silently dropped.
- **Human-in-the-loop delivery.** Praxis opens PRs but never merges or force-pushes
  on its own unless you opt in with `git.auto_merge`.
- **Fail-open hooks.** If a hook script errors, the session continues.
- **Clear escapes.** The Stop gate can be disabled per-repo
  (`touch .claude/.praxis/skip-gate`) or per-session (`PRAXIS_GATE=off`).
- **No shipped secrets / no live MCP.** MCP wiring is a template that references
  environment variables.

## License

MIT — see [LICENSE](LICENSE).
