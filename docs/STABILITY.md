# Stability & Public Surface (v2.0)

From v1.0, the following surface is **stable** and changes to it follow Semantic
Versioning (breaking changes → a new MAJOR).

## Stable
- **Commands:** `/praxis:task`, `/praxis:frontend`, `/praxis:audit`,
  `/praxis:docs`, `/praxis:ship`, `/praxis:bootstrap`, `/praxis:doctor`,
  `/praxis:config`, `/praxis:discover`. Several take a mode as an argument:
  `task spec:`, `audit repo`, `ship release`.
- **Config file:** `.praxis.toml`, keys `gate.enabled`, `gate.require_tests`,
  `gate.require_ui_verticals`, `autopilot.default`, `audit.depth`,
  `git.auto_merge`, `git.default_branch`, `style.ban_em_dash`,
  `style.ban_ai_attribution`.
- **Environment variables:** `PRAXIS_GATE` (`off` disables the Stop gate),
  `PRAXIS_AUTOPILOT` (`on` enables auto-pilot), `PRAXIS_AUTO_MERGE` (`on` enables
  autonomous PR review-and-merge).
- **Escapes:** `.claude/.praxis/skip-gate` (per-repo gate opt-out); the
  `praxis:ack` inline annotation, which exempts one line from the placeholder
  scanner, the house-style scanner, and the drift checker alike.
- **State files** under `.claude/.praxis/` (git-ignored):
  `task.json`, `quality_report.json`, `gate_notified.json`, `repo_scan.json`,
  `autopilot`, `auto-merge`.
- **Helper CLIs** (stable flags): `task_state.py`, `report.py`, `changelog.py`,
  `adr.py`, `workspaces.py`, `config.py`, `doctor.py`, `drift.py`,
  `scan_placeholders.py`, `scan_style.py`, `selfcheck.py`, `repo_scan.py`.

- **Install identifier:** marketplace `ohswedd-praxis`, plugin `praxis`, i.e.
  `/plugin install praxis@ohswedd-praxis`. Owner-scoped deliberately: a
  marketplace name is a single global slot per user, so a generic one can be
  silently replaced by an unrelated project claiming the same name.
- **Managed marker:** `<!-- praxis:managed -->` in a Praxis-managed `CLAUDE.md`.
- **The `/docs` + `CHANGELOG.md` + `docs/adr/` contract** Praxis maintains.

## Removed in 2.0 (breaking)
| Was | Now |
| --- | --- |
| `/praxis:spec <request>` | `/praxis:task spec: <request>` | <!-- praxis:ack: a migration table names the old command on purpose -->
| `/praxis:scan [path]` | `/praxis:audit repo` or `/praxis:audit <path>` | <!-- praxis:ack -->
| `/praxis:sync` | `/praxis:docs` (now covers the CLAUDE.md hierarchy) | <!-- praxis:ack -->
| `/praxis:release [version]` | `/praxis:ship release [version]` | <!-- praxis:ack -->
| `/praxis:autopilot on\|off` | `/praxis:config autopilot on\|off` | <!-- praxis:ack -->
| `autopilot.py`, `git_delivery.py` | `config.py <switch> <on\|off>` |

No workflow was removed: the same skills run behind fewer entry points. Nothing
else in the stable surface above was removed or renamed.

## Internal (may change without a MAJOR bump)
- The wording of injected directives, skill/agent prompt text, and report layout.
- Detection heuristics (test command, workspaces, formatters, secret/placeholder/
  deferral patterns, and the prompt router's classification): these improve over
  time; their *presence* is stable, their exact matches are not.
- The Stop gate's escalation caps (`MAX_NUDGES`, `SESSION_NUDGE_CAP`) and the
  wording of each escalation step.
- The internal schema of state files beyond the keys listed above.

## Compatibility
- Requires Python 3.8+ (stdlib only) and Claude Code (v2.1.139+ recommended).
- Backwards-compatible state migration is provided for any stable state-file change.
