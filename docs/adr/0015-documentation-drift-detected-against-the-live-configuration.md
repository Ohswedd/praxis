# 15. Documentation drift detected against the live configuration

- Status: accepted
- Date: 2026-07-28

## Context
Documentation in this project rots one way: it states as a constant something that is really configuration, and then the configuration moves. The reported case is a doc asserting that praxis opens a pull request and leaves the merge to a human, written while auto_merge was off and still read as authoritative long after a repo turned it on. Nothing about the sentence looks stale, so every session repeats the wrong policy with complete confidence.

## Decision
Add drift.py, which compares the assertions in a repo's instruction documents (CLAUDE.md, README, /docs) against the configuration actually in force, and checks that every documented command, slash command, and link still resolves. A sentence that qualifies itself is exempt, so a doc explaining both states of a toggle is not a finding, and a praxis:ack line covers a deliberate mention such as a migration table. The SessionStart audit additionally prints the resolved settings every session, so a turn never has to infer policy from prose at all, and the delivery route in the router states the live merge policy rather than a default.

## Consequences
The specific failure that prompted this cannot recur silently: it surfaces at SessionStart, in /praxis:doctor, and at both ends of /praxis:docs. Detection is deliberately conservative, since a drift report that fires on correct documentation is a report nobody reads; it therefore catches unqualified contradictions and broken references, not every possible inaccuracy. Fixing is left to docs-living and claudemd-living: this reports, it never edits.

## Alternatives considered
Generating the affected sentences from the configuration, which makes documentation unreadable and unreviewable. Removing every mention of a configurable behaviour from the docs, which loses the explanation users need. Trusting review, which is what allowed the drift to persist across several releases.
