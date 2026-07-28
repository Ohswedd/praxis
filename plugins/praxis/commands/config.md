---
description: Show or toggle praxis settings for this repo (auto-pilot, auto-merge, quality gate).
argument-hint: "[ blank = show all | autopilot on|off | auto-merge on|off | gate on|off ]"
---

Run the settings command and report the result:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config.py" ${ARGUMENTS:-status}
```

Each switch resolves environment variable, then repo toggle file, then
`.praxis.toml`, then the default, and the output names the source, so a value that
surprises the user can always be traced. Read the output rather than assuming:
what it prints is what is in force for the rest of the session.

- **auto-pilot ON**: ask no design or approach questions. Do your own QA, resolve
  each decision with the `best-practices` skill, and record every non-trivial one
  under "Decisions taken autonomously" in the report. Stop only for a hard external
  blocker such as a missing credential.
- **auto-merge ON**: after a green audit and passing checks, self-review the diff
  and merge the PR. OFF means open the PR and leave the merge to a human.
- **gate OFF**: the Stop hook no longer holds the turn open. Say so plainly when
  you hand work back, because nothing else will.

A toggle file is a local, uncommitted choice. For a decision the whole team should
share, put it in `.praxis.toml` and commit it. Safety guards and the secret and
destructive-command blocks stay active whatever these are set to.
