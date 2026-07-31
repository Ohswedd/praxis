# 28. Living knowledge is measured per change, including what the change removed

- Status: accepted
- Date: 2026-07-31

## Context
Every praxis scanner reads the lines a change adds. A deleted paragraph appears in none of them, so a still-valid instruction can stop existing inside a change that reports itself clean, and the loss is only noticed when somebody goes looking for what it said. Separately, 'documentation is part of done' was stated in the output style, the task orchestrator, the docs-living skill and the session directives, and measured nowhere, which is exactly the kind of rule that gets skipped at the end of a long task.

## Decision
knowledge_check.py asks three questions about the current change only: did the changelog record it, did any document move with the behaviour, and did this change remove documentation. The third reads the diff's removed lines, and reports a heading deleted from a document that shrank, or a document deleted outright. A section that merely moved is read back out of the change's own prose and is not a finding. It resolves the changelog through the same mode-aware path changelog.py writes, so a contributor's local record counts and a project with no /docs is never asked for one. report.py runs it; the only escape is --knowledge-ack, which records the reason in the report.

## Consequences
A behaviour change that genuinely needs no document must now say so once, with a reason that is kept. The check is a floor and not a judgement: it asks whether documentation moved, never whether what was written is any good. Scoped to the change so a repo's existing doc debt is never charged to whoever touched one file today. In contributor mode with a git-excluded local changelog no diff can see the file, so the check verifies that an [Unreleased] entry exists rather than that it describes today's work; that weaker guarantee is stated in the script instead of implied.
