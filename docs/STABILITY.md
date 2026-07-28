# Stability & Public Surface (v3.1)

From v1.0, the following surface is **stable** and changes to it follow Semantic
Versioning (breaking changes → a new MAJOR).

## Stable
- **Commands:** `/praxis:task`, `/praxis:audit`, `/praxis:docs`, `/praxis:ship`,
  `/praxis:bootstrap`, `/praxis:doctor`, `/praxis:config`, `/praxis:discover`.
  Several take a mode as an argument: `task spec:`, `audit repo`,
  `ship release`, `config mode|autopilot|auto-merge|bootstrap|gate`.
- **Config file:** `.praxis.toml`, keys `workspace.mode`, `bootstrap.auto`,
  `gate.enabled`, `gate.require_tests`, `gate.require_ui_verticals`,
  `autopilot.default`, `audit.depth`, `git.auto_merge`, `git.default_branch`,
  `style.ban_em_dash`, `style.ban_ai_attribution`. A second copy at
  `.claude/.praxis/praxis.toml` is read afterwards and overrides it; it is
  git-excluded and is the only one praxis writes in `contributor` mode.
- **Environment variables:** `PRAXIS_MODE` (`owner` / `contributor`),
  `PRAXIS_GATE` (`off` disables the Stop gate), `PRAXIS_AUTOPILOT` (`on` enables
  auto-pilot), `PRAXIS_AUTO_MERGE` (`on` enables autonomous PR review-and-merge),
  `PRAXIS_BOOTSTRAP` (`off` disables auto-bootstrap).
- **Escapes:** `.claude/.praxis/skip-gate` (per-repo gate opt-out);
  `.claude/.praxis/no-bootstrap` (per-repo auto-bootstrap opt-out); the
  `praxis:ack` inline annotation, which exempts one line from the placeholder
  scanner, the house-style scanner, and the drift checker alike.
- **State files** under `.claude/.praxis/` (git-ignored):
  `task.json`, `quality_report.json`, `gate_notified.json`, `repo_scan.json`,
  `autopilot`, `auto-merge`, `workspace`, `no-bootstrap`, `praxis.toml`, and the
  `knowledge/` tree.
- **Local artifacts** praxis writes in `contributor` mode, and never commits:
  `CLAUDE.local.md`, `.claude/settings.local.json`, and everything under
  `.claude/.praxis/`. praxis keeps them out of git with a marked block in
  `$GIT_COMMON_DIR/info/exclude`, and the PreToolUse guard refuses to stage them in
  either mode.
- **Helper CLIs** (stable flags): `task_state.py` (including `--subtasks`,
  `plan`, `subtask start|done`, `delivery`), `report.py`, `changelog.py`,
  `adr.py`, `debt.py`, `scope.py`, `workspaces.py`, `config.py`, `doctor.py`,
  `drift.py`, `scan_placeholders.py`, `scan_style.py`, `selfcheck.py` (including
  `--require-repo`), `repo_scan.py`.

- **Install identifier:** marketplace `ohswedd-praxis`, plugin `praxis`, i.e.
  `/plugin install praxis@ohswedd-praxis`. Owner-scoped deliberately: a
  marketplace name is a single global slot per user, so a generic one can be
  silently replaced by an unrelated project claiming the same name.
- **Managed marker:** `<!-- praxis:managed -->` in a Praxis-managed `CLAUDE.md`.
- **The `/docs` + `CHANGELOG.md` + `docs/adr/` + `docs/DEBT.md` contract** Praxis
  maintains.
- **The review scope**: a change is the branch's commits since its merge-base
  with the integration branch, plus the working tree and untracked files. On the
  integration branch itself there is no range, and the scope is the working tree
  alone.

## Added in 3.1 (non-breaking)
| What | Why it matters |
| --- | --- |
| `debt` vertical + `@praxis:debt-auditor` + `debt.py` + `docs/DEBT.md` | nothing asked what a change would cost later, or whether the shortcut was recorded |
| Branch-scoped review + `scope.py` | one commit used to empty every diff praxis reads, so the audit apparatus went blind exactly when delivery got better |
| `task_state.py` subtasks and delivery binding | a large prompt was one opaque task; now it is an ordered plan, one commit per subtask, one PR per task |

Nothing was removed or renamed, and a repo that never branches behaves exactly
as it did in 3.0.

## Removed in 3.0 (breaking)
| Was | Now |
| --- | --- |
| `/praxis:frontend <request>` | nothing to type. The `frontend-pipeline` skill is engaged by the surface a change touches, through the prompt router, the task-orchestrator, and the Stop gate | <!-- praxis:ack: a migration table names the old command on purpose -->

The pipeline itself is unchanged, and so is every phase, artifact and auditor in
it. What went away is the fourth way to start it, which could only be used
wrongly: typed after the design decisions were made, or not typed at all for the
"fix the checkout bug" that was front-end work all along. See ADR-0020.

Two behaviours changed without breaking the surface, and both can be switched
off: praxis now bootstraps a repo it does not manage before working in it
(`bootstrap.auto`), and it detects when a repository is not yours and keeps
everything it writes local (`workspace.mode`). See ADR-0018 and ADR-0019.

## Removed in 2.0 (breaking)
| Was | Now |
| --- | --- |
| `/praxis:spec <request>` | `/praxis:task spec: <request>` | <!-- praxis:ack: a migration table names the old command on purpose -->
| `/praxis:scan [path]` | `/praxis:audit repo` or `/praxis:audit <path>` | <!-- praxis:ack -->
| `/praxis:sync` | `/praxis:docs`, which now covers the brief hierarchy too | <!-- praxis:ack -->
| `/praxis:release [version]` | `/praxis:ship release [version]` | <!-- praxis:ack -->
| `/praxis:autopilot on\|off` | `/praxis:config autopilot on\|off` | <!-- praxis:ack -->
| `autopilot.py`, `git_delivery.py` | `config.py <switch> <on\|off>` |

No workflow was removed: the same skills run behind fewer entry points. Nothing
else in the stable surface above was removed or renamed.

## Internal (may change without a MAJOR bump)
- The wording of injected directives, skill/agent prompt text, and report layout.
- Detection heuristics (test command, monorepo packages, formatters, secret/
  placeholder/deferral patterns, the prompt router's classification, and the
  signals behind `workspace.mode = "auto"`): these improve over time; their
  *presence* is stable, their exact matches are not. Pin the mode explicitly if a
  repo must never be re-classified.
- The Stop gate's escalation caps (`MAX_NUDGES`, `SESSION_NUDGE_CAP`) and the
  wording of each escalation step.
- The internal schema of state files beyond the keys listed above.

## Compatibility
- Requires Python 3.8+ (stdlib only) and Claude Code (v2.1.139+ recommended).
- Backwards-compatible state migration is provided for any stable state-file change.
