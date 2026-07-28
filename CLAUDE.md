<!-- praxis:managed -->
# Project: praxis

A Claude Code plugin that turns any prompt into a full engineering pipeline
(spec, investigate, plan, implement, audit, document, ship) and enforces the
result with deterministic hooks. It is distributed through the `ohswedd-praxis`
marketplace and runs entirely inside the interactive session.

## Commands
- Test:   `make test`   (python3 -m unittest discover -s tests)
- Check:  `make check`  (selfcheck, drift, tests, compile: this is what CI runs)
- Lint:   `make compile` (byte-compiles every script; there is no external linter)
- Run:    there is nothing to run. Exercise a script directly, e.g.
  `python3 plugins/praxis/scripts/doctor.py`, or feed a hook its JSON on stdin.

## Architecture
Four layers, only one of which can refuse:

- `plugins/praxis/output-styles/praxis-quality.md`: the always-on doctrine.
- `plugins/praxis/skills/*/SKILL.md`: the reasoning workflows, routed per prompt.
- `plugins/praxis/agents/*.md`: read-only auditor subagents (`Read, Grep, Glob`).
- `plugins/praxis/scripts/*.py`: the hooks, wired in `hooks/hooks.json`. These are
  the only deterministic gates.

`scripts/lib/common.py` holds every shared helper: the review scope (the branch's
base, its commits, and what is still uncommitted), workspace mode and artifact
paths, repo state, the change signature, config resolution, UI-surface detection,
secret and house-style patterns. Put shared logic there rather than in a second
script. `docs/ARCHITECTURE.md` is the long form.

## Conventions
- **Python 3.8+, standard library only.** No pip installs, no network calls at
  runtime. A dependency here would be a supply chain in every user's session.
- **Hooks fail open.** Every hook catches at the top level and exits 0. A CLI
  whose exit code a caller reads (`report.py`, `selfcheck.py`, `config.py`,
  `drift.py`) fails loudly instead, because a silent success there is a lie.
- Comments explain *why*, never *what*. Most of this code exists because of a
  specific failure; the comment is where that failure is recorded.
- Tests are stdlib `unittest` in `tests/`, one class per behaviour, and they run
  the real scripts as subprocesses against a temporary git repo.
- Commit format: Conventional Commits. The release workflow reads them to derive
  the next version.

## Do
- Follow the authoritative Claude Code docs for anything about hooks, settings,
  memory files, or plugin manifests. Behaviour there is versioned and changes.
- Reuse what is in `common.py`; do not reinvent or duplicate it.
- Run `make check` before calling anything done. `selfcheck.py --require-repo`
  fails on a dangling `/praxis:<command>` or `scripts/<name>.py` reference, so
  renaming or removing either means updating every doc that names it.
- Keep `docs/STABILITY.md` honest: it is the SemVer contract. Removing a command,
  a config key, an environment variable, or a state file is a MAJOR.

## Don't
- Do not add an em dash or an AI attribution anywhere, including in this file.
  `selfcheck.py` fails CI on praxis's own text before it fails anyone else's.
  `praxis:ack` on a line exempts a case that is genuinely correct.
- Do not hand-bump `plugin.json` or `marketplace.json`. The release workflow
  derives the version from the commits and stamps both; a hand-edit either
  collides with it or leaves the two manifests disagreeing.
- Do not write a value that a setting controls as a constant in any doc. State it
  conditionally and name the setting, or `drift.py` will (correctly) report it.
- Do not commit `.claude/.praxis/`, `.claude/settings.local.json`, or a
  `CLAUDE.local.md`. The guard refuses to stage them.

## Integration points
- **GitHub Actions** (`.github/workflows/release.yml`): validates the manifests,
  runs the checks, then derives a SemVer version from the Conventional Commits,
  stamps both manifests, tags, and publishes the release from the matching
  `CHANGELOG.md` section. A protected `main` needs a `RELEASE_TOKEN` secret; see
  `CONTRIBUTING.md`.
- **Claude Code itself** is the only runtime. There is no backend and no
  telemetry: see `PRIVACY.md`.

<!--
Writing note for whoever maintains this file, praxis included.

State behaviour that a setting controls *as* conditional, and name the setting.
"With auto-merge off, which is the default, praxis stops at the PR" survives the
toggle being flipped; "praxis never merges" becomes a confident lie the moment
someone turns it on, and every later session repeats it.

`/praxis:doctor` prints the settings actually in force and reports any line here
that contradicts them. Prefer pointing at that command over restating a value.
-->
