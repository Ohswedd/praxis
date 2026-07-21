# 8. Per-prompt skill routing via UserPromptSubmit

- Status: accepted
- Date: 2026-07-21

## Context
praxis announced its pipeline once, at SessionStart. Skill selection then relied on the model spontaneously matching a skill description against the request. That works for an explicit /praxis:task, but degrades badly for a bare prompt many turns into a session, when the SessionStart block is far behind in the context — the reported symptom was that direct, command-less prompts skipped the orchestrator, the front-end pipeline, and the audit entirely.

## Decision
Add a UserPromptSubmit hook (prompt_router.py) that classifies each request by shape — implement / review / scan / deliver / none, with UI and docs modifiers — and injects a short directive naming the exact skills that request requires. It errs toward routing (a false positive costs a few lines of context; a false negative costs the whole pipeline), stays silent on information questions, slash commands and acknowledgements, and never blocks or rewrites the prompt.

## Consequences
Skill engagement no longer depends on context recency or phrasing. Cost: a small context tax on every work-shaped prompt, and a classifier whose heuristics will need tuning — so its exact matches are declared internal in STABILITY.md while its presence is stable. The router only ADDS routing; the workflow's guarantee still comes from the always-on directive and the change-based gates, so a misclassified prompt still gets the full pipeline.
