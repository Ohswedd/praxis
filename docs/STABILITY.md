# Stability & Public Surface (v1.0)

From v1.0, the following surface is **stable** and changes to it follow Semantic
Versioning (breaking changes → a new MAJOR).

## Stable
- **Commands:** `/praxis:task`, `/praxis:frontend`, `/praxis:spec`,
  `/praxis:bootstrap`, `/praxis:audit`, `/praxis:scan`, `/praxis:sync`,
  `/praxis:docs`, `/praxis:discover`, `/praxis:autopilot`, `/praxis:ship`,
  `/praxis:release`, `/praxis:doctor`.
- **Config file:** `.praxis.toml` — keys `gate.enabled`, `gate.require_tests`,
  `autopilot.default`, `audit.depth`, `git.auto_merge`, `git.default_branch`.
- **Environment variables:** `PRAXIS_GATE` (`off` disables the Stop gate),
  `PRAXIS_AUTOPILOT` (`on` enables auto-pilot), `PRAXIS_AUTO_MERGE` (`on` enables
  autonomous PR review-and-merge).
- **Escapes:** `.claude/.praxis/skip-gate` (per-repo gate opt-out); the
  `praxis:ack` inline annotation (exempts one line from the placeholder scanner).
- **State files** under `.claude/.praxis/` (git-ignored):
  `task.json`, `quality_report.json`, `gate_notified.json`, `repo_scan.json`,
  `autopilot`, `auto-merge`.
- **Helper CLIs** (stable flags): `task_state.py`, `report.py`, `changelog.py`,
  `adr.py`, `workspaces.py`, `autopilot.py`, `git_delivery.py`, `doctor.py`,
  `selfcheck.py`, `repo_scan.py`.
- **Managed marker:** `<!-- praxis:managed -->` in a Praxis-managed `CLAUDE.md`.
- **The `/docs` + `CHANGELOG.md` + `docs/adr/` contract** Praxis maintains.

## Internal (may change without a MAJOR bump)
- The wording of injected directives, skill/agent prompt text, and report layout.
- Detection heuristics (test command, workspaces, formatters, secret/placeholder/
  deferral patterns, and the prompt router's classification) — these improve over
  time; their *presence* is stable, their exact matches are not.
- The Stop gate's escalation caps (`MAX_NUDGES`, `SESSION_NUDGE_CAP`) and the
  wording of each escalation step.
- The internal schema of state files beyond the keys listed above.

## Compatibility
- Requires Python 3.8+ (stdlib only) and Claude Code (v2.1.139+ recommended).
- Backwards-compatible state migration is provided for any stable state-file change.
