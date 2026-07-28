# 24. Technical debt is a vertical, and a register, not a comment

- Status: accepted
- Date: 2026-07-28

## Context
Nothing in praxis asked what a change would cost later. The seven verticals all judge the code as it is now: correct, safe, fast, complete, non-duplicating, documented. None covers work that is correct today and expensive tomorrow, which is most of what makes a codebase unpleasant to work in over time. The only place the word debt appeared was in the completeness auditor's brief, where it meant TODO markers: unfinished work, which is a different thing entirely. <!-- praxis:ack: naming the marker is the point -->

## Decision
Add debt as the eighth code vertical, with @praxis:debt-auditor, and give it a register. The auditor looks for shortcuts and workarounds, coupling and duplication something must keep in sync by hand, abstractions the change has made wrong, deprecated or pinned dependencies, and tests that lock in implementation rather than behaviour. Its central question is not whether debt exists but whether it was recorded: debt taken for a stated reason and written down is a decision, while the same shortcut taken silently is the defect, because the next person meets the consequence without the reason. debt.py maintains docs/DEBT.md under the living-knowledge contract, and refuses an entry that does not state its interest (what it costs, and how often) and its principal (what the real fix is).

## Consequences
Deliberate shortcuts become reviewable decisions rather than discoveries. The register is rankable, because every entry carries a cost, which is what lets debt be prioritised against features instead of being a wish-list. The auditor does not re-report what is already registered, so recording debt is the cheapest correct resolution and the incentive points the right way. As a repo-scan dimension it lets an existing codebase be ranked by interest rather than by how bad each file looks. Costs: one more subagent per change audit; and the boundary with duplication (over-engineering) and completeness (stubs) has to be stated explicitly in the agent brief, or three auditors report the same finding.

## Alternatives considered
Folding debt into the completeness auditor was rejected: completeness asks whether this change is finished, debt asks what the finished change will cost, and merging them buries the second question under the first. A TODO-comment convention was rejected: scan_placeholders already refuses those, <!-- praxis:ack --> and a comment is not a record anyone can rank or review. Making the register gate-enforced was rejected as premature; the auditor reports unrecorded debt as a finding, which is enforcement enough without failing a build over a judgement call.
