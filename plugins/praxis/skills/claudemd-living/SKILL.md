---
name: claudemd-living
description: Keep the CLAUDE.md hierarchy (root and nested files) current and regression-free. Use when a convention, command, dependency, or architectural pattern changes; when the user runs /praxis:sync; when you notice CLAUDE.md contradicts the actual code; or after adding a subsystem that deserves its own nested CLAUDE.md. Proposes updates as diffs, routes them through the regression verifier, and never blindly overwrites or drops still-valid instructions. Use this instead of editing CLAUDE.md directly.
---

# Living CLAUDE.md

CLAUDE.md is loaded into context every session, so it must stay accurate — a
stale or contradictory memory file silently degrades every future session. This
skill maintains it with the same no-regression discipline praxis applies to
code.

## When to act
- A build/test/run command changed.
- A new convention, dependency, or architectural pattern was introduced.
- A whole new cohesive subsystem appeared → it may need its own nested file.
- The session audit or your own reading found CLAUDE.md contradicting the code.
- The user asks to update project memory (`/praxis:sync`).

## Step 1 — Locate the right file
Decide the correct scope: a change local to a subsystem belongs in that
subsystem's nested `CLAUDE.md`, not the root. Only genuinely global facts go in
the root. Create a nested file if the scope warrants one and none exists.

## Step 2 — Draft the update
Write the minimal edit that captures the change. Preserve the existing structure
and the `<!-- praxis:managed -->` marker. Keep it high-signal; do not let the
file bloat.

## Step 3 — Verify against regression (mandatory)
Before writing, compare the current file with your draft:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/claudemd_check.py <current> <draft>
```

Then dispatch `@praxis:claudemd-verifier` with both versions. The verifier
confirms the draft does **not**:
- drop a still-valid instruction,
- remove a build/test/run command that still applies,
- contradict another part of the file,
- shrink the file by silently losing content.

Any structural regression the checker flags must be explained and justified by
the verifier (e.g. "the `npm run e2e` command was removed because that script no
longer exists") before it is accepted.

## Step 4 — Propose, then write
Show the user the diff and the verifier's verdict. Write only after confirmation
(or immediately if the change is additive and unambiguously safe, stating what
you did). Never overwrite silently.

## Step 5 — Keep the hierarchy coherent
After updating, ensure root and nested files do not contradict each other and
that nothing is duplicated across levels.
