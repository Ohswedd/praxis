# Usage

## Day-to-day

- **Start in any repo.** The `SessionStart` audit classifies it and injects a
  health report + standing directives. If praxis is not set up here, it
  bootstraps the repo itself on the first prompt that does real work, then
  carries on with your request; `/praxis:bootstrap` is only for asking
  explicitly, or re-running it later. Turn it off with
  `/praxis:config bootstrap off`.
- **Working in a repo that is not yours?** praxis notices, and switches to
  `contributor` mode: it writes `CLAUDE.local.md` instead of `CLAUDE.md`,
  `.claude/settings.local.json` instead of `.claude/settings.json`, keeps its
  knowledge under `.claude/.praxis/knowledge/` unless the project already has a
  `/docs` or `CHANGELOG.md` to join, excludes all of it from git, and refuses to
  stage any of it. Check or override with `/praxis:config mode`. See
  [`MODES.md`](MODES.md).
- **Just ask.** Type a normal request: *"fix the pagination bug"*, *"integrate
  Stripe checkout"*, *"refactor the auth module"* (English or Italian), and pick
  your effort level. The always-on directive applies the full pipeline to
  implementation work automatically (restructure → investigate → plan → implement
  → audit → report), and for multi-step tasks praxis's Stop gate keeps the
  session working until the task is done. You can also invoke it explicitly with
  `/praxis:task <request>`, or just get the spec with `/praxis:task spec: <request>`.
- **Plan-first.** For anything non-trivial praxis presents a plan (plan mode)
  before touching files; approve or adjust it, then it implements.
- **Finish a change.** When you stop with unreviewed code, the Stop gate asks you
  to run `/praxis:audit`, which dispatches the vertical auditors, including the
  completeness auditor that guarantees no placeholders/stubs and no silently
  dropped scope: loops until green, then records the pass.
- **Audit a whole repo.** `/praxis:audit repo` runs the repo-wide scanner on an
  existing codebase: a shard ledger inventories every file, every vertical
  dimension runs on every shard, each finding is adversarially reverse-audited,
  and confirmed findings are fixed (or deferred with a plan). Coverage-honest
  reports, resumable across sessions; `--report-only` to skip fixes. See
  [`SCAN.md`](SCAN.md).
- **Build a front-end.** Just ask, in whatever words fit: *"make a landing
  page"*, but equally *"fix the checkout bug"* or *"update `Header.tsx`"*. There
  is no command, because the pipeline is triggered by the surface a change
  touches rather than by how the request was phrased. It runs business research →
  story-first wireframes → design system → development → optimization,
  proportional to the task, keeps the design artifacts in `docs/design/`, and
  audits UI changes on the accessibility and design-consistency verticals. See
  [`FRONTEND.md`](FRONTEND.md).
- **Knowledge upkeep.** `/praxis:docs` reconciles all of it in one pass: `/docs`,
  `CHANGELOG.md`, ADRs, and the CLAUDE.md hierarchy with regression verification.
  It starts by running the drift check, so a document that contradicts the repo's
  live settings, or points at a command or file that no longer exists, is found
  rather than remembered.
- **Deliver it.** `/praxis:ship` writes the Conventional Commit, branches, and
  opens the PR; `/praxis:ship release` cuts a SemVer release from the changelog
  and the commit history.
- **Change a setting.** `/praxis:config` prints every switch, its value, and the
  source that decided it; `/praxis:config autopilot on` (or `auto-merge`,
  `bootstrap`, or `gate`) toggles one, and `/praxis:config mode
  owner|contributor|auto` sets the workspace mode.
- **Missing a tool.** `/praxis:discover` finds or creates the capability,
  reusing an existing one first.

## What it will refuse to hand back

The Stop gate is not a reminder, and these are not judgement calls:

- unfinished work in the change, including in files you have not staged yet;
- deferral prose in a comment ("for now", "in a real implementation");  <!-- praxis:ack -->
- a report whose tests praxis did not run itself;
- a change touching markup, styles, or components without the accessibility and
  design-consistency verdicts, whatever the request called the work;
- an em dash, anywhere in the text of the change;
- a commit or PR carrying an AI co-author trailer or a "generated with" credit,
  which is refused at the command rather than at the turn.

`praxis:ack` on a line records a genuine exception; `.praxis.toml` turns any of
these off for a repo that wants them off.

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

- Disable the Stop gate for one repo: `/praxis:config gate off` (which writes
  `.claude/.praxis/skip-gate`).
- Disable it for a session: set `PRAXIS_GATE=off`.
- Re-enable: `/praxis:config gate on`, or unset the variable.
- Stop praxis setting up a repo on its own: `/praxis:config bootstrap off` (which
  writes `.claude/.praxis/no-bootstrap`), or `PRAXIS_BOOTSTRAP=off` for a session.
- Correct the workspace verdict: `/praxis:config mode owner` or
  `mode contributor`, or `PRAXIS_MODE=` for a session. `mode auto` hands the
  decision back to detection. Switching to `owner` also removes praxis's block
  from `$GIT_COMMON_DIR/info/exclude`.
- `/praxis:config` with no argument shows every switch and, importantly, the
  source that decided it: clearing a toggle that an environment variable still
  forces prints a warning instead of quietly reporting success.
- Let praxis create a file the project never had, in a repo you only contribute
  to: `/praxis:config project-artifacts on`, or `PRAXIS_PROJECT_ARTIFACTS=on`
  for a session. Only needed when the maintainers actually asked for a
  `CHANGELOG.md`, a `CLAUDE.md` or a `/docs` tree.
- Record why a living-knowledge finding does not apply, rather than working
  around it: `report.py record --knowledge-ack "<reason>"`. The reason is kept in
  the report and shown by the gate.
- Per-repo opt-outs live in `.praxis.toml`: `workspace.mode`,
  `workspace.allow_project_artifacts`, `bootstrap.auto`, `gate.require_tests`,
  `gate.require_ui_verticals`, `gate.require_knowledge`, `gate.require_evidence`,
  `gate.require_runtime`, `style.ban_em_dash`, `style.ban_ai_attribution`. In
  `contributor` mode put them in `.claude/.praxis/praxis.toml`, which layers on
  top and stays out of git. The file is optional in both modes: praxis runs from
  its defaults, so not having one is not a missing setup.

The guardrail hooks (secret + destructive-command blocks) are intentionally not
disableable via those switches: remove or edit `hooks/hooks.json` if you must.

## Tuning

- **Permissions:** edit `.claude/settings.json` (bootstrap proposes a starting
  point from the template), or `.claude/settings.local.json` in `contributor` mode.
- **Workspace detection:** the signals live in `_detect_workspace_mode` in
  `scripts/lib/common.py`. Pin `workspace.mode` explicitly rather than tuning
  them for one repo.
- **Auditor depth:** edit each agent's `model` / `effort` frontmatter.
- **Formatters:** extend the table in `scripts/post_edit.py`.
- **Sensitive paths / secret patterns:** extend `scripts/lib/common.py`.
- **House style:** `style.ban_em_dash` and `style.ban_ai_attribution` in
  `.praxis.toml`; `praxis:ack` on a line for a one-off exception.
- **UI surface detection:** the suffix and path sets in `scripts/lib/common.py`
  (`UI_SUFFIXES`, `UI_FILENAME_RE`, `UI_PATH_RE`).

## Troubleshooting

- Hooks not firing → `/reload-plugins` or restart; confirm `python3` is on PATH.
- Gate never fires → it only fires with a dirty git tree; commit or check
  `/praxis:doctor`.
- Gate too eager → a green report is keyed to the exact change state, so an edit
  after a green audit re-arms it. That is expected; re-audit.
- Gate blocking on the UI verticals → the change touched a file praxis reads as
  user-facing surface. Run the two UI auditors, or set
  `require_ui_verticals = false` under `[gate]` if the repo genuinely does not
  want them.
- Docs and behaviour disagree → run `/praxis:doctor`; the drift section names the
  line and the setting it contradicts.
- praxis called your own repo `contributor` → it found a remote, real history,
  and no commit from your configured `git config user.email`. Common in a fresh
  fork, or when your local email differs from the one in the history. Fix it with
  `/praxis:config mode owner`, which also drops the exclude block.
- A praxis file will not stage → that is the guard, and it is right:
  `CLAUDE.local.md`, `.claude/.praxis/` and `.claude/settings.local.json`
  describe your machine, not the project. Stage the paths your change touches.

## Uninstall & cleanup

- Remove the plugin: `/plugin uninstall praxis@ohswedd-praxis` (and
  `/plugin marketplace remove praxis` if you added it locally).
- Per-repo state lives in `.claude/.praxis/` (git-ignored); delete it to reset
  Praxis's memory for that repo. Your `/docs`, `CHANGELOG.md`, ADRs, and
  `CLAUDE.md` are yours: they stay.
