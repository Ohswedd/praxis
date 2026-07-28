---
description: Diagnose the praxis setup for this repo and report health/drift.
---

Run the praxis doctor check and report the results:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"
```

Interpret the output rather than pasting it: explain each MISSING item and what it
costs, state the settings actually in force, and walk through any documentation
drift it found. Drift means a document contradicts the live configuration, or
points at a command, script, or file that no longer exists; both make a session
act on something untrue, so treat them as defects and offer to fix them with
`/praxis:docs`.

Then offer `/praxis:bootstrap` for missing setup, and `/praxis:config` to change a
setting. Propose changes and ask before writing anything.
