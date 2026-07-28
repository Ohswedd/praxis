# 20. The front-end pipeline has no command of its own

- Status: accepted
- Date: 2026-07-28

## Context
ADR-0014 established that UI work is decided by the surface a change touches, not by how the request was phrased, and three mechanisms already implement that: the prompt router matches interface vocabulary and UI file extensions, the task-orchestrator wraps the pipeline around its phases when the work will touch that surface, and the Stop gate resolves the same question from the changed file list and refuses a report without accessibility=pass and design-consistency=pass. /praxis:frontend was a fourth entry point for a decision the other three make from files.

## Decision
Remove /praxis:frontend. The frontend-pipeline skill, its phases, artifacts, references and two auditors are unchanged; only the command file is gone. Its description now states the surface trigger instead of naming a command, and the skill carries a short paragraph explaining that three mechanisms start it and why a fourth was a liability.

## Consequences
One less thing to remember, and one less way to get UI work wrong. A command can only differ from the file-based mechanisms in two ways, and both are failures: typed after the design decisions have already been made, or, far more often, not typed at all for the 'fix the checkout bug' that was front-end work all along. This removes a documented stable-surface command, so it is a breaking change and the release is a MAJOR (3.0.0). Migration is nothing: describe the work and the pipeline engages. selfcheck.py fails on a dangling /praxis: reference and drift.py reports one, so every doc that named the command had to be updated before this could merge.

## Alternatives considered
Keeping it as a deprecated alias was rejected: an alias that is only ever the worse way to do something is a trap kept alive for politeness, and the surface it preserves would have to be carried to the next MAJOR. Keeping it as an explicit 'run the full pipeline including research' escape was rejected too: Phase 0 already sizes the work as full/feature/patch, and a user who wants the full route can say so in the request.
