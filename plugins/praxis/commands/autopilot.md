---
description: Toggle auto-pilot — praxis makes no user-facing questions and decides by best-practice.
argument-hint: "[on|off|status]"
---

Run the auto-pilot toggle and report the new state:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/autopilot.py" ${ARGUMENTS:-status}
```

When ON: for this and subsequent tasks, do not ask the user design or approach
questions. Do your own QA and resolve each decision by the best-practice that fits
(use the `best-practices` skill's decision procedure), then record every non-trivial
decision in the report's "Decisions taken autonomously" section. Only stop for an
external blocker you genuinely cannot resolve yourself (e.g. a missing credential
the user must supply). Safety guards and the quality gate remain active.
