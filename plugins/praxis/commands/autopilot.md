---
description: Toggle auto-pilot — praxis makes no user-facing questions and decides by best-practice.
argument-hint: "[on|off|status]"
---

Run the auto-pilot toggle and report the new state:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot.py" ${ARGUMENTS:-status}
```

When ON: don't ask design or approach questions. Do your own QA, resolve each
decision by the best-practice that fits (`best-practices` skill), and record every
non-trivial one under "Decisions taken autonomously" in the report. Stop only for a
hard external blocker you cannot resolve (e.g. a missing credential). Safety guards
and the quality gate stay active.
