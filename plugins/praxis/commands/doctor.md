---
description: Diagnose the praxis setup for this repo and report health/drift.
---

Run the praxis doctor check and report the results:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"
```

Interpret the output: explain any MISSING items and whether the quality gate is
enabled, then offer to run `/praxis:bootstrap` to fix drift. Propose changes and
ask before writing anything.
