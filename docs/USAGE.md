# Usage

## Day-to-day

- **Start in any repo.** The `SessionStart` audit classifies it and injects a
  health report + standing directives. If it reports `new`, `uninitialised`, or
  `legacy`, run `/praxis:bootstrap`.
- **Just ask.** Type a normal request — *"fix the pagination bug"*, *"integrate
  Stripe checkout"*, *"refactor the auth module"* (English or Italian) — and pick
  your effort level. The always-on directive applies the full pipeline to
  implementation work automatically (restructure → investigate → plan → implement
  → audit → report), and for multi-step tasks praxis's Stop gate keeps the
  session working until the task is done. You can also invoke it explicitly with
  `/praxis:task <request>`, or just get the spec with `/praxis:spec <request>`.
- **Plan-first.** For anything non-trivial praxis presents a plan (plan mode)
  before touching files; approve or adjust it, then it implements.
- **Finish a change.** When you stop with unreviewed code, the Stop gate asks you
  to run `/praxis:audit`, which dispatches the vertical auditors — including the
  completeness auditor that guarantees no placeholders/stubs and no silently
  dropped scope — loops until green, then records the pass.
- **Audit a whole repo.** `/praxis:scan` runs the repo-wide scanner on an
  existing codebase: a shard ledger inventories every file, every vertical
  dimension runs on every shard, each finding is adversarially reverse-audited,
  and confirmed findings are fixed (or deferred with a plan). Coverage-honest
  reports, resumable across sessions; `--report-only` to skip fixes. See
  [`SCAN.md`](SCAN.md).
- **Memory upkeep.** After conventions change, `/praxis:sync` updates the
  CLAUDE.md hierarchy with regression verification.
- **Missing a tool.** `/praxis:discover` finds or creates the capability,
  reusing an existing one first.

## Why it stays on your subscription

The harness runs **inside the interactive session** (hooks + subagents), which is
covered by a Pro/Max subscription's usage. It deliberately does **not** move the
routine checks into `claude -p`, the Agent SDK, or CI, because non-interactive
usage on subscription plans draws from a separate metered credit pool. Keep the
harness interactive and the subscription covers it.

Quality is prioritised over speed: the vertical auditors run on Opus at high
effort. On a Max plan this is the intended trade-off. Model/effort still affects
how fast you consume the shared usage window (Opus > Sonnet > Haiku), so if you
ever want to dial a specific auditor down, change its `model`/`effort` frontmatter.

## Escape hatches

- Disable the Stop gate for one repo: `touch .claude/.praxis/skip-gate`
- Disable it for a session: set `PRAXIS_GATE=off`
- Re-enable: delete the file / unset the variable.

The guardrail hooks (secret + destructive-command blocks) are intentionally not
disableable via those switches — remove or edit `hooks/hooks.json` if you must.

## Tuning

- **Permissions:** edit `.claude/settings.json` (bootstrap proposes a starting
  point from the template).
- **Auditor depth:** edit each agent's `model` / `effort` frontmatter.
- **Formatters:** extend the table in `scripts/post_edit.py`.
- **Sensitive paths / secret patterns:** extend `scripts/lib/common.py`.

## Troubleshooting

- Hooks not firing → `/reload-plugins` or restart; confirm `python3` is on PATH.
- Gate never fires → it only fires with a dirty git tree; commit or check
  `/praxis:doctor`.
- Gate too eager → it prompts once per change signature per session; if you
  edited after a green audit, that is expected (re-audit).

## Uninstall & cleanup

- Remove the plugin: `/plugin uninstall praxis@praxis` (and
  `/plugin marketplace remove praxis` if you added it locally).
- Per-repo state lives in `.claude/.praxis/` (git-ignored); delete it to reset
  Praxis's memory for that repo. Your `/docs`, `CHANGELOG.md`, ADRs, and
  `CLAUDE.md` are yours — they stay.
