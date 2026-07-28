# 18. Bootstrap runs first, automatically, instead of being recommended

- Status: accepted
- Date: 2026-07-28

## Context
session_audit.py classified every repo as new/uninitialised/legacy/partial/managed and then printed a line recommending /praxis:bootstrap. A recommendation is not a step: it sat at the top of the context and was routinely stepped past, so sessions ran in repos with no operating brief, no guardrails and no living knowledge, which is precisely the state praxis exists to prevent. The same failure mode had already been proved for the house style, where prose lost to hooks, and for UI routing, where the wording of a request lost to the changed file list.

## Decision
Any session that does real work in a repo whose state is not 'managed' runs the bootstrap skill first, in the same turn, then continues to the request. The instruction is issued at SessionStart and repeated by the prompt router on every actionable prompt, because the SessionStart block has effectively expired by the tenth turn. Conversational prompts stay silent: answering a question does not require writing a brief first, and the router's silence on interrogatives is a property worth keeping. Bootstrap writes what is absent without asking, since creating a file a repo lacks is additive and reversible, and stops for exactly one thing: reconciling a CLAUDE.md praxis did not author, which is the only lossy step and which keeps going through the claudemd-verifier. repo_state() and bootstrap_required() moved from session_audit into common so the audit, the router and the doctor share one classifier rather than three copies.

## Consequences
A repo is set up before it is worked in, without anyone remembering a command, and the setup obeys the workspace mode so it stays local when the repo is not ours. The cost is a first turn that does two things; the skill's contract caps that at a one-line report so bootstrap cannot hijack the prompt. This is an instruction, not a block: the Stop gate deliberately does not enforce it, because that would trap read-only sessions in every unmanaged repo. Opt out per repo with bootstrap.auto = false, .claude/.praxis/no-bootstrap, or PRAXIS_BOOTSTRAP=off.

## Alternatives considered
Enforcing it in the Stop gate was rejected: the gate is keyed on change quality, and blocking a turn because a repo lacks a CLAUDE.md would punish sessions that changed nothing. Asking for confirmation every time was rejected as the status quo in a politer form: a prompt that can be declined is a recommendation.
