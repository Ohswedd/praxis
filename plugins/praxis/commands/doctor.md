---
description: Diagnose the praxis setup for this repo and report health/drift.
---

Run the praxis doctor check and report the results:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"
```

Then interpret the output for the user: explain any MISSING items, whether the
quality gate is enabled, and offer to run `/praxis:bootstrap` to fix drift.
Propose changes and ask before writing anything.
