---
description: Show or toggle praxis settings for this repo (workspace mode, auto-pilot, auto-merge, auto-bootstrap, quality gate).
argument-hint: "[ blank = show all | mode owner|contributor|auto | autopilot on|off | auto-merge on|off | bootstrap on|off | gate on|off ]"
---

Run the settings command and report the result:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" ${ARGUMENTS:-status}
```

Each setting resolves environment variable, then repo toggle file, then
`.praxis.toml`, then (for `mode`) detection, and the output names the source, so a
value that surprises the user can always be traced. Read the output rather than
assuming: what it prints is what is in force for the rest of the session.

- **mode** is the one setting that is not on/off. `owner` means praxis maintains
  this project's `CLAUDE.md`, `.claude/settings.json`, `/docs`, `CHANGELOG.md` and
  ADRs as committed files. `contributor` means the repository is not ours:
  the brief is `CLAUDE.local.md`, settings are `.claude/settings.local.json`,
  praxis config is `.claude/.praxis/praxis.toml`, and `/docs`, `CHANGELOG.md`,
  `docs/adr/` and `docs/design/` are updated **only if the repo already has
  them**, otherwise kept under `.claude/.praxis/knowledge/`. All of it is
  git-excluded, and nothing praxis authors goes near a commit. `auto` (the
  default) infers it from the repo's git history. Switching also adds or removes
  the praxis block in `$GIT_COMMON_DIR/info/exclude`.
- **auto-pilot ON**: ask no design or approach questions. Do your own QA, resolve
  each decision with the `best-practices` skill, and record every non-trivial one
  under "Decisions taken autonomously" in the report. Stop only for a hard external
  blocker such as a missing credential.
- **auto-merge ON**: after a green audit and passing checks, self-review the diff
  and merge the PR. OFF means open the PR and leave the merge to a human. It never
  applies in `contributor` mode: merging is the maintainers' call.
- **bootstrap ON** (the default): a repo praxis has not set up is bootstrapped
  first, in the same turn, before the work starts. OFF leaves the repo without a
  brief or guardrails until the user runs `/praxis:bootstrap` themselves.
- **gate OFF**: the Stop hook no longer holds the turn open. Say so plainly when
  you hand work back, because nothing else will.

A toggle file is a local, uncommitted choice. For a decision the whole team should
share, put it in `.praxis.toml` and commit it; in `contributor` mode put it in
`.claude/.praxis/praxis.toml`, which layers on top and stays local. Safety guards
and the secret and destructive-command blocks stay active whatever these are set
to, as does the refusal to stage a praxis local artifact.
