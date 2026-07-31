# 26. The report runs the deterministic scanners, because recording it was the way past them

- Status: accepted
- Date: 2026-07-31

## Context
The Stop gate's fast path is 'a green report for this signature exists, therefore allow'. Every deterministic scan the gate performed (unfinished work, house style) ran only on the branch where no such report existed. Recording a report was therefore not the consequence of passing the scanners; it was the way around them, and a TODO <!-- praxis:ack: naming the marker is the point --> or an em dash could ship inside a change that reported itself clean. The same shape produced the reported symptom of tech debt surviving three or four rounds of review.

## Decision
report.py runs scan_placeholders.py, scan_style.py and knowledge_check.py itself at record time, records what each one found, and cannot write a green report over an unresolved finding. A scanner that could not run is recorded as not run and is equally disqualifying: the hooks fail open so a broken scanner cannot wedge a session, but a report that failed open would state that a check passed when it never executed. quality_gate.py re-derives its verdict from that recorded evidence rather than reading the report's status field.

## Consequences
Recording a report is now slower, by the cost of three scans over the change. A report written by 3.1 carries no scan evidence and is rejected rather than grandfathered, on the same reasoning as ADR-0010: an unverifiable claim is not evidence. Re-recording costs one `report.py vertical`
per verdict plus the `record` itself at 3.2 defaults, or a single `record` with
`require_evidence = false`, and saying "one command" understated that by an order
of magnitude. The gate duplicates the verdict logic that report.py already applies, deliberately: the report is JSON in a directory anyone can write, so a gate that trusted its status field would have its whole guarantee one hand-edited line away.
