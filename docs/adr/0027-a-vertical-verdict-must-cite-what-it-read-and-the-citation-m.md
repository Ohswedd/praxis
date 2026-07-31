# 27. A vertical verdict must cite what it read, and the citation must resolve

- Status: accepted
- Date: 2026-07-31

## Context
A vertical verdict reached report.py as a string in a comma-separated list. Nothing distinguished eight auditors that ran from eight words that were typed, and sessions were reported in which an audit asserted findings, coverage, or file contents that a second look showed had never been examined. praxis had already closed this exact hole for test results in ADR-0010 and left every other claim on trust.

## Decision
Each verdict is recorded on its own, as it is reached: report.py vertical <name> --verdict ... --summary ... --evidence 'file:line,...'. The summary must be a real sentence and at least one citation is required, and every citation is verified to resolve against the repository: the file must exist, and a line number must be within it. A citation that does not resolve is refused at the moment it is written. report.py record then refuses to claim any verdict the ledger does not carry, or that contradicts it. The rule the auditors work under lives once, in the audit-evidence skill, preloaded through the same frontmatter mechanism that carries review-scope.

## Consequences
An audit costs one extra command per vertical, which is the friction that does the work: naming a file you read is free, and inventing one now fails. This proves that a verdict was substantiated, not that a subagent ran, and that boundary is documented rather than blurred. gate.require_evidence turns it off for a workflow that records evidence elsewhere. Citations are checked for existence, not for relevance: praxis can refuse a fabricated reference, not a lazily chosen one.
