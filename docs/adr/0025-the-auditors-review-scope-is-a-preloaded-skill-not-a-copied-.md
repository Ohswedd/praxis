# 25. The auditors' review scope is a preloaded skill, not a copied preamble

- Status: accepted
- Date: 2026-07-29

## Context
Ten agent briefs each carried a verbatim copy of the rules for scoping a review. It was recorded as debt entry 1 on the stated premise that Claude Code agent files have no include mechanism, so the only available fix was a self-check asserting each brief still mentioned scope.py: an assertion that catches an omission but not a wording drift. The premise was wrong. Agent frontmatter has a skills field that preloads a skill's full content into the subagent at startup, which is exactly an include. Checking the premise before engineering around it is the whole of this decision.

## Decision
The rules live once, in the review-scope skill. Every review auditor declares skills: praxis:review-scope, and no agent body restates them. Each brief keeps a six-line pointer that names the skill and says to read the file if it was not preloaded. That pointer is deliberate rather than residual duplication: a skill that is missing or disabled is skipped with only a debug-log warning, and the auditors carry Read but not Skill, so reading the file is their only fallback. It is asserted byte for byte, so it cannot drift the way the rules did. selfcheck fails on five silent breakages: a reworded pointer, an auditor that stops preloading, the skill going missing, a skill that sets disable-model-invocation and so cannot be preloaded, and the wiring appearing on one of the three agents that are handed a file list rather than a change.

## Consequences
One copy of the rules, so changing how a review is scoped is one edit rather than ten made in lockstep. The failure this guarded against (an auditor scoping to git diff, reading nothing on a branch with commits, and reporting PASS) is now impossible to introduce silently: every route to it fails CI. The residual cost is the pointer, six lines in ten files, which has no mechanics to drift and is byte-enforced. A second cost is a dependency on a documented frontmatter field: if a future Claude Code changed or removed skills preloading, the fallback pointer is what keeps the auditors correct, which is why it exists rather than being trimmed away as redundant.

## Alternatives considered
Generating the full preamble into each brief from one source, with a byte-equality check, was the fallback plan before the skills field was found: it removes drift but keeps ten copies and needs a sync tool. Passing the scope in the dispatch prompt was rejected because agents are also invoked directly by a user, and would then have no scoping at all. Trimming the pointer and relying on preloading alone was rejected: a silently skipped preload would leave every auditor with no scoping, which is the exact catastrophic failure, and six lines is cheap insurance against it.
